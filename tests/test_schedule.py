"""Tests for the ex-ante annual schedule assembler (sreca.optimize.schedule) — spec §4, §6.

Route A: assemble the annual ex-ante coefficient profile (one 24h day-type per month) that
is presented to the distribuidora. Legal mode = ex_ante (TED/1247/2021); ex_post_dynamic is a
gated stub with no logic until the dedicated RD is in force (spec §6).
"""
import dataclasses

import pandas as pd
import pytest

from sreca.concejo import load_concejo
from sreca.optimize import schedule as sch

FIXTURE = "tests/fixtures/teverga_climatology_hourly.csv"


@pytest.fixture
def cfg():
    return load_concejo("teverga")


@pytest.fixture
def clim():
    return pd.read_csv(FIXTURE)


def test_generation_daytypes_12_months_24h(cfg, clim):
    daytypes = sch.monthly_generation_daytypes(clim, cfg.site, cfg.pv)
    assert set(daytypes) == set(range(1, 13))
    assert all(len(v) == 24 for v in daytypes.values())


def test_summer_daytype_generates_more_than_winter(cfg, clim):
    daytypes = sch.monthly_generation_daytypes(clim, cfg.site, cfg.pv)
    assert sum(daytypes[7]) > sum(daytypes[1])  # July > January


def test_schedule_betas_sum_to_one_each_month_hour(cfg, clim):
    schedule = sch.build_ex_ante_schedule(clim, cfg)
    pids = [p.id for p in cfg.participants]
    for month in range(1, 13):
        for h in range(24):
            assert sum(schedule[month][pid][h] for pid in pids) == pytest.approx(1.0)


def test_schedule_every_participant_24h_per_month(cfg, clim):
    schedule = sch.build_ex_ante_schedule(clim, cfg)
    for month in range(1, 13):
        for p in cfg.participants:
            assert len(schedule[month][p.id]) == 24


def test_ex_post_dynamic_mode_is_gated(cfg, clim):
    # the dynamic ex-post mode is not legal yet → no logic, must refuse
    gated_legal = dataclasses.replace(cfg.legal, coefficient_mode="ex_post_dynamic")
    gated_cfg = dataclasses.replace(cfg, legal=gated_legal)
    with pytest.raises(NotImplementedError):
        sch.build_ex_ante_schedule(clim, gated_cfg)
