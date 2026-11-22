"""Day-level solar geometry for the POI clock. No third-party libraries."""

from __future__ import annotations

import math

# The sun is counted as up once its center is 0.833° below the horizon
# (refraction plus the sun's radius). That is the usual sunrise cut.
REFRACTION_DEG = 0.833

# Mean tropical year. The precession hook counts with this, from the Unix epoch.
TROPICAL_YEAR_DAYS = 365.2425
TROPICAL_YEAR_SECONDS = TROPICAL_YEAR_DAYS * 86400

# poi-world's three sky rates. Precession is Gobri's round figure: one degree
# in 72 years, not a swing of 72 degrees.
ROTATION_DEGREES_PER_HOUR = 15.0
PRECESSION_YEARS_PER_DEGREE = 72.0
SUN_DEGREES_PER_DAY = 360.0 / TROPICAL_YEAR_DAYS


def declination_and_equation_of_time(unix: float) -> tuple[float, float]:
    """Return (declination degrees, equation of time in minutes) at `unix`.

    Equation of time is positive when a sundial is ahead of a mean clock.
    The series is the usual low-precision solar one: fine for which day a
    turn falls on, not for aiming a telescope.
    """

    jd = unix / 86400.0 + 2440587.5
    t = (jd - 2451545.0) / 36525.0
    mean_long = (280.46646 + 36000.76983 * t + 0.0003032 * t * t) % 360.0
    anomaly_deg = (357.52911 + 35999.05029 * t - 0.0001537 * t * t) % 360.0
    anomaly = math.radians(anomaly_deg)
    center = (
        (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(anomaly)
        + (0.019993 - 0.000101 * t) * math.sin(2 * anomaly)
        + 0.000289 * math.sin(3 * anomaly)
    )
    true_long = math.radians((mean_long + center) % 360.0)
    obliquity = math.radians(23.439291 - 0.0130042 * t)
    decl = math.degrees(math.asin(math.sin(obliquity) * math.sin(true_long)))
    ecc = 0.016708634 - 0.000042037 * t
    y = math.tan(obliquity / 2.0) ** 2
    mean = math.radians(mean_long)
    eot = 4.0 * math.degrees(
        y * math.sin(2 * mean)
        - 2 * ecc * math.sin(anomaly)
        + 4 * ecc * y * math.sin(anomaly) * math.cos(2 * mean)
        - 0.5 * y * y * math.sin(4 * mean)
        - 1.25 * ecc * ecc * math.sin(2 * anomaly)
    )
    return decl, eot


def noon_altitude(decl_deg: float, lat_deg: float) -> float:
    """Altitude of the sun at meridian transit, in degrees above the horizon."""

    lat = math.radians(lat_deg)
    dec = math.radians(decl_deg)
    sin_alt = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec)
    sin_alt = min(1.0, max(-1.0, sin_alt))
    return math.degrees(math.asin(sin_alt))


def day_length_hours(decl_deg: float, lat_deg: float) -> float:
    """Hours between sunrise and sunset. 24 in polar day, 0 in polar night."""

    lat = math.radians(lat_deg)
    dec = math.radians(decl_deg)
    cos_lat = math.cos(lat)
    cos_dec = math.cos(dec)
    if abs(cos_lat) < 1e-12 or abs(cos_dec) < 1e-12:
        return 24.0 if noon_altitude(decl_deg, lat_deg) > 0 else 0.0
    cos_ha = (
        math.sin(math.radians(-REFRACTION_DEG)) - math.sin(lat) * math.sin(dec)
    ) / (cos_lat * cos_dec)
    if cos_ha <= -1.0:
        return 24.0
    if cos_ha >= 1.0:
        return 0.0
    hour_angle = math.degrees(math.acos(min(1.0, max(-1.0, cos_ha))))
    return 2.0 * hour_angle / 15.0


def sunset_hour(decl_deg: float, eot_minutes: float, lat_deg: float) -> float | None:
    """Local mean solar hour of sunset, or None when the sun does not set.

    Noon of the mean sun is 12:00. The equation of time shifts the real sun
    off that noon, which is why the earliest sunset is not the solstice.
    """

    length = day_length_hours(decl_deg, lat_deg)
    if length <= 0.0 or length >= 24.0:
        return None
    noon = 12.0 - eot_minutes / 60.0
    return noon + length / 2.0


def yellow_fraction(decl_deg: float, lat_deg: float) -> float:
    """Share of the day the sun is up. This is the yellow bar."""

    return day_length_hours(decl_deg, lat_deg) / 24.0


def rotation_degrees(hours: float) -> float:
    """Sky rotation. poi-world counts this as 15 degrees an hour."""

    return ROTATION_DEGREES_PER_HOUR * hours


def precession_degrees(unix: float) -> float:
    """Star drift since the Unix epoch, in degrees.

    One degree takes 72 tropical years. At unix 0 the hook sits on 0.
    """

    years = unix / TROPICAL_YEAR_SECONDS
    return years / PRECESSION_YEARS_PER_DEGREE
