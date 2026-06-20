"""Physical FV production model (spec §5) — irradiance → kWh, physically traceable.

Pipeline per hour:
  1. solar_position    datetime+lat/lon → solar zenith & azimuth (NOAA algorithm)
  2. poa_irradiance    GHI/DNI/DHI + sun geometry → plane-of-array irradiance (isotropic)
  3. cell_temperature  POA + ambient → cell temp (NOCT model)
  4. dc_power          POA + cell temp → AC-side power (temperature derate + system losses)
  5. integrate         hourly energy → annual

Same model for both data routes (spec §4): only the irradiance *source* changes
(archive climatology vs forecast D+1), not the transformation.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import pandas as pd

from sreca.concejo import PV, Site

_REF_YEAR = 2021  # non-leap reference year for the 8760-h climatological year
_ALBEDO = 0.2     # ground reflectance (generic grass/soil)
_STC_IRRADIANCE = 1000.0  # W/m² reference


def solar_position(dt_utc: datetime, lat: float, lon: float) -> tuple[float, float]:
    """Solar zenith and azimuth (degrees) via the NOAA solar position algorithm.

    Azimuth measured clockwise from north (0=N, 90=E, 180=S, 270=W).
    """
    doy = dt_utc.timetuple().tm_yday
    hour = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    gamma = 2 * math.pi / 365 * (doy - 1 + (hour - 12) / 24)

    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.001480 * math.sin(3 * gamma)
    )

    time_offset = eqtime + 4 * lon  # minutes (UTC → tz term is 0)
    tst = hour * 60 + time_offset   # true solar time, minutes
    ha = math.radians(tst / 4 - 180)  # hour angle, radians

    lat_r = math.radians(lat)
    cos_zenith = math.sin(lat_r) * math.sin(decl) + math.cos(lat_r) * math.cos(decl) * math.cos(ha)
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith = math.acos(cos_zenith)

    sin_zenith = math.sin(zenith)
    if sin_zenith < 1e-6:  # sun at zenith — azimuth undefined, return south
        return math.degrees(zenith), 180.0
    sin_az = -math.cos(decl) * math.sin(ha) / sin_zenith
    cos_az = (math.sin(decl) - math.sin(lat_r) * cos_zenith) / (math.cos(lat_r) * sin_zenith)
    azimuth = (math.degrees(math.atan2(sin_az, cos_az)) + 360) % 360

    return math.degrees(zenith), azimuth


def poa_irradiance(
    ghi: float,
    dni: float,
    dhi: float,
    zenith_deg: float,
    sun_azimuth_deg: float,
    tilt_deg: float,
    surface_azimuth_deg: float,
    albedo: float = _ALBEDO,
) -> float:
    """Plane-of-array irradiance (W/m²) via the isotropic sky model (spec §5 step 2)."""
    zenith = math.radians(zenith_deg)
    tilt = math.radians(tilt_deg)
    az_diff = math.radians(sun_azimuth_deg - surface_azimuth_deg)

    cos_incidence = (
        math.cos(zenith) * math.cos(tilt)
        + math.sin(zenith) * math.sin(tilt) * math.cos(az_diff)
    )
    beam = dni * max(cos_incidence, 0.0)
    diffuse = dhi * (1 + math.cos(tilt)) / 2
    ground = ghi * albedo * (1 - math.cos(tilt)) / 2
    return beam + diffuse + ground


def cell_temperature(poa: float, t_amb: float, noct_c: float) -> float:
    """Cell temperature via the NOCT model (spec §5 step 3)."""
    return t_amb + poa * (noct_c - 20) / 800.0


def dc_power(
    poa: float,
    t_cell: float,
    kwp: float,
    gamma_pmp_per_c: float,
    system_losses: float,
) -> float:
    """Power output (kW) — linear irradiance, temperature derate, lumped losses (spec §5 step 4)."""
    temp_factor = 1 + gamma_pmp_per_c * (t_cell - 25)
    power = kwp * (poa / _STC_IRRADIANCE) * temp_factor * (1 - system_losses)
    return max(power, 0.0)


def hourly_energy(df: pd.DataFrame, site: Site, pv: PV) -> list[float]:
    """Hourly FV energy (kWh) for a climatology/forecast frame.

    Frame columns: month, day, hour, ghi_wm2, dni_wm2, dhi_wm2, temp_c.
    Horizon-agnostic: returns one value per row (8760 for a full year).
    """
    out: list[float] = []
    for row in df.itertuples(index=False):
        dt = datetime(_REF_YEAR, int(row.month), int(row.day), int(row.hour), tzinfo=timezone.utc)
        zenith, sun_az = solar_position(dt, site.lat, site.lon)
        poa = poa_irradiance(
            ghi=row.ghi_wm2, dni=row.dni_wm2, dhi=row.dhi_wm2,
            zenith_deg=zenith, sun_azimuth_deg=sun_az,
            tilt_deg=site.tilt_deg, surface_azimuth_deg=site.azimuth_deg,
        )
        t_cell = cell_temperature(poa, row.temp_c, pv.noct_c)
        power = dc_power(poa, t_cell, pv.kwp, pv.gamma_pmp_per_c, pv.system_losses)
        out.append(power * 1.0)  # × 1 h
    return out


def annual_energy(df: pd.DataFrame, site: Site, pv: PV) -> float:
    """Total annual FV energy (kWh/yr)."""
    return sum(hourly_energy(df, site, pv))
