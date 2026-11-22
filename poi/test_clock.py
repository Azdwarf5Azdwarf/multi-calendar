"""The POI clock keeps the bounds named for it."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from poi.clock import locate, month_lengths, read, thirds, year_covering
from poi.sun import (
    PRECESSION_YEARS_PER_DEGREE,
    SUN_DEGREES_PER_DAY,
    TROPICAL_YEAR_SECONDS,
    precession_degrees,
    rotation_degrees,
)

STOCKHOLM = (59.3293, 18.0686)
SYDNEY = (-33.8688, 151.2093)


def unix_of(year: int, month: int, day: int, hour: int = 12) -> float:
    return datetime(year, month, day, hour, tzinfo=timezone.utc).timestamp()


def date_of(ordinal: int) -> str:
    return datetime.fromtimestamp(ordinal * 86400, timezone.utc).strftime("%Y-%m-%d")


class MonthShapeTests(unittest.TestCase):
    def test_common_year_is_the_named_shape(self) -> None:
        lengths = month_lengths(365)
        self.assertEqual(
            lengths,
            (17, 25, 32, 33, 32, 26, 17, 17, 26, 32, 33, 32, 26, 17),
        )
        self.assertEqual(sum(lengths), 365)
        self.assertEqual(lengths[0], 17)
        self.assertLessEqual(max(lengths), 33)
        self.assertEqual(lengths[3], 33)

    def test_leap_year_adds_the_day_to_month_two(self) -> None:
        self.assertEqual(
            month_lengths(366),
            (17, 26, 32, 33, 32, 26, 17, 17, 26, 32, 33, 32, 26, 17),
        )

    def test_opening_month_stays_inside_15_to_17_for_real_years(self) -> None:
        for days in (365, 366):
            opening = month_lengths(days)[0]
            self.assertGreaterEqual(opening, 15)
            self.assertLessEqual(opening, 17)

    def test_thirds_differ_by_at_most_one_day_and_cover_the_month(self) -> None:
        for length in range(15, 34):
            beginning, middle, end = thirds(length)
            self.assertEqual(beginning + middle + end, length)
            self.assertLessEqual(max(beginning, middle, end) - min(beginning, middle, end), 1)
        # A leftover day goes to the middle first.
        self.assertEqual(thirds(17), (6, 6, 5))
        self.assertEqual(thirds(33), (11, 11, 11))
        self.assertEqual(thirds(16), (5, 6, 5))

    def test_every_day_lands_in_exactly_one_month_and_one_third(self) -> None:
        lengths = month_lengths(365)
        seen = []
        for day in range(365):
            month, month_day, third, third_length = locate(day, lengths)
            seen.append((month, month_day, third))
            self.assertIn(third, ("beginning", "middle", "end"))
            self.assertGreaterEqual(third_length, 1)
        self.assertEqual(len(seen), len(set(seen)) + 0)
        self.assertEqual(seen[0], (1, 1, "beginning"))
        self.assertEqual(seen[16], (1, 17, "end"))  # month 1 is 17 days, index 0..16
        self.assertEqual(seen[17][0], 2)
        self.assertEqual(seen[-1][0], 14)


class TangentTests(unittest.TestCase):
    def test_stockholm_tangents_for_the_2026_high_sun(self) -> None:
        year = year_covering(unix_of(2026, 6, 21), *STOCKHOLM)
        self.assertEqual(date_of(year.beginning), "2025-12-16")
        self.assertEqual(date_of(year.high_sun), "2026-06-21")
        self.assertEqual(date_of(year.earlier_sunset), "2026-06-23")
        self.assertEqual(date_of(year.next_beginning), "2026-12-16")
        self.assertEqual(year.year_days, 365)

    def test_the_33_day_month_ends_before_the_high_sun(self) -> None:
        for place in (STOCKHOLM, SYDNEY):
            for stamp in (unix_of(2026, 4, 1), unix_of(2027, 1, 15)):
                year = year_covering(stamp, *place)
                lengths = year.lengths
                climb_end = sum(lengths[:4]) - 1  # last day index of month 4
                high_index = year.high_sun - year.beginning
                self.assertEqual(lengths[3], 33, place)
                self.assertLess(climb_end, high_index, (place, date_of(year.beginning), date_of(year.high_sun)))
                self.assertGreater(year.earlier_sunset, year.high_sun - 1)
                self.assertLess(year.earlier_sunset, year.next_beginning)
                self.assertIn(year.year_days, (365, 366))

    def test_sydney_opens_in_june_and_crests_in_december(self) -> None:
        year = year_covering(unix_of(2026, 11, 22), *SYDNEY)
        self.assertEqual(date_of(year.beginning), "2026-06-12")
        # The December solstice is on the morning of the 22nd in Sydney.
        self.assertEqual(date_of(year.high_sun), "2026-12-22")
        self.assertEqual(date_of(year.earlier_sunset), "2027-01-08")

    def test_polar_night_still_has_a_year(self) -> None:
        # Longyearbyen. The sun does not set in summer and does not rise in winter.
        year = year_covering(unix_of(2026, 6, 21), 78.2232, 15.6267)
        self.assertEqual(date_of(year.high_sun), "2026-06-21")
        self.assertEqual(year.earlier_sunset, year.high_sun)
        self.assertEqual(year.year_days, 365)
        reading = read(unix_of(2026, 6, 21), 78.2232, 15.6267)
        self.assertEqual(reading.yellow, 1.0)
        winter = read(unix_of(2026, 12, 21), 78.2232, 15.6267)
        self.assertEqual(winter.yellow, 0.0)

    def test_yellow_is_wider_at_the_high_sun_than_at_the_opening(self) -> None:
        opened = read(unix_of(2025, 12, 16), *STOCKHOLM)
        crest = read(unix_of(2026, 6, 21), *STOCKHOLM)
        self.assertGreater(crest.yellow, opened.yellow)
        self.assertGreater(crest.yellow, 0.7)
        self.assertLess(opened.yellow, 0.3)
        self.assertAlmostEqual(opened.yellow + opened.night, 1.0)

    def test_a_day_in_the_climb_is_the_long_month(self) -> None:
        # 2026-03-20 is inside the 33-day month that ends before the high sun.
        reading = read(unix_of(2026, 3, 20), *STOCKHOLM)
        self.assertEqual(reading.month, 4)
        self.assertEqual(reading.month_length, 33)
        self.assertLess(reading.ordinal, reading.high_sun)
        self.assertIn(reading.third, ("beginning", "middle", "end"))


class EpochTests(unittest.TestCase):
    def test_precession_is_one_degree_per_72_years_from_the_epoch(self) -> None:
        self.assertEqual(precession_degrees(0), 0.0)
        self.assertAlmostEqual(precession_degrees(72 * TROPICAL_YEAR_SECONDS), 1.0)
        self.assertEqual(PRECESSION_YEARS_PER_DEGREE, 72.0)

    def test_the_other_two_sky_rates(self) -> None:
        self.assertEqual(rotation_degrees(1), 15.0)
        self.assertEqual(rotation_degrees(24), 360.0)
        self.assertAlmostEqual(SUN_DEGREES_PER_DAY, 360.0 / 365.2425)

    def test_rejects_an_impossible_place(self) -> None:
        with self.assertRaises(ValueError):
            read(0, 91.0, 0.0)
        with self.assertRaises(ValueError):
            read(0, 0.0, 181.0)


if __name__ == "__main__":
    unittest.main()
