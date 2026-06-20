"""Dashboard data layer — pure, testable (streamlit-fidelity: data layer separate from view).

Reads the latest persisted run from SQLite and shapes it for display. No Streamlit imports
here, so it unit-tests without a UI runtime.
"""
from __future__ import annotations

from dataclasses import dataclass

from sreca.store import db


@dataclass(frozen=True)
class DashboardData:
    run_id: str
    concejo: str
    coefficient_mode: str
    gen: list[float]                       # 24h generation day-type (kWh)
    demand: dict[str, list[float]]         # participant -> 24h demand (kWh)
    coefficients: dict[str, list[float]]   # participant -> 24h β
    savings: dict[str, dict]               # participant -> {self_consumed_kwh, excess_kwh, eur_saved}


def load_dashboard_data(db_path: str) -> DashboardData | None:
    """Load the most recent run, or None if the database has no runs."""
    conn = db.connect(db_path)
    run_id = db.latest_run_id(conn)
    if run_id is None:
        return None
    run = next(r for r in db.read_runs(conn) if r["run_id"] == run_id)
    return DashboardData(
        run_id=run_id,
        concejo=run["concejo"],
        coefficient_mode=run["coefficient_mode"],
        gen=db.read_pv_forecast(conn, run_id),
        demand=db.read_demand(conn, run_id),
        coefficients=db.read_coefficients(conn, run_id),
        savings=db.read_savings(conn, run_id),
    )
