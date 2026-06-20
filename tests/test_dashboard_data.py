"""Tests for the dashboard data layer (sreca.dashboard.data) — pure, testable.

The Streamlit view (app.py) stays thin; all read/shape logic lives here and is unit-tested
(streamlit-fidelity lesson: pure data layer + thin view).
"""
from sreca import main
from sreca.dashboard import data
from sreca.store import db


def test_load_dashboard_data_from_populated_db(tmp_path):
    db_path = str(tmp_path / "sreca.sqlite")
    run_id = main.run_rebalance("teverga", db_path)

    d = data.load_dashboard_data(db_path)
    assert d is not None
    assert d.run_id == run_id
    assert d.concejo == "Teverga"
    assert len(d.gen) == 24
    assert sum(d.gen) > 0
    assert len(d.savings) == 3
    assert all("eur_saved" in s for s in d.savings.values())
    assert len(d.demand) == 3


def test_dashboard_data_recommends_flexible_loads_in_solar_window(tmp_path):
    # Route B wired into the dashboard (the corrected-synergy thesis): flexible loads are
    # recommended for the highest-generation hours; non-flexible (milking) never appears.
    db_path = str(tmp_path / "sreca.sqlite")
    main.run_rebalance("teverga", db_path)
    d = data.load_dashboard_data(db_path)
    assert "tanque_frio_leche" in d.load_shift
    assert "acs_limpieza" in d.load_shift
    assert "ordeno" not in d.load_shift
    for hours in d.load_shift.values():
        assert all(d.gen[h] > 0 for h in hours)  # inside the solar window


def test_load_dashboard_data_empty_db_returns_none(tmp_path):
    db_path = str(tmp_path / "empty.sqlite")
    conn = db.connect(db_path)
    db.init_schema(conn)
    assert data.load_dashboard_data(db_path) is None
