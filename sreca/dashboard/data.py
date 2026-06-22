"""Persisted-run data layer — pure, testable (streamlit-fidelity: data separate from view).

Reads the latest persisted run from SQLite and shapes it for display. No Streamlit imports
here, so it unit-tests without a UI runtime.

Note (2026-06-22): the interactive cockpit (``app.py``) now recomputes live from config +
climatology via ``analytics.cockpit_bundle`` and does not read the DB, so ``load_dashboard_data``
/ ``community_kpis`` / ``DashboardData`` serve the CLI batch-and-store path (``main.run_rebalance``)
and its tests, not the live view. ``territory_context`` below is still used by the cockpit. This
DB path is kept deliberately as the persistence/seed layer (a scheduled run, or a future API),
not dead code.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from sreca.concejo import ConcejoConfig, load_concejo
from sreca.datasets import climatology_path
from sreca.optimize.load_shift import recommend_flexible_load_shift
from sreca.report import AnnualSummary, annual_summary
from sreca.store import db


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


# CE IMPLEMENTA / RDL 7/2026 target band: municipios de reto demográfico (< 5.000 hab).
# It is the public funding rationale this project addresses (see docs/2026-06-22-official-data-sources.md).
RETO_DEMOGRAFICO_MAX_HAB = 5000


@dataclass(frozen=True)
class TerritoryContext:
    concejo: str
    population: int | None
    population_year: int | None
    area_km2: float | None
    density_hab_km2: float | None
    is_reto_demografico: bool       # municipio < 5.000 hab (CE IMPLEMENTA / reto demográfico)


def territory_context(cfg: ConcejoConfig) -> TerritoryContext:
    """Demographic framing for a concejo, straight from its config (pure, no DB).

    Ties the app to its funding rationale: the pilot concejos are small, low-density
    municipios de reto demográfico. Density is derived in the config; never fabricated here.
    """
    pop = cfg.population
    return TerritoryContext(
        concejo=cfg.concejo,
        population=pop,
        population_year=cfg.population_year,
        area_km2=cfg.area_km2,
        density_hab_km2=cfg.density_hab_km2,
        is_reto_demografico=(pop is not None and pop < RETO_DEMOGRAFICO_MAX_HAB),
    )


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


@lru_cache(maxsize=16)
def _annual_headline(concejo: str) -> AnnualSummary | None:
    """Honest full-year figures (8760h chain) for a concejo, memoised per process.

    The 8760h solar-position loop is the one heavy computation here. Streamlit reruns the script
    on every interaction (e.g. the month selectbox), so without this cache each rerun would
    recompute the whole year. Each concejo has its own committed climatology fixture (static),
    so per-process memoisation by concejo is safe and correct."""
    try:
        cfg = load_concejo(concejo.lower())
    except FileNotFoundError:
        return None
    clim = climatology_path(concejo)
    if not clim.exists():
        return None
    return annual_summary(cfg, pd.read_csv(clim))


def load_dashboard_data(db_path: str, concejo: str | None = None) -> DashboardData | None:
    """Load the latest run, or the latest run for ``concejo`` (display name) if given.

    Returns None if there is no matching run.
    """
    conn = db.connect(db_path)
    run_id = db.latest_run_id(conn, concejo)
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
