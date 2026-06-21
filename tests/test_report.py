"""Annual headline figures — full 8760 h chain (honest, not day-type × 365).

Day-type × 365 averages the days first and then takes min(gen, demand); min is concave, so by
Jensen it *overstates* collective self-consumption and savings. The headline a grant jury sees
must come from the full-resolution chain. These tests pin conservation, bounds, additivity, and
the Jensen direction (annual rate ≤ day-type×365 rate).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sreca.concejo import load_concejo
from sreca.forecast.demand import daily_demand
from sreca.forecast.pv import hourly_energy
from sreca.optimize.coefficients import compute_coefficients
from sreca.optimize.savings import compute_savings
from sreca.report import annual_summary

_CLIMATOLOGY = Path(__file__).parent / "fixtures" / "teverga_climatology_hourly.csv"


@pytest.fixture(scope="module")
def climatology() -> pd.DataFrame:
    return pd.read_csv(_CLIMATOLOGY)


@pytest.fixture(scope="module")
def summary(climatology):
    return annual_summary(load_concejo("teverga"), climatology)


def test_conservation(summary):
    """Self-consumed can never exceed generation nor demand (energy conservation)."""
    assert summary.self_consumed_kwh <= summary.gen_kwh + 1e-6
    assert summary.self_consumed_kwh <= summary.demand_kwh + 1e-6


def test_rates_in_unit_interval(summary):
    assert 0.0 <= summary.self_consumption_rate <= 1.0
    assert 0.0 <= summary.demand_coverage <= 1.0


def test_per_participant_euros_sum_to_community(summary):
    total = sum(p.eur_saved for p in summary.participants.values())
    assert total == pytest.approx(summary.community_eur, rel=1e-9)


def test_per_participant_self_consumed_sum_to_community(summary):
    total = sum(p.self_consumed_kwh for p in summary.participants.values())
    assert total == pytest.approx(summary.self_consumed_kwh, rel=1e-9)


def test_generation_matches_full_year(summary, climatology):
    cfg = load_concejo("teverga")
    expected = sum(hourly_energy(climatology, cfg.site, cfg.pv))
    assert summary.gen_kwh == pytest.approx(expected, rel=1e-9)


def test_annual_rate_not_above_daytype_extrapolation(summary, climatology):
    """The Jensen guard: day-type×365 must not understate self-consumption vs the honest annual
    figure. If it did, the cheap shortcut would be safe and this module would be pointless. We
    require annual ≤ day-type×365, i.e. the shortcut inflates (or ties)."""
    cfg = load_concejo("teverga")
    df = climatology.copy()
    df["gen"] = hourly_energy(df, cfg.site, cfg.pv)
    daytype_gen = [df[df["hour"] == h]["gen"].mean() for h in range(24)]
    daytype_demand = {p.id: daily_demand(p.profile, p.daily_kwh) for p in cfg.participants}
    priority = {p.id: p.renta_priority for p in cfg.participants}
    beta = compute_coefficients(daytype_gen, daytype_demand, priority)
    sav = compute_savings(
        beta, daytype_gen, daytype_demand,
        cfg.prices.retail_eur_kwh, cfg.prices.compensation_eur_kwh,
    )
    daytype_sc_year = sum(s.self_consumed_kwh for s in sav.values()) * 365
    daytype_rate = daytype_sc_year / (sum(daytype_gen) * 365)

    assert summary.self_consumption_rate <= daytype_rate + 1e-9
