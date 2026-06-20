"""Tests for per-household savings (sreca.optimize.savings) — spec §6.

Self-consumed energy is valued at the avoided retail price; allocated energy beyond a
participant's demand is grid excess, valued at the (low) compensation price. The two must
never be conflated (spec §6). β is passed explicitly here to isolate the savings math.
"""
import pytest

from sreca.optimize.savings import compute_savings

RETAIL, COMP = 0.20, 0.06


def test_pure_self_consumption_valued_at_retail():
    gen = [10.0]
    beta = {"a": [0.3]}            # allocated 3, demand 3 → no excess
    demand = {"a": [3.0]}
    s = compute_savings(beta, gen, demand, RETAIL, COMP)["a"]
    assert s.self_consumed_kwh == pytest.approx(3.0)
    assert s.excess_kwh == pytest.approx(0.0)
    assert s.eur_saved == pytest.approx(3.0 * RETAIL)


def test_excess_valued_at_compensation():
    gen = [10.0]
    beta = {"a": [0.6], "b": [0.4]}
    demand = {"a": [3.0], "b": [5.0]}   # a is over-allocated → 3 kWh excess
    res = compute_savings(beta, gen, demand, RETAIL, COMP)
    a = res["a"]
    assert a.self_consumed_kwh == pytest.approx(3.0)
    assert a.excess_kwh == pytest.approx(3.0)
    assert a.eur_saved == pytest.approx(3.0 * RETAIL + 3.0 * COMP)
    # b fully self-consumes its allocation, no excess
    assert res["b"].excess_kwh == pytest.approx(0.0)
    assert res["b"].eur_saved == pytest.approx(4.0 * RETAIL)


def test_energy_balance_self_consumed_plus_excess_equals_allocated():
    gen = [10.0, 8.0]
    beta = {"a": [0.6, 0.5], "b": [0.4, 0.5]}
    demand = {"a": [3.0, 5.0], "b": [5.0, 2.0]}
    res = compute_savings(beta, gen, demand, RETAIL, COMP)
    for p in demand:
        allocated = sum(beta[p][h] * gen[h] for h in range(len(gen)))
        assert res[p].self_consumed_kwh + res[p].excess_kwh == pytest.approx(allocated)


def test_returns_every_participant():
    gen = [5.0]
    beta = {"a": [0.5], "b": [0.5]}
    demand = {"a": [2.0], "b": [2.0]}
    res = compute_savings(beta, gen, demand, RETAIL, COMP)
    assert set(res) == {"a", "b"}
