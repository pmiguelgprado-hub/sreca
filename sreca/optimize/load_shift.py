"""Flexible-load-shift recommender — Route B (spec §6, always legal, after the meter).

Recommends running each FLEXIBLE load (cold-milk tank, cleaning ACS) during the hours of
highest expected PV generation, i.e. inside the solar window. This is the real synergy
(spec §9.1): the farm's milking is fixed at dawn/dusk and stays on the grid; only its
flexible thermal-inertia loads are nudged into the sun.

Invariant (guarded by tests): a load with ``shiftable=False`` (e.g. milking) is NEVER
relocated — it does not appear in the recommendation at all.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FlexibleLoad:
    name: str
    energy_kwh: float
    duration_h: int
    shiftable: bool = True  # milking would be False — never moved (invariant §9.1)


def recommend_flexible_load_shift(
    loads: list[FlexibleLoad],
    gen: list[float],
) -> dict[str, list[int]]:
    """Map each *shiftable* load to the ``duration_h`` hours with the most PV generation.

    Non-shiftable loads are excluded entirely (never relocated). Hours are returned in
    ascending order.
    """
    hours_by_gen = sorted(range(len(gen)), key=lambda h: (-gen[h], h))
    rec: dict[str, list[int]] = {}
    for load in loads:
        if not load.shiftable:
            continue  # invariant §9.1: never move a non-flexible load
        chosen = sorted(hours_by_gen[: load.duration_h])
        rec[load.name] = chosen
    return rec
