"""End-to-end orchestration — the SRECA vertical slice (spec §1).

run_rebalance ties the whole brain together on the PVGIS-TMY climatology and writes one
ex-ante run to SQLite for the dashboard to read:

    PVGIS climatology → pv (day-type) → demand (per participant) → coefficients
                      → savings → store/db

Route A persists both a representative mean day-type (summary) AND the monthly ex-ante legal
coefficient profile (schedule.build_ex_ante_schedule, spec §4/§6 — the artefact presented to
the distribuidora). Route B (load_shift) is computed on read by the dashboard from the
generation + the concejo's flexible loads (placeholder sizing).
"""
from __future__ import annotations

import datetime as _dt
import uuid
from pathlib import Path

import pandas as pd

from sreca.concejo import PV, Site, load_concejo
from sreca.forecast import pv as pv_mod
from sreca.forecast.demand import daily_demand
from sreca.optimize.coefficients import compute_coefficients
from sreca.optimize.savings import compute_savings
from sreca.optimize.schedule import build_ex_ante_schedule
from sreca.store import db

_DEFAULT_CLIMATOLOGY = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "teverga_climatology_hourly.csv"
)


def mean_generation_daytype(climatology: pd.DataFrame, site: Site, pv: PV) -> list[float]:
    """Representative 24h generation day-type: mean hourly energy across all days of the year."""
    df = climatology.copy()
    df["gen_kwh"] = pv_mod.hourly_energy(df, site, pv)
    return [df[df["hour"] == h]["gen_kwh"].mean() for h in range(24)]


def run_rebalance(
    concejo: str,
    db_path: str,
    climatology_path: str | Path = _DEFAULT_CLIMATOLOGY,
    run_id: str | None = None,
) -> str:
    """Run the slice for ``concejo`` and persist one ex-ante run to ``db_path``. Returns run_id."""
    cfg = load_concejo(concejo)
    if cfg.legal.coefficient_mode != "ex_ante":
        raise NotImplementedError(
            f"coefficient_mode '{cfg.legal.coefficient_mode}' is gated (ex_post_dynamic)"
        )

    climatology = pd.read_csv(climatology_path)
    gen = mean_generation_daytype(climatology, cfg.site, cfg.pv)
    demand = {p.id: daily_demand(p.profile, p.daily_kwh) for p in cfg.participants}
    priority = {p.id: p.renta_priority for p in cfg.participants}

    beta = compute_coefficients(gen, demand, priority)
    savings = compute_savings(
        beta, gen, demand, cfg.prices.retail_eur_kwh, cfg.prices.compensation_eur_kwh
    )

    # Route A legal artefact: the monthly ex-ante coefficient profile (spec §4, §6).
    schedule = build_ex_ante_schedule(climatology, cfg)

    run_id = run_id or uuid.uuid4().hex[:12]
    conn = db.connect(db_path)
    db.init_schema(conn)
    db.insert_participants(conn, cfg.participants)
    db.insert_run(conn, run_id, _dt.date.today().isoformat(), cfg.concejo, cfg.legal.coefficient_mode)
    db.insert_pv_forecast(conn, run_id, gen)
    db.insert_demand(conn, run_id, demand)
    db.insert_coefficients(conn, run_id, beta)
    db.insert_savings(conn, run_id, savings)
    db.insert_ex_ante_schedule(conn, run_id, schedule)
    return run_id


if __name__ == "__main__":  # pragma: no cover
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/local/sreca.sqlite"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    rid = run_rebalance("teverga", path)
    print(f"run {rid} written to {path}")
