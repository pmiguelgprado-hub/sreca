"""Tests for the physical FV model (sreca.forecast.pv) — spec §5.

Unit tests anchor each transform with hand-computed expected values. The calibration
integration test runs the whole model on the committed climatology fixture and asserts
the annual total lands within ±10 % of PVGIS (spec §5 sanity). The fixture is mocked
data on disk — no network (spec §10).
"""
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from sreca.concejo import load_concejo
from sreca.forecast import pv

FIXTURE = Path(__file__).parent / "fixtures" / "teverga_climatology_hourly.csv"
LAT, LON = 43.16, -6.09
DECL_MAX = 23.44  # axial tilt — solar declination at solstices


# --- solar position -------------------------------------------------------

def _min_zenith_over_day(year, month, day):
    """Lowest solar zenith reached during a UTC day (i.e. solar noon)."""
    zeniths = []
    for h in range(24):
        dt = datetime(year, month, day, h, tzinfo=timezone.utc)
        z, _ = pv.solar_position(dt, LAT, LON)
        zeniths.append(z)
    return min(zeniths)


def test_solar_noon_zenith_summer_solstice():
    # at solar noon on the summer solstice, zenith ≈ lat − declination
    z = _min_zenith_over_day(2021, 6, 21)
    assert z == pytest.approx(LAT - DECL_MAX, abs=1.5)


def test_solar_noon_zenith_winter_solstice():
    # winter solstice: zenith ≈ lat + declination (sun lowest)
    z = _min_zenith_over_day(2021, 12, 21)
    assert z == pytest.approx(LAT + DECL_MAX, abs=1.5)


def test_solar_azimuth_east_morning_west_afternoon():
    # Locks the E/W azimuth convention (0=N, 90=E, 180=S, 270=W). The south-facing
    # calibration is symmetric in cos(sun_az−180) → blind to an E/W flip; this is the
    # only test that catches it, which matters for non-south arrays / other concejos (§9.4).
    # Solar noon here ≈ 12:24 UTC, so 08:00 is clearly morning, 16:00 clearly afternoon.
    _, az_morning = pv.solar_position(datetime(2021, 6, 21, 8, tzinfo=timezone.utc), LAT, LON)
    _, az_afternoon = pv.solar_position(datetime(2021, 6, 21, 16, tzinfo=timezone.utc), LAT, LON)
    assert az_morning < 180   # sun in the eastern sky
    assert az_afternoon > 180  # sun in the western sky


# --- transposition to plane of array (POA) --------------------------------

def test_poa_horizontal_equals_ghi():
    # tilt=0: POA must reduce to GHI for any closure-consistent (DNI,DHI,zenith)
    zenith = 40.0
    dni, dhi = 700.0, 120.0
    ghi = dni * math.cos(math.radians(zenith)) + dhi  # closure
    poa = pv.poa_irradiance(ghi=ghi, dni=dni, dhi=dhi, zenith_deg=zenith,
                            sun_azimuth_deg=180.0, tilt_deg=0.0,
                            surface_azimuth_deg=180.0)
    assert poa == pytest.approx(ghi, rel=1e-6)


def test_poa_beam_clamped_when_sun_behind_panel():
    # south panel tilted 35°, sun in the north (azimuth 0) and low → no beam gain
    poa = pv.poa_irradiance(ghi=100.0, dni=500.0, dhi=80.0, zenith_deg=85.0,
                            sun_azimuth_deg=0.0, tilt_deg=35.0,
                            surface_azimuth_deg=180.0)
    # only diffuse + ground terms remain; beam term clamped to 0, never negative
    assert poa >= 0.0
    assert poa < 100.0  # no direct contribution


# --- cell temperature (NOCT model) ----------------------------------------

def test_cell_temperature_noct_anchor():
    # at POA=800, Tcell = Tamb + (NOCT−20)  (spec §5 step 3)
    assert pv.cell_temperature(poa=800.0, t_amb=20.0, noct_c=45.0) == pytest.approx(45.0)


def test_cell_temperature_zero_irradiance_equals_ambient():
    assert pv.cell_temperature(poa=0.0, t_amb=12.0, noct_c=45.0) == pytest.approx(12.0)


# --- DC power -------------------------------------------------------------

def test_dc_power_at_stc_equals_rated():
    # POA=1000, Tcell=25, no losses → P = rated kWp
    p = pv.dc_power(poa=1000.0, t_cell=25.0, kwp=15.0, gamma_pmp_per_c=-0.0035,
                    system_losses=0.0)
    assert p == pytest.approx(15.0)


def test_dc_power_temperature_derate():
    # Tcell=45 (ΔT=20) with γ=−0.0035 → factor 0.93
    p = pv.dc_power(poa=1000.0, t_cell=45.0, kwp=15.0, gamma_pmp_per_c=-0.0035,
                    system_losses=0.0)
    assert p == pytest.approx(15.0 * 0.93)


def test_dc_power_never_negative():
    p = pv.dc_power(poa=0.0, t_cell=10.0, kwp=15.0, gamma_pmp_per_c=-0.0035,
                    system_losses=0.14)
    assert p == pytest.approx(0.0)


# --- calibration (integration) — the test that proves the model -----------

def test_annual_energy_within_10pct_of_pvgis():
    # Same-source check: model runs on PVGIS TMY → compare to PVGIS PVcalc for the
    # same site/config. PVGIS API 2026-06-20 (15 kWp, 35° south, loss=14): E_y=17376,
    # yield=1158. The residual (~+4%) is our lighter loss model (system+temp only vs
    # PVGIS's spectral/low-light) — documented in docs/2026-06-20-calibration-source-discrepancy.md.
    cfg = load_concejo("teverga")
    df = pd.read_csv(FIXTURE)
    annual_kwh = pv.annual_energy(df, cfg.site, cfg.pv)

    expected = 17376.0  # PVGIS PVcalc canonical, same site/config
    assert abs(annual_kwh - expected) / expected < 0.10, \
        f"annual {annual_kwh:.0f} kWh outside ±10% of {expected:.0f}"

    yield_kwh_kwp = annual_kwh / cfg.pv.kwp
    assert yield_kwh_kwp == pytest.approx(1158.0, rel=0.10)


def test_somiedo_annual_energy_within_10pct_of_pvgis():
    # Second concejo carries the same calibration guarantee as Teverga, so its public dashboard
    # numbers are not uncross-checked. PVGIS PVcalc 2026-06-21 (43.094,-6.255; 15 kWp, 35° south,
    # loss=14, free-standing, horizon): E_y=16945. Model on its own TMY fixture lands at ~+0.2%.
    from sreca.datasets import climatology_path

    cfg = load_concejo("somiedo")
    df = pd.read_csv(climatology_path("somiedo"))
    annual_kwh = pv.annual_energy(df, cfg.site, cfg.pv)

    expected = 16945.0  # PVGIS PVcalc canonical, same site/config
    assert abs(annual_kwh - expected) / expected < 0.10, \
        f"Somiedo annual {annual_kwh:.0f} kWh outside ±10% of {expected:.0f}"


def test_annual_energy_horizon_agnostic_sum_matches_hourly():
    # internal consistency: annual_energy == Σ of hourly_energy series it produces
    cfg = load_concejo("teverga")
    df = pd.read_csv(FIXTURE)
    series = pv.hourly_energy(df, cfg.site, cfg.pv)
    assert len(series) == 8760
    assert sum(series) == pytest.approx(pv.annual_energy(df, cfg.site, cfg.pv))
