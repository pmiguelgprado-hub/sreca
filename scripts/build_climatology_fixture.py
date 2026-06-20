"""Build the Teverga climatological-year irradiance fixture (one-time, network).

Route A (ex-ante annual profile) source = **PVGIS TMY** (decision 2026-06-20):
SARAH2 satellite irradiance + DEM horizon shading, window 2005–2020, also 0 €/no key.
This is the faithful climatology for a mountain-valley site; the §5 calibration test
then measures the MODEL against same-source PVGIS, not a source discrepancy.

(Route B — D+1 forecast — uses Open-Meteo, a separate ingest path; PVGIS has no forecast.)

Writes an 8760-row standard year to tests/fixtures/teverga_climatology_hourly.csv.
The committed CSV is what tests mock against (spec §10: no network in tests).

Usage:  python scripts/build_climatology_fixture.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

LAT, LON = 43.16, -6.09
OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "teverga_climatology_hourly.csv"


def main() -> int:
    print("fetching PVGIS TMY (SARAH2 + horizon) ...", file=sys.stderr)
    r = requests.get(
        "https://re.jrc.ec.europa.eu/api/v5_2/tmy",
        params={"lat": LAT, "lon": LON, "usehorizon": 1, "outputformat": "json"},
        timeout=120,
    )
    r.raise_for_status()
    hourly = r.json()["outputs"]["tmy_hourly"]
    assert len(hourly) == 8760, f"expected 8760 TMY hours, got {len(hourly)}"

    rows = []
    annual_ghi = 0.0
    for rec in hourly:
        ts = rec["time(UTC)"]          # "YYYYMMDD:HHMM"
        month, day, hour = int(ts[4:6]), int(ts[6:8]), int(ts[9:11])
        ghi, dni, dhi, temp = rec["G(h)"], rec["Gb(n)"], rec["Gd(h)"], rec["T2m"]
        annual_ghi += ghi              # W/m² × 1h = Wh/m²
        rows.append(f"{month},{day},{hour},{ghi:.2f},{dni:.2f},{dhi:.2f},{temp:.2f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("month,day,hour,ghi_wm2,dni_wm2,dhi_wm2,temp_c\n" + "\n".join(rows) + "\n")
    print(f"wrote {OUT} ({len(rows)} rows)", file=sys.stderr)
    print(f"sanity: annual GHI on horizontal = {annual_ghi/1000:.0f} kWh/m²/yr", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
