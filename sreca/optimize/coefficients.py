"""Reparto-coefficient optimizer — water-filling + equity (spec §6).

Computes the legal sharing coefficients β_i,h (one per participant per hour, Σ_i β_i,h = 1)
that maximize the collective self-consumption rate. Horizon-agnostic: feed a single day-type
hour or a full 8760-h year — the per-hour rule is identical.

Two regimes per hour:
  • surplus (gen ≥ Σ demand): cover every participant's demand, then split the leftover by
    equity weight (the leftover only earns excess compensation, so it goes to lower income).
  • scarcity (gen < Σ demand): fill demand in priority order (lower income first) until the
    generation is exhausted → all generation is self-consumed; equity breaks the tie.

Self-consumption is min(allocated, demand); anything allocated beyond demand is grid excess.
"""
from __future__ import annotations

_EPS = 1e-12


def _equity_weights(priority: dict[str, int]) -> dict[str, float]:
    total = sum(priority.values())
    if total <= 0:
        n = len(priority)
        return {p: 1.0 / n for p in priority}
    return {p: priority[p] / total for p in priority}


def _allocate_hour(gen_h: float, demand_h: dict[str, float], priority: dict[str, int]) -> dict[str, float]:
    """Return β_i for one hour (Σ_i β_i = 1)."""
    weights = _equity_weights(priority)

    if gen_h <= _EPS:
        # no generation to share; coefficients still defined (Σ=1) by equity weight
        return dict(weights)

    total_demand = sum(demand_h.values())

    if total_demand <= gen_h:
        # surplus: cover all demand, distribute leftover by equity weight
        leftover = gen_h - total_demand
        allocated = {p: demand_h[p] + leftover * weights[p] for p in demand_h}
    else:
        # scarcity: fill by priority (higher renta_priority first), then by id for determinism
        order = sorted(demand_h, key=lambda p: (-priority[p], p))
        allocated = {p: 0.0 for p in demand_h}
        remaining = gen_h
        for p in order:
            take = min(demand_h[p], remaining)
            allocated[p] = take
            remaining -= take
            if remaining <= _EPS:
                break

    return {p: allocated[p] / gen_h for p in demand_h}


def compute_coefficients(
    gen: list[float],
    demand: dict[str, list[float]],
    priority: dict[str, int],
) -> dict[str, list[float]]:
    """β_i,h for the whole horizon. Σ_i β_i,h = 1 ∀h."""
    horizon = len(gen)
    beta: dict[str, list[float]] = {p: [0.0] * horizon for p in demand}
    for h in range(horizon):
        demand_h = {p: demand[p][h] for p in demand}
        alloc = _allocate_hour(gen[h], demand_h, priority)
        for p in demand:
            beta[p][h] = alloc[p]
    return beta


def self_consumed(
    beta: dict[str, list[float]],
    gen: list[float],
    demand: dict[str, list[float]],
) -> dict[str, list[float]]:
    """Energy each participant actually self-consumes: min(β_i,h · gen_h, demand_i,h)."""
    return {
        p: [min(beta[p][h] * gen[h], demand[p][h]) for h in range(len(gen))]
        for p in demand
    }
