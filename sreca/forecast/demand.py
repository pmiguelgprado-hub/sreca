"""Synthetic, parametrizable demand curves per participant profile (spec §3, §4).

MVP uses rule-based synthetic shapes (decision #4: rules now, ML v2 gated). The shapes
deliberately encode the corrected synergy invariant (spec §9.1): the dairy farm's
NON-flexible base load (milking) peaks at dawn and dusk, OUTSIDE the solar window.
Flexible loads (cold tank, cleaning ACS) are modelled separately by load_shift, which is
where the "only flexible loads move" invariant is guarded.

Hour index = 0..23 (local clock). Profiles are normalized day-type shapes (Σ = 1.0),
scaled by a per-participant daily total → expected hourly demand.
"""
from __future__ import annotations

# Relative hourly weights (un-normalized); normalized on read. One representative day-type.
_PROFILE_WEIGHTS: dict[str, list[float]] = {
    # Elderly, home through the day: morning rise, real midday presence, evening peak.
    "residencial_mayor_diurno": [
        0.2, 0.2, 0.2, 0.2, 0.2, 0.3,   # 00-05 night base
        0.6, 1.0, 1.0, 0.7, 0.7, 0.8,   # 06-11 morning
        1.0, 1.0, 1.0, 0.7, 0.6, 0.7,   # 12-17 midday presence
        0.9, 1.2, 1.2, 1.0, 0.6, 0.3,   # 18-23 evening peak
    ],
    # Dairy farm NON-flexible base: milking at dawn (06-07) and dusk (18-19); low midday.
    "ganadero_lacteo": [
        0.3, 0.3, 0.3, 0.3, 0.4, 0.7,   # 00-05 farmhouse base + pre-milking
        1.5, 1.5, 0.7, 0.5, 0.4, 0.4,   # 06-11 MORNING MILKING peak, then low
        0.4, 0.4, 0.4, 0.4, 0.6, 0.9,   # 12-17 low solar-window base
        1.5, 1.5, 0.7, 0.4, 0.3, 0.3,   # 18-23 EVENING MILKING peak
    ],
}


def profile_shape(profile: str) -> list[float]:
    """Normalized 24-hour day-type shape (Σ = 1.0) for a participant profile."""
    weights = _PROFILE_WEIGHTS[profile]  # KeyError on unknown profile
    total = sum(weights)
    return [w / total for w in weights]


def daily_demand(profile: str, daily_kwh: float) -> list[float]:
    """Expected hourly demand (kWh) for a day, scaled to ``daily_kwh``."""
    return [w * daily_kwh for w in profile_shape(profile)]
