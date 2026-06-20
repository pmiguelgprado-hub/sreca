"""End-to-end wire smoke test (sreca.main) — spec §1 vertical slice.

run_rebalance runs the whole brain on the committed PVGIS-TMY climatology (no network) and
persists one readable run to SQLite: PVGIS → pv → demand → coefficients → savings → store.
"""
import pytest

from sreca.concejo import load_concejo
from sreca.store import db
from sreca import main


def test_run_rebalance_populates_a_readable_run(tmp_path):
    db_path = str(tmp_path / "sreca.sqlite")
    run_id = main.run_rebalance("teverga", db_path)

    conn = db.connect(db_path)

    # PV generation day-type persisted (24h, daytime generation > 0)
    gen = db.read_pv_forecast(conn, run_id)
    assert len(gen) == 24
    assert sum(gen) > 0

    # coefficients valid for every hour (Σ_i β_i,h = 1)
    beta = db.read_coefficients(conn, run_id)
    pids = {p.id for p in load_concejo("teverga").participants}
    assert set(beta) == pids
    for h in range(24):
        assert sum(beta[p][h] for p in pids) == pytest.approx(1.0)

    # savings present for every participant
    savings = db.read_savings(conn, run_id)
    assert set(savings) == pids
    assert all(s["self_consumed_kwh"] >= 0 for s in savings.values())

    # monthly ex-ante legal profile persisted (12 months, Σβ=1 per month/hour)
    schedule = db.read_ex_ante_schedule(conn, run_id)
    assert set(schedule) == set(range(1, 13))
    for month in (1, 7):
        for h in range(24):
            assert sum(schedule[month][p][h] for p in pids) == pytest.approx(1.0)


def test_run_rebalance_records_ex_ante_mode(tmp_path):
    db_path = str(tmp_path / "sreca.sqlite")
    run_id = main.run_rebalance("teverga", db_path)
    conn = db.connect(db_path)
    run = next(r for r in db.read_runs(conn) if r["run_id"] == run_id)
    assert run["coefficient_mode"] == "ex_ante"
    assert run["concejo"] == "Teverga"
