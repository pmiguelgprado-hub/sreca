"""Resolve per-concejo data fixtures (committed climatology years).

Each concejo carries its own PVGIS-TMY climatology fixture so replicability is real, not just a
config swap: <concejo>_climatology_hourly.csv. Built one-time by scripts/build_climatology_fixture.py.
"""
from __future__ import annotations

from pathlib import Path

_FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def climatology_path(concejo: str) -> Path:
    """Path to a concejo's committed climatology year (may not exist for an un-built concejo)."""
    return _FIXTURES / f"{concejo.lower()}_climatology_hourly.csv"
