"""Pure analytics backbone for the interactive cockpit (DB-free, recomputable live).

The dashboard reads precomputed runs from SQLite for the default view, but the interactive
controls (parameter sliders, uploaded consumption curves) must recompute on the fly without
touching the DB. Everything here is a pure function of a ConcejoConfig + its climatology year,
so it unit-tests without a UI runtime and memoises cleanly by input. The honest annual engine
stays sreca.report.annual_summary; this module adds the override + chart-shaping layer around it.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pandas as pd

from sreca.concejo import ConcejoConfig
from sreca.forecast.pv import hourly_energy
from sreca.report import AnnualSummary


@dataclass(frozen=True)
class EnergyBalance:
    self_consumed_kwh: float    # solar consumed by the community
    exported_kwh: float         # solar surplus exported to the grid
    grid_import_kwh: float      # demand not covered by solar (bought from the grid)


def apply_overrides(
    cfg: ConcejoConfig,
    *,
    kwp: float | None = None,
    retail_eur_kwh: float | None = None,
    compensation_eur_kwh: float | None = None,
    daily_kwh: dict[str, float] | None = None,
) -> ConcejoConfig:
    """Return a copy of ``cfg`` with the cockpit-tunable fields overridden (frozen-safe).

    Only the knobs a user controls (plant size, prices, per-household daily consumption);
    every other field is carried through unchanged. The input config is never mutated.
    """
    pv = cfg.pv if kwp is None else dataclasses.replace(cfg.pv, kwp=kwp)

    prices = cfg.prices
    if retail_eur_kwh is not None or compensation_eur_kwh is not None:
        prices = dataclasses.replace(
            cfg.prices,
            retail_eur_kwh=cfg.prices.retail_eur_kwh if retail_eur_kwh is None else retail_eur_kwh,
            compensation_eur_kwh=(
                cfg.prices.compensation_eur_kwh
                if compensation_eur_kwh is None
                else compensation_eur_kwh
            ),
        )

    participants = cfg.participants
    if daily_kwh:
        participants = [
            dataclasses.replace(p, daily_kwh=daily_kwh.get(p.id, p.daily_kwh))
            for p in cfg.participants
        ]

    return dataclasses.replace(cfg, pv=pv, prices=prices, participants=participants)


def monthly_generation(cfg: ConcejoConfig, climatology: pd.DataFrame) -> dict[int, float]:
    """Total FV generation (kWh) per calendar month over the climatology year."""
    df = climatology.assign(_gen=hourly_energy(climatology, cfg.site, cfg.pv))
    return {int(m): float(g) for m, g in df.groupby("month")["_gen"].sum().items()}


def generation_heatmap(cfg: ConcejoConfig, climatology: pd.DataFrame) -> pd.DataFrame:
    """Mean hourly generation (kWh) as a month×hour matrix (12 rows × 24 cols).

    The "when does this site actually produce" view: rows = months 1..12, cols = hours 0..23.
    """
    df = climatology.assign(_gen=hourly_energy(climatology, cfg.site, cfg.pv))
    table = df.groupby(["month", "hour"])["_gen"].mean().unstack("hour")
    return table.reindex(index=range(1, 13), columns=range(24), fill_value=0.0)


def energy_balance(annual: AnnualSummary) -> EnergyBalance:
    """Split the year's energy into solar self-consumed, solar exported, and grid-imported."""
    return EnergyBalance(
        self_consumed_kwh=annual.self_consumed_kwh,
        exported_kwh=annual.excess_kwh,
        grid_import_kwh=max(annual.demand_kwh - annual.self_consumed_kwh, 0.0),
    )


def demand_from_csv(df: pd.DataFrame) -> dict[str, list[float]]:
    """Parse an uploaded consumption-curve CSV into per-participant 24h day-type demand.

    Expected columns: ``hour`` (0..23, each exactly once, any order) plus one numeric column
    per participant id holding that hour's kWh. Returns {participant_id: [24 hourly kWh]}.
    Raises ValueError on a malformed file so the UI can surface a clear message instead of
    silently mis-plotting.
    """
    by_lower = {str(c).lower(): c for c in df.columns}
    if "hour" not in by_lower:
        raise ValueError("El CSV debe incluir una columna 'hour' con las horas 0..23.")
    hour_col = by_lower["hour"]

    try:
        hours = df[hour_col].astype(int)
    except (ValueError, TypeError) as exc:
        raise ValueError("La columna 'hour' debe ser numérica (0..23).") from exc
    if sorted(hours.tolist()) != list(range(24)):
        raise ValueError("La columna 'hour' debe contener las 24 horas 0..23, cada una una vez.")

    ordered = df.set_index(hour_col).reindex(range(24))
    out: dict[str, list[float]] = {}
    for c in df.columns:
        if c == hour_col:
            continue
        try:
            out[str(c)] = [float(v) for v in ordered[c].tolist()]
        except (ValueError, TypeError) as exc:
            raise ValueError(f"La columna '{c}' tiene valores no numéricos.") from exc
    if not out:
        raise ValueError("El CSV no tiene ninguna columna de participante además de 'hour'.")
    return out
