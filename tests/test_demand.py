"""Tests for synthetic demand curves (sreca.forecast.demand) — spec §3, §4.

Curves are synthetic and parametrizable (decision #3). The shapes encode the corrected
synergy invariant (spec §9.1): the dairy farm's NON-flexible base (milking) peaks at
dawn/dusk, OUTSIDE the solar window — which is exactly why flexible loads must later be
shifted INTO it (load_shift's job, a separate module).
"""
import pytest

from sreca.forecast import demand

MAYOR = "residencial_mayor_diurno"
GANADERO = "ganadero_lacteo"
SOLAR_NOON = 13  # representative midday hour inside the solar window


def test_profile_shape_normalized_24h():
    for profile in (MAYOR, GANADERO):
        shape = demand.profile_shape(profile)
        assert len(shape) == 24
        assert sum(shape) == pytest.approx(1.0)
        assert all(w >= 0 for w in shape)


def test_daily_demand_scales_to_total():
    curve = demand.daily_demand(MAYOR, daily_kwh=10.0)
    assert len(curve) == 24
    assert sum(curve) == pytest.approx(10.0)


def test_mayor_diurno_present_at_midday():
    # elderly are home during the day → midday demand clearly above the small-hours base
    shape = demand.profile_shape(MAYOR)
    night = sum(shape[0:5]) / 5
    midday = sum(shape[11:15]) / 4
    assert midday > night


def test_ganadero_base_peaks_at_milking_not_midday():
    # corrected synergy: milking (dawn ~6h, dusk ~18h) dominates; the solar-noon base is
    # LOWER → no natural overlap with the solar window from the base load.
    shape = demand.profile_shape(GANADERO)
    assert shape[6] > shape[SOLAR_NOON]    # morning milking peak
    assert shape[18] > shape[SOLAR_NOON]   # evening milking peak


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        demand.profile_shape("perfil_inexistente")
