"""Tests for config loader (sreca.concejo) — per-concejo config drives everything (spec §8, §9.4)."""
import pytest

from sreca.concejo import available_concejos, load_concejo, ConcejoConfig


def test_loads_teverga_site_and_pv():
    cfg = load_concejo("teverga")
    assert isinstance(cfg, ConcejoConfig)
    assert cfg.concejo == "Teverga"
    assert cfg.site.lat == 43.16
    assert cfg.site.lon == -6.09
    assert cfg.site.tilt_deg == 35
    assert cfg.site.azimuth_deg == 180
    assert cfg.pv.kwp == 15
    assert cfg.pv.system_losses == 0.14
    assert cfg.pv.noct_c == 45
    assert cfg.pv.gamma_pmp_per_c == -0.0035


def test_loads_prices_and_legal():
    cfg = load_concejo("teverga")
    assert cfg.prices.retail_eur_kwh == 0.20
    assert cfg.prices.compensation_eur_kwh == 0.06
    assert cfg.legal.proximidad_max_m == 5000          # RDL 7/2026 (spec §9.3)
    assert cfg.legal.coefficient_mode == "ex_ante"     # ley vigente TED/1247/2021


def test_loads_participants_with_flexible_loads():
    cfg = load_concejo("teverga")
    assert len(cfg.participants) == 3
    by_id = {p.id: p for p in cfg.participants}
    granja = by_id["granja_lactea_1"]
    assert granja.profile == "ganadero_lacteo"
    assert granja.renta_priority == 1
    assert granja.daily_kwh == 25.0
    assert [f.name for f in granja.flexible_loads] == ["tanque_frio_leche", "acs_limpieza"]
    assert granja.flexible_loads[0].energy_kwh == 6.0
    assert granja.flexible_loads[0].duration_h == 3
    assert all(f.shiftable for f in granja.flexible_loads)
    # mayor-diurno has no flexible loads (invariant: only farm has shiftable loads)
    assert by_id["mayor_diurno_1"].flexible_loads == []
    assert by_id["mayor_diurno_1"].daily_kwh == 8.0


def test_coefficient_mode_must_be_legal_value():
    # spec §6: coefficient_mode ∈ {ex_ante, ex_post_dynamic}; ex_post not legal yet
    cfg = load_concejo("teverga")
    assert cfg.legal.coefficient_mode in {"ex_ante", "ex_post_dynamic"}


def test_unknown_concejo_raises():
    with pytest.raises(FileNotFoundError):
        load_concejo("atlantida")


def test_available_concejos_lists_configured():
    concejos = available_concejos()
    assert "teverga" in concejos
    assert "somiedo" in concejos          # replicability: a second concejo exists
    assert concejos == sorted(concejos)


def test_population_verified_at_source_per_concejo():
    # Both figures verified at the INE source (tempus API, table 2886, padrón 1-ene-2025).
    # The invariant is "no fabricated public number", not "Somiedo stays blank": once the
    # official figure is confirmed at source it is filled in.
    teverga = load_concejo("teverga")
    somiedo = load_concejo("somiedo")
    assert teverga.population == 1495 and teverga.population_year == 2025
    assert somiedo.population == 1031 and somiedo.population_year == 2025


def test_area_and_density_per_concejo():
    # area_km2 is the official surface; density is derived (pop/area), not a duplicated figure.
    teverga = load_concejo("teverga")
    somiedo = load_concejo("somiedo")
    assert teverga.area_km2 == 168.86
    assert somiedo.area_km2 == 291.38
    assert teverga.density_hab_km2 == pytest.approx(1495 / 168.86, abs=0.01)
    assert somiedo.density_hab_km2 == pytest.approx(1031 / 291.38, abs=0.01)


def test_density_none_when_area_or_population_missing(tmp_path):
    # No area or no population → no density (never invent the denominator).
    (tmp_path / "x.yaml").write_text(
        "concejo: X\n"
        "site: {lat: 43.0, lon: -6.0, tilt_deg: 35, azimuth_deg: 180}\n"
        "pv: {kwp: 15, system_losses: 0.14, noct_c: 45, gamma_pmp_per_c: -0.0035}\n"
        "prices: {retail_eur_kwh: 0.20, compensation_eur_kwh: 0.06}\n"
        "legal: {proximidad_max_m: 5000, coefficient_mode: ex_ante}\n"
        "participants: [{id: a, profile: residencial_mayor_diurno, renta_priority: 3, daily_kwh: 8.0}]\n"
    )
    cfg = load_concejo("x", config_dir=tmp_path)
    assert cfg.area_km2 is None
    assert cfg.population is None
    assert cfg.density_hab_km2 is None
