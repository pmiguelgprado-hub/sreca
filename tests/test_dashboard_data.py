"""Tests for the dashboard data layer (sreca.dashboard.data) — pure, testable.

The Streamlit view (app.py) stays thin; all read/shape logic lives here and is unit-tested
(streamlit-fidelity lesson: pure data layer + thin view).
"""
import pytest

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


def test_dashboard_data_includes_monthly_ex_ante_profile(tmp_path):
    db_path = str(tmp_path / "sreca.sqlite")
    main.run_rebalance("teverga", db_path)
    d = data.load_dashboard_data(db_path)
    assert set(d.ex_ante_schedule) == set(range(1, 13))
    # each month: 24h β per participant, Σβ=1 per hour
    for h in range(24):
        assert sum(d.ex_ante_schedule[6][p][h] for p in d.ex_ante_schedule[6]) == pytest.approx(1.0)


def test_community_kpis(tmp_path):
    db_path = str(tmp_path / "sreca.sqlite")
    main.run_rebalance("teverga", db_path)
    d = data.load_dashboard_data(db_path)
    k = data.community_kpis(d)

    total_sc = sum(s["self_consumed_kwh"] for s in d.savings.values())
    total_dem = sum(sum(v) for v in d.demand.values())

    assert k.generation_kwh == pytest.approx(sum(d.gen))
    assert k.savings_eur == pytest.approx(sum(s["eur_saved"] for s in d.savings.values()))
    assert k.self_consumption_rate == pytest.approx(total_sc / sum(d.gen))
    assert k.demand_coverage == pytest.approx(total_sc / total_dem)
    assert 0 <= k.self_consumption_rate <= 1
    assert 0 <= k.demand_coverage <= 1


def test_load_dashboard_data_empty_db_returns_none(tmp_path):
    db_path = str(tmp_path / "empty.sqlite")
    conn = db.connect(db_path)
    db.init_schema(conn)
    assert data.load_dashboard_data(db_path) is None
