"""Dashboard data layer — pure, testable (streamlit-fidelity: data layer separate from view).

Reads the latest persisted run from SQLite and shapes it for display. No Streamlit imports
here, so it unit-tests without a UI runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from sreca.concejo import load_concejo
from sreca.optimize.load_shift import recommend_flexible_load_shift
from sreca.report import AnnualSummary, annual_summary
from sreca.store import db

# Same climatology source main.py runs the year on (PVGIS TMY, committed). Single source of truth.
_CLIMATOLOGY = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "teverga_climatology_hourly.csv"


@dataclass(frozen=True)
class DashboardData:
    run_id: str
    concejo: str
    coefficient_mode: str
    gen: list[float]                       # 24h generation day-type (kWh)
    demand: dict[str, list[float]]         # participant -> 24h demand (kWh)
    coefficients: dict[str, list[float]]   # participant -> 24h β (mean day-type summary)
    savings: dict[str, dict]               # participant -> {self_consumed_kwh, excess_kwh, eur_saved}
    load_shift: dict[str, list[int]]       # flexible load -> recommended solar-window hours (Route B)
    ex_ante_schedule: dict[int, dict[str, list[float]]]  # month -> participant -> 24h β (legal §4)
    annual: AnnualSummary | None           # honest full-year headline (8760h chain, not day-type×365)


@dataclass(frozen=True)
class CommunityKPIs:
    generation_kwh: float          # total FV generation over the day-type
    savings_eur: float             # total community savings (€)
    self_consumption_rate: float   # Σ self_consumed / Σ generation (0..1)
    demand_coverage: float         # Σ self_consumed / Σ demand (0..1)


def community_kpis(d: DashboardData) -> CommunityKPIs:
    """Headline community metrics derived from a run (pure)."""
    total_gen = sum(d.gen)
    total_sc = sum(s["self_consumed_kwh"] for s in d.savings.values())
    total_dem = sum(sum(v) for v in d.demand.values())
    return CommunityKPIs(
        generation_kwh=total_gen,
        savings_eur=sum(s["eur_saved"] for s in d.savings.values()),
        self_consumption_rate=(total_sc / total_gen) if total_gen else 0.0,
        demand_coverage=(total_sc / total_dem) if total_dem else 0.0,
    )


def _load_shift_recommendation(concejo: str, gen: list[float]) -> dict[str, list[int]]:
    """Route B (spec §6, §9.1): recommend running flexible loads in the solar window.

    Computed on read from the persisted generation + the concejo's flexible loads (no extra
    DB table). Flexible-load sizing in config is PLACEHOLDER pending real farm data.
    """
    try:
        cfg = load_concejo(concejo.lower())
    except FileNotFoundError:
        return {}
    flex = [fl for p in cfg.participants for fl in p.flexible_loads]
    return recommend_flexible_load_shift(flex, gen)


def _annual_headline(concejo: str) -> AnnualSummary | None:
    """Honest full-year figures (8760h chain). Computed on read from config + climatology."""
    try:
        cfg = load_concejo(concejo.lower())
    except FileNotFoundError:
        return None
    if not _CLIMATOLOGY.exists():
        return None
    return annual_summary(cfg, pd.read_csv(_CLIMATOLOGY))


def load_dashboard_data(db_path: str) -> DashboardData | None:
    """Load the most recent run, or None if the database has no runs."""
    conn = db.connect(db_path)
    run_id = db.latest_run_id(conn)
    if run_id is None:
        return None
    run = next(r for r in db.read_runs(conn) if r["run_id"] == run_id)
    gen = db.read_pv_forecast(conn, run_id)
    return DashboardData(
        run_id=run_id,
        concejo=run["concejo"],
        coefficient_mode=run["coefficient_mode"],
        gen=gen,
        demand=db.read_demand(conn, run_id),
        coefficients=db.read_coefficients(conn, run_id),
        savings=db.read_savings(conn, run_id),
        load_shift=_load_shift_recommendation(run["concejo"], gen),
        ex_ante_schedule=db.read_ex_ante_schedule(conn, run_id),
        annual=_annual_headline(run["concejo"]),
    )
