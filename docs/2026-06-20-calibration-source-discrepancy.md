---
type: analysis
status: open-decision
tags: [sreca, pv, calibration, open-meteo, pvgis, data-source]
created: 2026-06-20
related: [docs/2026-06-19-sreca-mvp-design.md]
---

# SRECA — PV calibration: source discrepancy (Open-Meteo ERA5 vs PVGIS SARAH2)

## Finding

The physical FV model (`sreca/forecast/pv.py`) is **physically correct** — every unit
test (solar position at solstices, transposition reduces to GHI at tilt 0, NOCT anchor,
STC power, temperature derate) passes. But the §5 calibration integration test (annual
sim vs PVGIS ±10 %) **fails**, and the miss decomposes cleanly into data, not bugs:

| Quantity | Model (Open-Meteo archive) | PVGIS canonical | Gap |
|---|---|---|---|
| In-plane irradiation POA | 1642 kWh/m²/yr | 1456 kWh/m²/yr | **+12.8 %** |
| Performance ratio PR | 0.839 | 0.795 | **+5.5 %** |
| Annual energy | 20 672 kWh/yr | 17 376 kWh/yr | **+19.0 %** |
| Specific yield | 1378 kWh/kWp | 1158 kWh/kWp | +19.0 % |
| Transposition gain POA/GHI | 1.148 (sane 1.10–1.20) | — | OK |

PVGIS API echo for `lat=43.16, lon=-6.09, 15 kWp, 35° south, loss=14`:
`radiation_db: PVGIS-SARAH2`, `meteo_db: ERA5`, `use_horizon: true`, window 2005–2020.

## Root causes

1. **Irradiance source (+12.8 % of the gap).** Open-Meteo archive serves **ERA5
   reanalysis** shortwave radiation; PVGIS serves **SARAH2 satellite** irradiance. ERA5
   has a documented positive bias over cloudy regions (cantábrico). PVGIS also applies
   **DEM horizon shading** — Teverga sits in a mountain valley, so terrain blocks low-sun
   hours; our model has no horizon term. Both push our POA above PVGIS.
2. **Loss model (+5.5 %).** Our PR (0.839) lumps only system losses (14 %) + NOCT
   temperature derate. PVGIS PR (0.795) additionally absorbs spectral, low-irradiance and
   other losses inside its 14 % nominal. Our loss model is lighter → PR too high.

## Spec anchor note

Spec §5 cites 16 700 kWh / yield 1114 / PR 0.765 (prior-session PVGIS lookup). The **live**
PVGIS API (2026-06-20) returns **17 376 kWh / yield 1158 / PR 0.795** at loss=14. The 1114
figure implies ~17 % loss. Minor; the spec anchor should be refreshed to the live value.

## Decision (RESOLVED 2026-06-20 — Pablo)

**Route A (ex-ante annual climatology) source = PVGIS TMY** (SARAH2 + DEM horizon, 0 €/no key).
Route B (D+1 forecast) stays Open-Meteo (PVGIS has no forecast). Rationale: most faithful for a
mountain-valley site, and the calibration test now measures the **model** against same-source
PVGIS rather than conflating model + irradiance source.

### Result after switching the fixture to PVGIS TMY
- Climatology fixture rebuilt from PVGIS TMY (`scripts/build_climatology_fixture.py`).
  Annual GHI horizontal 1313 kWh/m² (vs ERA5 1431 — confirms ~9 % ERA5 hot bias here).
- Model annual = **18 130 kWh** (yield 1209) vs PVGIS PVcalc **17 376** (yield 1158) → **+4.3 %**,
  inside ±10 %. Calibration test passes.
- Residual +4.3 % = our lighter loss model (system 14 % + NOCT temp only; PVGIS adds
  spectral/low-light inside its nominal). Acceptable MVP simplification (spec §5 "simple OK");
  closing it (Hay-Davies diffuse, spectral derate) is a fase-2 refinement, not a bug.
- Spec §5 anchor and `config/concejos/teverga.yaml` refreshed to live PVGIS (17 376/1158/0.795).
  The model clears ±10 % against **both** the original spec anchor (16 700 → +8.6 %) and the live
  value (17 376 → +4.3 %); the swap corrects a stale number, it does not widen a failing margin.

### Follow-up (fase 2, not blocking)
- If tighter than ±5 % is wanted: add spectral + low-irradiance loss terms, or Hay-Davies
  anisotropic diffuse transposition.
