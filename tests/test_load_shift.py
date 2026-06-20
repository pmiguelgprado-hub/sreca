"""Tests for the flexible-load-shift recommender (sreca.optimize.load_shift) — spec §6, §9.1.

This is Route B (always legal, after the meter). The non-negotiable invariant (spec §9.1,
§10): it moves ONLY flexible loads (cold tank, cleaning ACS) toward the solar window. Milking
is non-flexible and must NEVER be relocated — the guard test fails if it is.
"""
import pytest

from sreca.optimize.load_shift import FlexibleLoad, recommend_flexible_load_shift


def _solar_day():
    # generation peaks midday (hours 11-14), zero at night
    return [0, 0, 0, 0, 0, 0, 1, 3, 6, 9, 12, 15, 16, 14, 11, 7, 4, 2, 0, 0, 0, 0, 0, 0]


def test_shifts_flexible_load_to_peak_generation_hours():
    gen = _solar_day()
    tank = FlexibleLoad(name="tanque_frio_leche", energy_kwh=4.0, duration_h=2)
    rec = recommend_flexible_load_shift([tank], gen)
    # the 2 highest-generation hours are 12 (16) and 11 (15)
    assert sorted(rec["tanque_frio_leche"]) == [11, 12]


def test_duration_respected():
    gen = _solar_day()
    acs = FlexibleLoad(name="acs_limpieza", energy_kwh=3.0, duration_h=3)
    rec = recommend_flexible_load_shift([acs], gen)
    assert len(rec["acs_limpieza"]) == 3


def test_recommended_hours_have_generation():
    gen = _solar_day()
    acs = FlexibleLoad(name="acs_limpieza", energy_kwh=3.0, duration_h=3)
    rec = recommend_flexible_load_shift([acs], gen)
    assert all(gen[h] > 0 for h in rec["acs_limpieza"])


def test_never_shifts_nonflexible_load():
    # INVARIANT GUARD (spec §9.1): milking is non-flexible → must not be relocated, ever.
    gen = _solar_day()
    milking = FlexibleLoad(name="ordeno", energy_kwh=5.0, duration_h=2, shiftable=False)
    tank = FlexibleLoad(name="tanque_frio_leche", energy_kwh=4.0, duration_h=2)
    rec = recommend_flexible_load_shift([milking, tank], gen)
    assert "ordeno" not in rec               # never appears as a moved load
    assert "tanque_frio_leche" in rec        # the flexible one is moved


def test_multiple_flexible_loads_each_recommended():
    gen = _solar_day()
    loads = [
        FlexibleLoad(name="tanque_frio_leche", energy_kwh=4.0, duration_h=2),
        FlexibleLoad(name="acs_limpieza", energy_kwh=3.0, duration_h=1),
    ]
    rec = recommend_flexible_load_shift(loads, gen)
    assert set(rec) == {"tanque_frio_leche", "acs_limpieza"}
