"""Tests for the reparto-coefficient optimizer (sreca.optimize.coefficients) — spec §6, §10.

Water-filling maximizes the collective self-consumption rate; in scarcity the tie is broken
by equity (lower income = higher renta_priority served first — the social mission). These are
the non-negotiable invariants (spec §9): Σ_i β_i,h = 1, energy conservation, equity in scarcity.
"""
import pytest

from sreca.optimize import coefficients as co

# 3 synthetic participants; higher priority = lower income = served first
PRIORITY = {"granja": 1, "mayor_a": 3, "mayor_b": 3}


def _self_consumed_total(beta, gen, demand):
    sc = co.self_consumed(beta, gen, demand)
    return sum(sum(v) for v in sc.values())


def test_betas_sum_to_one_each_hour():
    gen = [0.0, 5.0, 20.0]            # zero / scarce / surplus hours
    demand = {
        "granja":  [1.0, 4.0, 3.0],
        "mayor_a": [0.5, 3.0, 4.0],
        "mayor_b": [0.5, 3.0, 4.0],
    }
    beta = co.compute_coefficients(gen, demand, PRIORITY)
    for h in range(len(gen)):
        assert sum(beta[p][h] for p in demand) == pytest.approx(1.0)


def test_surplus_hour_meets_all_demand():
    # gen ≥ Σ demand → every participant fully self-consumes their demand
    gen = [20.0]
    demand = {"granja": [3.0], "mayor_a": [4.0], "mayor_b": [4.0]}
    beta = co.compute_coefficients(gen, demand, PRIORITY)
    sc = co.self_consumed(beta, gen, demand)
    assert sc["granja"][0] == pytest.approx(3.0)
    assert sc["mayor_a"][0] == pytest.approx(4.0)
    assert sc["mayor_b"][0] == pytest.approx(4.0)


def test_scarcity_achieves_full_self_consumption():
    # gen < Σ demand → all generation is self-consumed (nothing spilled)
    gen = [5.0]
    demand = {"granja": [4.0], "mayor_a": [3.0], "mayor_b": [3.0]}
    beta = co.compute_coefficients(gen, demand, PRIORITY)
    assert _self_consumed_total(beta, gen, demand) == pytest.approx(5.0)


def test_equity_higher_priority_served_first_in_scarcity():
    # scarce hour: low-income (priority 3) participants get more than the farm (priority 1)
    gen = [5.0]
    demand = {"granja": [4.0], "mayor_a": [4.0], "mayor_b": [4.0]}
    beta = co.compute_coefficients(gen, demand, PRIORITY)
    alloc = {p: beta[p][0] * gen[0] for p in demand}
    assert alloc["mayor_a"] > alloc["granja"]
    assert alloc["mayor_b"] > alloc["granja"]


def test_energy_conservation():
    gen = [0.0, 5.0, 8.0, 20.0]
    demand = {
        "granja":  [1.0, 4.0, 2.0, 3.0],
        "mayor_a": [0.5, 3.0, 3.0, 4.0],
        "mayor_b": [0.5, 3.0, 3.0, 4.0],
    }
    beta = co.compute_coefficients(gen, demand, PRIORITY)
    total_sc = _self_consumed_total(beta, gen, demand)
    assert total_sc <= sum(gen) + 1e-9
    assert total_sc <= sum(sum(v) for v in demand.values()) + 1e-9


def test_zero_generation_hour_betas_valid_no_self_consumption():
    gen = [0.0]
    demand = {"granja": [2.0], "mayor_a": [1.0], "mayor_b": [1.0]}
    beta = co.compute_coefficients(gen, demand, PRIORITY)
    assert sum(beta[p][0] for p in demand) == pytest.approx(1.0)
    assert _self_consumed_total(beta, gen, demand) == pytest.approx(0.0)


def test_horizon_agnostic_single_hour_and_day():
    # same function for 1 day-type hour or a full 24h horizon (spec §6)
    for H in (1, 24):
        gen = [10.0] * H
        demand = {"granja": [2.0] * H, "mayor_a": [3.0] * H, "mayor_b": [3.0] * H}
        beta = co.compute_coefficients(gen, demand, PRIORITY)
        assert all(len(beta[p]) == H for p in demand)
        for h in range(H):
            assert sum(beta[p][h] for p in demand) == pytest.approx(1.0)
