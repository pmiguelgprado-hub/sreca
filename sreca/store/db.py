"""SQLite persistence for SRECA run artefacts (spec §7).

Stdlib sqlite3 only (0 € stack). One row per (run, participant, hour) for the time series;
the dashboard reads these back. DB files are gitignored (*.sqlite) — may hold consumption
data (RGPD trigger → local hosting, spec §12).
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS participants (
    id TEXT PRIMARY KEY, concejo TEXT, perfil TEXT,
    renta_priority INTEGER, flexible_loads TEXT
);
CREATE TABLE IF NOT EXISTS forecast_runs (
    run_id TEXT PRIMARY KEY, fecha TEXT, concejo TEXT, coefficient_mode TEXT
);
CREATE TABLE IF NOT EXISTS pv_forecast (
    run_id TEXT, hour INTEGER, gen_kwh REAL
);
CREATE TABLE IF NOT EXISTS demand_forecast (
    run_id TEXT, participant_id TEXT, hour INTEGER, dem_kwh REAL
);
CREATE TABLE IF NOT EXISTS coefficients (
    run_id TEXT, participant_id TEXT, hour INTEGER, beta REAL
);
CREATE TABLE IF NOT EXISTS savings (
    run_id TEXT, participant_id TEXT,
    self_consumed_kwh REAL, excess_kwh REAL, eur_saved REAL
);
"""


def connect(path: str) -> sqlite3.Connection:
    return sqlite3.connect(path)


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def _field(obj: Any, name: str) -> float:
    """Read a field from either a dataclass (attr) or a dict (key)."""
    return getattr(obj, name) if hasattr(obj, name) else obj[name]


# --- writes ---------------------------------------------------------------

def insert_run(conn, run_id, fecha, concejo, coefficient_mode) -> None:
    conn.execute(
        "INSERT INTO forecast_runs VALUES (?,?,?,?)",
        (run_id, fecha, concejo, coefficient_mode),
    )
    conn.commit()


def insert_participants(conn, participants) -> None:
    conn.executemany(
        "INSERT OR REPLACE INTO participants VALUES (?,?,?,?,?)",
        [(p.id, getattr(p, "concejo", None), p.profile, p.renta_priority,
          json.dumps(p.flexible_loads)) for p in participants],
    )
    conn.commit()


def insert_pv_forecast(conn, run_id, gen: list[float]) -> None:
    conn.executemany(
        "INSERT INTO pv_forecast VALUES (?,?,?)",
        [(run_id, h, g) for h, g in enumerate(gen)],
    )
    conn.commit()


def insert_demand(conn, run_id, demand: dict[str, list[float]]) -> None:
    rows = [(run_id, pid, h, d) for pid, series in demand.items() for h, d in enumerate(series)]
    conn.executemany("INSERT INTO demand_forecast VALUES (?,?,?,?)", rows)
    conn.commit()


def insert_coefficients(conn, run_id, beta: dict[str, list[float]]) -> None:
    rows = [(run_id, pid, h, b) for pid, series in beta.items() for h, b in enumerate(series)]
    conn.executemany("INSERT INTO coefficients VALUES (?,?,?,?)", rows)
    conn.commit()


def insert_savings(conn, run_id, savings: dict[str, Any]) -> None:
    rows = [
        (run_id, pid, _field(s, "self_consumed_kwh"), _field(s, "excess_kwh"), _field(s, "eur_saved"))
        for pid, s in savings.items()
    ]
    conn.executemany("INSERT INTO savings VALUES (?,?,?,?,?)", rows)
    conn.commit()


# --- reads ----------------------------------------------------------------

def read_runs(conn) -> list[dict]:
    cur = conn.execute("SELECT run_id, fecha, concejo, coefficient_mode FROM forecast_runs")
    cols = ["run_id", "fecha", "concejo", "coefficient_mode"]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def latest_run_id(conn) -> str | None:
    """run_id of the most recently inserted run (by rowid), or None if empty."""
    row = conn.execute("SELECT run_id FROM forecast_runs ORDER BY rowid DESC LIMIT 1").fetchone()
    return row[0] if row else None


def read_pv_forecast(conn, run_id) -> list[float]:
    cur = conn.execute(
        "SELECT gen_kwh FROM pv_forecast WHERE run_id=? ORDER BY hour", (run_id,)
    )
    return [r[0] for r in cur.fetchall()]


def _read_series_by_participant(conn, table, run_id, value_col) -> dict[str, list[float]]:
    cur = conn.execute(
        f"SELECT participant_id, hour, {value_col} FROM {table} WHERE run_id=? ORDER BY participant_id, hour",
        (run_id,),
    )
    out: dict[str, list[float]] = {}
    for pid, _hour, val in cur.fetchall():
        out.setdefault(pid, []).append(val)
    return out


def read_demand(conn, run_id) -> dict[str, list[float]]:
    return _read_series_by_participant(conn, "demand_forecast", run_id, "dem_kwh")


def read_coefficients(conn, run_id) -> dict[str, list[float]]:
    return _read_series_by_participant(conn, "coefficients", run_id, "beta")


def read_savings(conn, run_id) -> dict[str, dict]:
    cur = conn.execute(
        "SELECT participant_id, self_consumed_kwh, excess_kwh, eur_saved FROM savings WHERE run_id=?",
        (run_id,),
    )
    return {
        pid: {"self_consumed_kwh": sc, "excess_kwh": ex, "eur_saved": eur}
        for pid, sc, ex, eur in cur.fetchall()
    }
