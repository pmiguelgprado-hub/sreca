"""Ex-ante annual schedule assembler — Route A (spec §4, §6).

Builds the annual ex-ante coefficient profile presented to the distribuidora: one
representative 24h day-type per month, computed from the PVGIS-TMY climatology. This is the
legal artefact (TED/1247/2021, revisable ≥4 months — the profile is a single submission with
hourly + seasonal variation, not a daily change).

coefficient_mode:
  • ex_ante (MVP) — real logic here.
  • ex_post_dynamic — gated stub, no logic until the dedicated RD is in force → raises.
"""
from __future__ import annotations

import pandas as pd

from sreca.concejo import PV, ConcejoConfig, Site
from sreca.forecast import demand as demand_mod
from sreca.forecast import pv as pv_mod
from sreca.optimize.coefficients import compute_coefficients


def monthly_generation_daytypes(
    climatology: pd.DataFrame, site: Site, pv: PV
) -> dict[int, list[float]]:
    """Average hourly FV generation across the days of each month → a 24h day-type per month."""
    df = climatology.copy()
    df["gen_kwh"] = pv_mod.hourly_energy(df, site, pv)
    daytypes: dict[int, list[float]] = {}
    for month in range(1, 13):
        m = df[df["month"] == month]
        daytypes[month] = [m[m["hour"] == h]["gen_kwh"].mean() for h in range(24)]
    return daytypes


def _demand_daytypes(cfg: ConcejoConfig) -> dict[str, list[float]]:
    """Expected 24h demand day-type per participant (month-independent in the MVP)."""
    return {
        p.id: demand_mod.daily_demand(p.profile, p.daily_kwh) for p in cfg.participants
    }


def build_ex_ante_schedule(
    climatology: pd.DataFrame, cfg: ConcejoConfig
) -> dict[int, dict[str, list[float]]]:
    """Assemble the annual ex-ante profile: {month: {participant_id: [β_h × 24]}}."""
    if cfg.legal.coefficient_mode != "ex_ante":
        raise NotImplementedError(
            f"coefficient_mode '{cfg.legal.coefficient_mode}' has no logic yet "
            "(ex_post_dynamic is gated to the pending RD)"
        )

    gen_daytypes = monthly_generation_daytypes(climatology, cfg.site, cfg.pv)
    demand_daytypes = _demand_daytypes(cfg)
    priority = {p.id: p.renta_priority for p in cfg.participants}

    schedule: dict[int, dict[str, list[float]]] = {}
    for month, gen in gen_daytypes.items():
        schedule[month] = compute_coefficients(gen, demand_daytypes, priority)
    return schedule
