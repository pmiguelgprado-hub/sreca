"""Tests for config loader (sreca.concejo) — per-concejo config drives everything (spec §8, §9.4)."""
import pytest

from sreca.concejo import load_concejo, ConcejoConfig


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
