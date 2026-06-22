"""Tests for the cockpit analytics backbone (sreca.dashboard.analytics) — pure, DB-free.

The interactive cockpit recomputes live from an overridable config + uploaded curves, so the
whole backbone must be a pure function of (ConcejoConfig, climatology). No Streamlit, no DB.
"""
import pandas as pd
import pytest

from sreca.concejo import load_concejo
from sreca.dashboard import analytics
from sreca.datasets import climatology_path
from sreca.report import annual_summary


@pytest.fixture
def teverga():
    return load_concejo("teverga")


@pytest.fixture
def clim():
    return pd.read_csv(climatology_path("teverga"))


def test_apply_overrides_scales_generation_linearly(teverga, clim):
    base = analytics.monthly_generation(teverga, clim)
    bigger = analytics.apply_overrides(teverga, kwp=teverga.pv.kwp * 2)
    big = analytics.monthly_generation(bigger, clim)
    for m in base:
        assert big[m] == pytest.approx(2 * base[m], rel=1e-6)


def test_apply_overrides_is_surgical_and_nonmutating(teverga):
    o = analytics.apply_overrides(
        teverga, retail_eur_kwh=0.25, daily_kwh={"granja_lactea_1": 30.0}
    )
    assert o.prices.retail_eur_kwh == 0.25
    assert o.prices.compensation_eur_kwh == teverga.prices.compensation_eur_kwh  # untouched
    by = {p.id: p for p in o.participants}
    assert by["granja_lactea_1"].daily_kwh == 30.0
    assert by["mayor_diurno_1"].daily_kwh == 8.0                                 # untouched
    # original config is a frozen value, never mutated by an override
    assert load_concejo("teverga").prices.retail_eur_kwh == 0.20


def test_monthly_generation_sums_to_annual(teverga, clim):
    m = analytics.monthly_generation(teverga, clim)
    assert set(m) == set(range(1, 13))
    assert sum(m.values()) == pytest.approx(annual_summary(teverga, clim).gen_kwh, rel=1e-9)


def test_generation_heatmap_shape_and_seasonality(teverga, clim):
    h = analytics.generation_heatmap(teverga, clim)
    assert list(h.index) == list(range(1, 13))      # 12 months
    assert list(h.columns) == list(range(24))        # 24 hours
    assert h.loc[6, 3] == pytest.approx(0.0, abs=1e-6)   # June 03h: no sun
    assert h.loc[6, 13] > h.loc[12, 13]                  # June midday > December midday


def test_energy_balance_conserves_generation(teverga, clim):
    a = annual_summary(teverga, clim)
    b = analytics.energy_balance(a)
    assert b.self_consumed_kwh == pytest.approx(a.self_consumed_kwh)
    assert b.exported_kwh == pytest.approx(a.excess_kwh)
    assert b.grid_import_kwh == pytest.approx(a.demand_kwh - a.self_consumed_kwh)
    # self-consumed + exported must equal total generation (no energy invented or lost)
    assert b.self_consumed_kwh + b.exported_kwh == pytest.approx(a.gen_kwh)


def test_demand_from_csv_parses_per_participant_curves():
    df = pd.DataFrame({"hour": list(range(24)), "hogar_1": [1.0] * 24, "hogar_2": [2.0] * 24})
    out = analytics.demand_from_csv(df)
    assert set(out) == {"hogar_1", "hogar_2"}
    assert out["hogar_1"] == [1.0] * 24
    assert sum(out["hogar_2"]) == pytest.approx(48.0)


def test_demand_from_csv_rejects_malformed():
    with pytest.raises(ValueError):
        analytics.demand_from_csv(pd.DataFrame({"foo": [1, 2, 3]}))          # no 'hour'
    with pytest.raises(ValueError):
        analytics.demand_from_csv(pd.DataFrame({"hour": list(range(23)), "h1": [1.0] * 23}))  # not 24h
    with pytest.raises(ValueError):
        analytics.demand_from_csv(pd.DataFrame({"hour": list(range(24))}))   # no participant col


def test_cockpit_bundle_is_consistent_and_wires_every_field(teverga, clim):
    b = analytics.cockpit_bundle(teverga, clim)
    # annual matches the standalone honest engine
    assert b.annual.gen_kwh == pytest.approx(annual_summary(teverga, clim).gen_kwh)
    # balance conserves generation
    assert b.balance.self_consumed_kwh + b.balance.exported_kwh == pytest.approx(b.annual.gen_kwh)
    # monthly sums to annual
    assert sum(b.monthly.values()) == pytest.approx(b.annual.gen_kwh, rel=1e-9)
    # day-type series present and well-formed (resolves the previously-orphaned coefficients)
    assert len(b.gen_daytype) == 24
    for h in range(24):
        assert sum(b.beta_daytype[p][h] for p in b.beta_daytype) == pytest.approx(1.0)
    # load-shift wired (Route B), and only flexible loads appear (synergy invariant)
    assert "tanque_frio_leche" in b.load_shift
    assert "ordeno" not in b.load_shift
    assert b.coefficient_mode == "ex_ante"


def test_cockpit_bundle_reacts_to_overrides(teverga, clim):
    base = analytics.cockpit_bundle(teverga, clim)
    bigger = analytics.cockpit_bundle(analytics.apply_overrides(teverga, kwp=teverga.pv.kwp * 2), clim)
    assert bigger.annual.gen_kwh == pytest.approx(2 * base.annual.gen_kwh, rel=1e-6)


def test_annual_summary_accepts_demand_override(teverga, clim):
    # An uploaded flat 1 kWh/h curve for each participant → deterministic annual demand.
    override = {p.id: [1.0] * 24 for p in teverga.participants}
    a = annual_summary(teverga, clim, demand_override=override)
    assert a.demand_kwh == pytest.approx(len(teverga.participants) * 24 * 365, rel=0.01)
    # the synthetic path (no override) yields a different demand, proving the override took effect
    assert a.demand_kwh != pytest.approx(annual_summary(teverga, clim).demand_kwh)
