"""Annual headline figures over the full 8760 h chain (spec §1, honesty guard).

The dashboard's day-type charts are a *visual* mean day; the headline numbers a grant jury
reads (kWh/año, €/año, % autoconsumo) must instead come from the full-resolution year, because
collective self-consumption = Σ min(gen, demand) and min is concave — averaging the days first
and then taking min overstates it (Jensen). The optimizer modules are horizon-agnostic, so this
is composition, not new logic: real hourly generation × the (synthetic, tiled) daily demand.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sreca.concejo import ConcejoConfig
from sreca.forecast.demand import daily_demand
from sreca.forecast.pv import hourly_energy
from sreca.optimize.coefficients import compute_coefficients
from sreca.optimize.savings import Savings, compute_savings


@dataclass(frozen=True)
class AnnualSummary:
    gen_kwh: float                       # total FV generation over the year
    demand_kwh: float                    # total community demand over the year
    self_consumed_kwh: float             # Σ collectively self-consumed
    excess_kwh: float                    # Σ exported to grid
    community_eur: float                 # Σ savings (avoided retail + compensation)
    self_consumption_rate: float         # self_consumed / generation (0..1)
    demand_coverage: float               # self_consumed / demand (0..1)
    participants: dict[str, Savings]     # per-household annual figures


def annual_summary(
    cfg: ConcejoConfig,
    climatology: pd.DataFrame,
    demand_override: dict[str, list[float]] | None = None,
) -> AnnualSummary:
    """Honest annual figures for ``cfg`` over the full climatology year (8760 h).

    ``demand_override`` (participant_id -> 24h day-type kWh) replaces the synthetic demand
    curves, so an uploaded consumption profile flows through the same honest annual chain.
    """
    gen = hourly_energy(climatology, cfg.site, cfg.pv)
    hours = climatology["hour"].astype(int).tolist()
    day_demand = demand_override or {
        p.id: daily_demand(p.profile, p.daily_kwh) for p in cfg.participants
    }
    demand = {pid: [day_demand[pid][h] for h in hours] for pid in day_demand}
    base_priority = {p.id: p.renta_priority for p in cfg.participants}
    priority = {pid: base_priority.get(pid, 2) for pid in day_demand}

    beta = compute_coefficients(gen, demand, priority)
    sav = compute_savings(
        beta, gen, demand, cfg.prices.retail_eur_kwh, cfg.prices.compensation_eur_kwh
    )

    gen_kwh = sum(gen)
    demand_kwh = sum(sum(v) for v in demand.values())
    self_consumed_kwh = sum(s.self_consumed_kwh for s in sav.values())
    excess_kwh = sum(s.excess_kwh for s in sav.values())
    community_eur = sum(s.eur_saved for s in sav.values())

    return AnnualSummary(
        gen_kwh=gen_kwh,
        demand_kwh=demand_kwh,
        self_consumed_kwh=self_consumed_kwh,
        excess_kwh=excess_kwh,
        community_eur=community_eur,
        self_consumption_rate=(self_consumed_kwh / gen_kwh) if gen_kwh else 0.0,
        demand_coverage=(self_consumed_kwh / demand_kwh) if demand_kwh else 0.0,
        participants=sav,
    )
