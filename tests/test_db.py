"""Tests for the SQLite store (sreca.store.db) — spec §7.

Round-trip persistence for the run artefacts the dashboard reads. In-memory DB, no files.
"""
import pytest

from sreca.store import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_schema(c)
    return c


def test_init_schema_creates_all_tables(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {r[0] for r in rows}
    assert {"participants", "forecast_runs", "pv_forecast",
            "demand_forecast", "coefficients", "savings"} <= names


def test_run_metadata_roundtrip(conn):
    db.insert_run(conn, run_id="r1", fecha="2026-06-20", concejo="Teverga",
                  coefficient_mode="ex_ante")
    runs = db.read_runs(conn)
    assert runs[0]["run_id"] == "r1"
    assert runs[0]["coefficient_mode"] == "ex_ante"


def test_pv_forecast_roundtrip_ordered_by_hour(conn):
    db.insert_run(conn, "r1", "2026-06-20", "Teverga", "ex_ante")
    gen = [0.0, 0.0, 1.5, 3.2, 2.1]
    db.insert_pv_forecast(conn, "r1", gen)
    assert db.read_pv_forecast(conn, "r1") == pytest.approx(gen)


def test_coefficients_roundtrip(conn):
    db.insert_run(conn, "r1", "2026-06-20", "Teverga", "ex_ante")
    beta = {"a": [0.6, 0.4], "b": [0.4, 0.6]}
    db.insert_coefficients(conn, "r1", beta)
    out = db.read_coefficients(conn, "r1")
    assert out["a"] == pytest.approx(beta["a"])
    assert out["b"] == pytest.approx(beta["b"])


def test_demand_roundtrip(conn):
    db.insert_run(conn, "r1", "2026-06-20", "Teverga", "ex_ante")
    dem = {"a": [1.0, 2.0], "b": [0.5, 0.5]}
    db.insert_demand(conn, "r1", dem)
    out = db.read_demand(conn, "r1")
    assert out["a"] == pytest.approx(dem["a"])


def test_savings_roundtrip(conn):
    db.insert_run(conn, "r1", "2026-06-20", "Teverga", "ex_ante")
    db.insert_savings(conn, "r1", {
        "a": {"self_consumed_kwh": 5.0, "excess_kwh": 1.0, "eur_saved": 1.06},
    })
    out = db.read_savings(conn, "r1")
    assert out["a"]["self_consumed_kwh"] == pytest.approx(5.0)
    assert out["a"]["eur_saved"] == pytest.approx(1.06)
