"""Per-household savings (spec §6).

Splits each participant's allocated generation (β_i,h · gen_h) into:
  • self-consumed = min(allocated, demand)  → valued at avoided RETAIL price
  • excess        = allocated − self-consumed → valued at the low COMPENSATION price
The two are never conflated (spec §6).

Anti-overclaim note (spec §6): ex-ante β optimized on *expected* demand underperforms
against *realized* demand. With synthetic data expected == realized so the gap collapses;
do not read these euros as the real-world figure once measured load curves arrive.
"""
from __future__ import annotations

from dataclasses import dataclass

from sreca.optimize.coefficients import self_consumed


@dataclass(frozen=True)
class Savings:
    self_consumed_kwh: float
    excess_kwh: float
    eur_saved: float


def compute_savings(
    beta: dict[str, list[float]],
    gen: list[float],
    demand: dict[str, list[float]],
    retail_eur_kwh: float,
    compensation_eur_kwh: float,
) -> dict[str, Savings]:
    """Self-consumed @retail + grid excess @compensation, per participant."""
    sc = self_consumed(beta, gen, demand)
    out: dict[str, Savings] = {}
    for p in demand:
        sc_kwh = sum(sc[p])
        allocated = sum(beta[p][h] * gen[h] for h in range(len(gen)))
        excess_kwh = allocated - sc_kwh
        eur = sc_kwh * retail_eur_kwh + excess_kwh * compensation_eur_kwh
        out[p] = Savings(self_consumed_kwh=sc_kwh, excess_kwh=excess_kwh, eur_saved=eur)
    return out
