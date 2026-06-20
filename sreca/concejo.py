"""Per-concejo config loader.

Single source of truth for a Comunidad Energética Local. Replicating to another
concejo = add a YAML under config/concejos/, no code change (spec §8, invariant §9.4).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from sreca.optimize.load_shift import FlexibleLoad

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "concejos"
_LEGAL_MODES = {"ex_ante", "ex_post_dynamic"}


@dataclass(frozen=True)
class Site:
    lat: float
    lon: float
    tilt_deg: float
    azimuth_deg: float


@dataclass(frozen=True)
class PV:
    kwp: float
    system_losses: float
    noct_c: float
    gamma_pmp_per_c: float


@dataclass(frozen=True)
class Prices:
    retail_eur_kwh: float
    compensation_eur_kwh: float


@dataclass(frozen=True)
class Legal:
    proximidad_max_m: float
    coefficient_mode: str


@dataclass(frozen=True)
class Participant:
    id: str
    profile: str
    renta_priority: int
    daily_kwh: float
    flexible_loads: list[FlexibleLoad]


@dataclass(frozen=True)
class ConcejoConfig:
    concejo: str
    site: Site
    pv: PV
    prices: Prices
    legal: Legal
    participants: list[Participant]


def load_concejo(name: str, config_dir: Path | None = None) -> ConcejoConfig:
    """Load and validate a concejo config by name (e.g. "teverga")."""
    base = config_dir or _CONFIG_DIR
    path = base / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No concejo config: {path}")

    raw = yaml.safe_load(path.read_text())

    legal = Legal(**raw["legal"])
    if legal.coefficient_mode not in _LEGAL_MODES:
        raise ValueError(
            f"coefficient_mode '{legal.coefficient_mode}' not in {_LEGAL_MODES}"
        )

    participants = [
        Participant(
            id=p["id"],
            profile=p["profile"],
            renta_priority=p["renta_priority"],
            daily_kwh=p["daily_kwh"],
            flexible_loads=[
                FlexibleLoad(name=f["name"], energy_kwh=f["energy_kwh"], duration_h=f["duration_h"])
                for f in (p.get("flexible_loads") or [])
            ],
        )
        for p in raw["participants"]
    ]

    return ConcejoConfig(
        concejo=raw["concejo"],
        site=Site(**raw["site"]),
        pv=PV(**raw["pv"]),
        prices=Prices(**raw["prices"]),
        legal=legal,
        participants=participants,
    )
