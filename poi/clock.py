"""The POI clock.

Unix time stays the count underneath. This clock reads a place and a unix
second and lays the sun's year on top: two bars, three tangents, fourteen
months, the slow star hook, and the gap between the clock a human believes
and the time the sun is actually keeping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from poi.sun import (
    altitude,
    azimuth,
    declination_and_equation_of_time,
    precession_degrees,
    sunset_hour,
    yellow_fraction,
)

# Fourteen is the count that keeps the opening month at 17 days and the
# longest month at 33, and still adds up to the year.
MONTHS_IN_YEAR = 14

# Pins for the bar's speed, before the lengths are rounded to whole days.
# Pinning the quiet end at 16 is what lands the opening month on 17, inside
# the 15-to-17 band, once the year is filled. Nothing is allowed past 33.
QUIET_DAYS = 16
RACING_DAYS = 33
FLOOR_DAYS = 15
CAP_DAYS = 33

# Sunset turns are kept only when they fall this close to the solstice they
# belong to. Further away they are equation-of-time wiggles, not the year's turn.
TANGENT_WINDOW_DAYS = 45

THIRDS = ("beginning", "middle", "end")


@dataclass(frozen=True)
class DaySky:
    ordinal: int
    declination: float
    sunset_hour: float | None
    yellow: float


@dataclass(frozen=True)
class Year:
    """One POI year at a place: from one beginning tangent to the next."""

    latitude: float
    longitude: float
    beginning: int
    high_sun: int
    earlier_sunset: int
    next_beginning: int

    @property
    def year_days(self) -> int:
        return self.next_beginning - self.beginning

    @property
    def lengths(self) -> tuple[int, ...]:
        return month_lengths(self.year_days)


@dataclass(frozen=True)
class SunStand:
    """Where the sun stands, read as a time.

    `mean_hours` is the even clock at this longitude. `sun_hours` is the
    time the real sun is keeping. `gap_minutes` is sun minus mean: positive
    when the sun says the moment is later than the even clock.
    """

    mean_hours: float
    sun_hours: float
    gap_minutes: float
    altitude: float
    azimuth: float
    declination: float


@dataclass(frozen=True)
class Reading:
    unix: float
    latitude: float
    longitude: float
    ordinal: int
    day_index: int
    year_days: int
    month: int
    month_day: int
    month_length: int
    third: str
    third_length: int
    yellow: float
    night: float
    beginning: int
    high_sun: int
    earlier_sunset: int
    precession_degrees: float
    lengths: tuple[int, ...]
    stand: SunStand


def solar_noon_unix(ordinal: int, longitude: float) -> float:
    """Unix time of mean solar noon on this UTC date, at this longitude."""

    return ordinal * 86400 + 12 * 3600 - longitude * 240.0


def day_ordinal(unix: float, longitude: float) -> int:
    """UTC date index of the mean-solar day that contains `unix`."""

    local = unix + longitude * 240.0
    return math.floor(local / 86400.0)


def sky_on(ordinal: int, latitude: float, longitude: float) -> DaySky:
    decl, eot = declination_and_equation_of_time(solar_noon_unix(ordinal, longitude))
    return DaySky(
        ordinal=ordinal,
        declination=decl,
        sunset_hour=sunset_hour(decl, eot, latitude),
        yellow=yellow_fraction(decl, latitude),
    )


def _speed_weights(n: int) -> list[float]:
    """Integral of |sin(2π t)| on each equal slice of the year.

    t = 0 is the beginning tangent, where the yellow bar is nearly still.
    The bar races twice a year, near the two equinoxes.
    """

    def accumulated(t: float) -> float:
        half = 2.0 * t
        cycles = math.floor(half + 1e-15)
        within = half - cycles
        return cycles / math.pi + (1.0 - math.cos(math.pi * within)) / (2.0 * math.pi)

    return [accumulated((i + 1) / n) - accumulated(i / n) for i in range(n)]


def month_lengths(year_days: int) -> tuple[int, ...]:
    """Whole-day month lengths for a tangent year of `year_days` days.

    The quiet end of the bar is pinned at 16 days and the racing end at 33.
    Whole days then put the opening month on 17. Rounding dust goes to the
    month that lost the most, and no month is allowed outside 15..33.
    """

    if year_days < 360 or year_days > 370:
        raise ValueError(f"a POI year of {year_days} days is outside 360..370")
    weights = _speed_weights(MONTHS_IN_YEAR)
    low = min(weights)
    high = max(weights)
    scale = (RACING_DAYS - QUIET_DAYS) / (high - low)
    base = QUIET_DAYS - scale * low
    raw = [base + scale * weight for weight in weights]
    lengths = [min(CAP_DAYS, max(FLOOR_DAYS, int(math.floor(value + 0.5)))) for value in raw]

    def add_key(index: int) -> tuple[float, int]:
        return (-(raw[index] - lengths[index]), index)

    def sub_key(index: int) -> tuple[float, int]:
        return (-(lengths[index] - raw[index]), index)

    guard = 0
    while sum(lengths) != year_days:
        guard += 1
        if guard > 10000:
            raise RuntimeError("month lengths could not be closed")
        if sum(lengths) < year_days:
            order = sorted(range(MONTHS_IN_YEAR), key=add_key)
            movable = next((index for index in order if lengths[index] < CAP_DAYS), None)
            if movable is None:
                raise RuntimeError("every month is already at 33 days")
            lengths[movable] += 1
        else:
            order = sorted(range(MONTHS_IN_YEAR), key=sub_key)
            movable = next((index for index in order if lengths[index] > FLOOR_DAYS), None)
            if movable is None:
                raise RuntimeError("every month is already at 15 days")
            lengths[movable] -= 1
    return tuple(lengths)


def thirds(length: int) -> tuple[int, int, int]:
    """Split one month into beginning, middle, end.

    The three parts differ by at most one day. A leftover day goes to the
    middle first, then to the beginning, then to the end.
    """

    if length < 3:
        raise ValueError(f"a month of {length} days cannot hold three parts")
    base, remainder = divmod(length, 3)
    parts = [base, base, base]
    for step in range(remainder):
        parts[(1, 0, 2)[step]] += 1
    return parts[0], parts[1], parts[2]


def locate(day_index: int, lengths: tuple[int, ...]) -> tuple[int, int, str, int]:
    """Return (month 1..14, month day 1..n, third name, third length)."""

    if day_index < 0 or day_index >= sum(lengths):
        raise ValueError(f"day {day_index} is outside a year of {sum(lengths)} days")
    cursor = day_index
    for month, length in enumerate(lengths, start=1):
        if cursor < length:
            beginning, middle, end = thirds(length)
            month_day = cursor + 1
            if month_day <= beginning:
                return month, month_day, "beginning", beginning
            if month_day <= beginning + middle:
                return month, month_day, "middle", middle
            return month, month_day, "end", end
        cursor -= length
    raise RuntimeError("locate fell through")


def _extrema(values: list[float]) -> tuple[list[int], list[int]]:
    """Indices of local minima and local maxima.

    On a flat bottom or top, the day kept is the last day of the plateau:
    the day after which the value finally leaves.
    """

    lows: list[int] = []
    highs: list[int] = []
    last = len(values) - 1
    for index in range(1, last):
        previous = values[index - 1]
        current = values[index]
        nxt = values[index + 1]
        if current <= previous and current < nxt:
            lows.append(index)
        elif current >= previous and current > nxt:
            highs.append(index)
    return lows, highs


def _closest(indices: list[int], anchor: int, window: int) -> int | None:
    near = [index for index in indices if abs(index - anchor) <= window]
    if not near:
        return None
    # Closest to the anchor. If two sit equally far, take the later day.
    return min(near, key=lambda index: (abs(index - anchor), -index))


def year_covering(unix: float, latitude: float, longitude: float) -> Year:
    """The POI year that contains `unix` at this place."""

    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"latitude {latitude} is outside -90..90")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"longitude {longitude} is outside -180..180")

    center = day_ordinal(unix, longitude)
    first = center - 500
    count = 1000
    days = [sky_on(first + offset, latitude, longitude) for offset in range(count)]
    decl = [day.declination for day in days]
    sunset = [day.sunset_hour for day in days]
    decl_lows, decl_highs = _extrema(decl)

    # North winter is the low December sun. South winter is the low June sun.
    # Those are the min and the max of declination, one of each per year.
    if latitude >= 0.0:
        winter_hits = decl_lows
        summer_hits = decl_highs
    else:
        winter_hits = decl_highs
        summer_hits = decl_lows

    sun_lows, sun_highs = _sunset_turns(sunset)

    beginnings: list[int] = []
    for winter in winter_hits:
        turn = _closest(sun_lows, winter, TANGENT_WINDOW_DAYS)
        beginnings.append(first + (winter if turn is None else turn))
    beginnings = sorted(set(beginnings))
    if len(beginnings) < 2:
        raise RuntimeError("could not find two beginning tangents around this instant")

    opened = None
    for index, beginning in enumerate(beginnings[:-1]):
        nxt = beginnings[index + 1]
        if beginning <= center < nxt:
            opened = beginning
            closed = nxt
            break
    if opened is None:
        raise RuntimeError("this instant sits outside the tangents that were found")

    high = None
    for summer in summer_hits:
        ordinal = first + summer
        if opened < ordinal < closed:
            high = ordinal
            break
    if high is None:
        raise RuntimeError("this POI year has no high sun")

    end_turn = _closest(sun_highs, high - first, TANGENT_WINDOW_DAYS)
    earlier = high if end_turn is None else first + end_turn
    if not opened < earlier < closed:
        earlier = high

    return Year(
        latitude=latitude,
        longitude=longitude,
        beginning=opened,
        high_sun=high,
        earlier_sunset=earlier,
        next_beginning=closed,
    )


def _sunset_turns(sunset: list[float | None]) -> tuple[list[int], list[int]]:
    """Local minima and maxima of sunset hour, skipping days with no sunset."""

    lows: list[int] = []
    highs: list[int] = []
    for index in range(1, len(sunset) - 1):
        previous, current, nxt = sunset[index - 1], sunset[index], sunset[index + 1]
        if previous is None or current is None or nxt is None:
            continue
        if current <= previous and current < nxt:
            lows.append(index)
        elif current >= previous and current > nxt:
            highs.append(index)
    return lows, highs


def _wrap_hours(delta: float) -> float:
    """Fold an hour difference into the short way around the day, -12 to 12."""

    return (delta + 12.0) % 24.0 - 12.0


def sun_stand(unix: float, latitude: float, longitude: float) -> SunStand:
    """The sun's place at this instant, written as the time the sun is keeping."""

    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"latitude {latitude} is outside -90..90")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"longitude {longitude} is outside -180..180")
    declination, equation = declination_and_equation_of_time(unix)
    mean_hours = (unix / 3600.0 + longitude / 15.0) % 24.0
    sun_hours = (mean_hours + equation / 60.0) % 24.0
    hour_angle = (sun_hours - 12.0) * 15.0
    return SunStand(
        mean_hours=mean_hours,
        sun_hours=sun_hours,
        gap_minutes=equation,
        altitude=altitude(declination, latitude, hour_angle),
        azimuth=azimuth(declination, latitude, hour_angle),
        declination=declination,
    )


def minutes_ahead(sun_hours: float, believed_hours: float) -> float:
    """Minutes the sun is ahead of a clock a human believes.

    Positive means the sun says this moment is later. Negative means the sun
    says it is earlier. The two clocks can carry the same label, 12:18, on
    two different days and still disagree by different amounts.
    """

    return _wrap_hours(sun_hours - believed_hours) * 60.0


def read(unix: float, latitude: float, longitude: float) -> Reading:
    """Read the POI clock at one unix second and one place."""

    year = year_covering(unix, latitude, longitude)
    ordinal = day_ordinal(unix, longitude)
    day_index = ordinal - year.beginning
    lengths = year.lengths
    month, month_day, third, third_length = locate(day_index, lengths)
    sky = sky_on(ordinal, latitude, longitude)
    stand = sun_stand(unix, latitude, longitude)
    return Reading(
        unix=unix,
        latitude=latitude,
        longitude=longitude,
        ordinal=ordinal,
        day_index=day_index,
        year_days=year.year_days,
        month=month,
        month_day=month_day,
        month_length=lengths[month - 1],
        third=third,
        third_length=third_length,
        yellow=sky.yellow,
        night=1.0 - sky.yellow,
        beginning=year.beginning,
        high_sun=year.high_sun,
        earlier_sunset=year.earlier_sunset,
        precession_degrees=precession_degrees(unix),
        lengths=lengths,
        stand=stand,
    )
