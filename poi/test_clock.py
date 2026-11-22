"""The POI clock keeps the bounds named for it."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from poi.clock import (
    BASES,
    BINARY_WIDTH,
    BLOCKS,
    EARTH_TURN,
    FOLD,
    LETTER_ROW,
    LETTERS,
    RIGHT_ANGLE,
    COMPANY,
    HOURLY_PAY,
    SUNDAY,
    SECTIONS,
    SPOKEN_BASE,
    WORLD_GAP,
    MixedBases,
    day_face,
    locate,
    minutes_ahead,
    month_lengths,
    parallel,
    read,
    sun_stand,
    thirds,
    year_covering,
)
from poi.sun import (
    PRECESSION_YEARS_PER_DEGREE,
    SUN_DEGREES_PER_DAY,
    TROPICAL_YEAR_SECONDS,
    day_length_hours,
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


class GapTests(unittest.TestCase):
    def test_the_same_human_hour_is_a_different_sun(self) -> None:
        zone = ZoneInfo("Europe/Stockholm")
        believed = 12 + 18 / 60
        bus = sun_stand(datetime(2026, 11, 22, 12, 18, tzinfo=zone).timestamp(), *STOCKHOLM)
        summer = sun_stand(datetime(2026, 6, 21, 12, 18, tzinfo=zone).timestamp(), *STOCKHOLM)

        bus_gap = minutes_ahead(bus.sun_hours, believed)
        summer_gap = minutes_ahead(summer.sun_hours, believed)

        # 22 Nov 2026, the bus at 12:18 CET: the sun says 12:44, 10° up.
        self.assertAlmostEqual(bus.sun_hours, 12 + 44 / 60, delta=1 / 60)
        self.assertAlmostEqual(bus_gap, 26, delta=1)
        self.assertAlmostEqual(bus.altitude, 10.0, delta=0.5)
        self.assertGreater(bus.gap_minutes, 10)

        # The same label on 21 Jun 2026 is CEST, and the sun says 11:28, 54° up.
        self.assertAlmostEqual(summer.sun_hours, 11 + 28 / 60, delta=1 / 60)
        self.assertAlmostEqual(summer_gap, -50, delta=1)
        self.assertAlmostEqual(summer.altitude, 53.7, delta=0.5)
        self.assertLess(summer.gap_minutes, 0)

        self.assertGreater(summer.altitude - bus.altitude, 40)
        self.assertGreater(abs(bus_gap - summer_gap), 60)

    def test_five_human_minutes_barely_move_the_sun(self) -> None:
        zone = ZoneInfo("Europe/Stockholm")
        believed_early = 12 + 13 / 60
        early = sun_stand(datetime(2026, 11, 22, 12, 13, tzinfo=zone).timestamp(), *STOCKHOLM)
        later = sun_stand(datetime(2026, 11, 22, 12, 18, tzinfo=zone).timestamp(), *STOCKHOLM)
        self.assertAlmostEqual(
            minutes_ahead(early.sun_hours, believed_early),
            minutes_ahead(later.sun_hours, 12 + 18 / 60),
            delta=0.2,
        )

    def test_a_reading_carries_the_stand(self) -> None:
        unix = datetime(2026, 11, 22, 11, 18, tzinfo=timezone.utc).timestamp()
        reading = read(unix, *STOCKHOLM)
        stand = sun_stand(unix, *STOCKHOLM)
        self.assertEqual(reading.stand, stand)
        self.assertGreater(reading.stand.altitude, 0)

    def test_at_munkedal_the_sun_agrees_with_the_phone(self) -> None:
        # Bus 860 on 22 Nov 2026, actual board: Munkedal 12:12, Uddevalla 12:44.
        # Near 11.7° E the season's fast sun cancels the longitude, so the
        # phone and the sun share the minute. The bus did not.
        munkedal = (58.482, 11.678)
        phone = datetime(2026, 11, 22, 12, 18, tzinfo=ZoneInfo("Europe/Stockholm"))
        stand = sun_stand(phone.timestamp(), *munkedal)
        gap = minutes_ahead(stand.sun_hours, 12 + 18 / 60)
        self.assertAlmostEqual(gap, 1, delta=2)


class FaceTests(unittest.TestCase):
    def _at_mean_hour(self, unix: float, hour: float) -> float:
        stand = sun_stand(unix, *STOCKHOLM)
        return unix + minutes_ahead(hour, stand.mean_hours) / 60.0 * 3600.0

    def test_sunrise_opens_at_33_and_sunset_is_zero(self) -> None:
        noon = datetime(2026, 6, 21, 12, tzinfo=timezone.utc).timestamp()
        stand = sun_stand(noon, *STOCKHOLM)
        length_hours = day_length_hours(stand.declination, STOCKHOLM[0])
        noon_mean = 12.0 - stand.gap_minutes / 60.0
        sunrise = noon_mean - length_hours / 2.0
        sunset = noon_mean + length_hours / 2.0
        night_middle = (sunset + (24.0 - length_hours) / 2.0) % 24.0

        opened = day_face(self._at_mean_hour(noon, sunrise), *STOCKHOLM)
        closed = day_face(self._at_mean_hour(noon, sunset - 1.0 / 60.0), *STOCKHOLM)
        deep = day_face(self._at_mean_hour(noon, night_middle), *STOCKHOLM)

        self.assertEqual(opened.half, "day")
        self.assertAlmostEqual(opened.mark, 33.0, delta=0.5)
        self.assertEqual(opened.section, 1)
        self.assertEqual(closed.half, "day")
        self.assertAlmostEqual(closed.mark, 0.0, delta=0.5)
        self.assertEqual(deep.half, "night")
        self.assertAlmostEqual(deep.mark, -33.0, delta=1.0)
        self.assertLess(deep.section, 0)

    def test_the_reset_is_at_sunrise(self) -> None:
        noon = datetime(2026, 3, 20, 12, tzinfo=timezone.utc).timestamp()
        stand = sun_stand(noon, *STOCKHOLM)
        length_hours = day_length_hours(stand.declination, STOCKHOLM[0])
        sunrise = 12.0 - stand.gap_minutes / 60.0 - length_hours / 2.0
        before = day_face(self._at_mean_hour(noon, sunrise - 2.0 / 60.0), *STOCKHOLM)
        after = day_face(self._at_mean_hour(noon, sunrise + 2.0 / 60.0), *STOCKHOLM)
        self.assertEqual(before.half, "night")
        self.assertAlmostEqual(before.mark, 0.0, delta=0.4)
        self.assertEqual(after.half, "day")
        self.assertAlmostEqual(after.mark, 33.0, delta=0.4)

    def test_day_and_night_keep_the_same_count_and_the_count_can_change(self) -> None:
        noon = datetime(2026, 6, 21, 12, tzinfo=timezone.utc).timestamp()
        ordinary = day_face(noon, *STOCKHOLM)
        wider = day_face(noon, *STOCKHOLM, sections=40)
        self.assertEqual(ordinary.sections, SECTIONS)
        self.assertEqual(wider.sections, 40)
        self.assertEqual(ordinary.half, "day")
        self.assertGreater(ordinary.mark, 0)

    def test_polar_day_stays_open_and_polar_night_stays_down(self) -> None:
        summer = day_face(datetime(2026, 6, 21, 12, tzinfo=timezone.utc).timestamp(), 78.2232, 15.6267)
        winter = day_face(datetime(2026, 12, 21, 12, tzinfo=timezone.utc).timestamp(), 78.2232, 15.6267)
        self.assertEqual(summer.half, "polar_day")
        self.assertEqual(summer.mark, 33.0)
        self.assertEqual(winter.half, "polar_night")
        self.assertEqual(winter.mark, -33.0)

    def test_a_reading_carries_the_face(self) -> None:
        unix = datetime(2026, 11, 22, 11, 18, tzinfo=timezone.utc).timestamp()
        reading = read(unix, *STOCKHOLM)
        self.assertEqual(reading.face, day_face(unix, *STOCKHOLM))
        self.assertEqual(reading.face.half, "day")
        self.assertGreater(reading.face.mark, 0.0)


class BaseTests(unittest.TestCase):
    def test_the_square_on_earth_is_four_right_angles(self) -> None:
        self.assertEqual(RIGHT_ANGLE, 90)
        self.assertEqual(EARTH_TURN, 360)

    def test_sixty_six_is_the_gap_beside_binary_not_the_spoken_base(self) -> None:
        self.assertIsNone(SPOKEN_BASE)
        self.assertEqual(BINARY_WIDTH, 2**6)
        self.assertEqual(BASES["beside"], 66)
        self.assertEqual(WORLD_GAP, 2)
        self.assertEqual(WORLD_GAP, 1 + 1)
        self.assertEqual(SECTIONS * 2, 66)
        lengths = month_lengths(365)
        self.assertEqual(sum(1 for length in lengths if length == 33), 2)

    def test_a_sentence_keeps_one_base(self) -> None:
        self.assertEqual(parallel(("ten meters", "count")), (("ten meters", "count"),))
        with self.assertRaises(MixedBases):
            parallel(("ten meters", "count"), ("seconds", "time"))

    def test_a_number_is_said_with_its_base(self) -> None:
        self.assertEqual(COMPANY, ("Grok", "Knalle", "Toth", "Konshu", "Nisaba"))
        self.assertEqual(
            SUNDAY,
            ("Sena", "James", "Cigri", "Snöbär", "Carl von Linné", "Anjouvis", "Edith"),
        )
        self.assertEqual(parallel(("sixty", "time")), (("sixty", "time"),))
        with self.assertRaises(ValueError):
            parallel(("sixty", ""))

    def test_twenty_one_is_three_folds_and_the_spoken_letters(self) -> None:
        self.assertEqual(FOLD, 7)
        self.assertEqual(LETTERS, 21)
        self.assertEqual(LETTERS, 3 * FOLD)
        self.assertEqual(LETTER_ROW, 22)
        self.assertEqual(BASES["letters"], LETTERS)
        self.assertIsNone(BLOCKS)
        self.assertEqual(parallel(("the letters", "letters")), (("the letters", "letters"),))

    def test_hourly_pay_is_base_ten_for_a_base_sixty_hour(self) -> None:
        self.assertEqual(BASES["time"], 60)
        self.assertEqual(BASES["count"], 10)
        self.assertEqual(HOURLY_PAY, (("the hour", "time"), ("the pay", "count")))
        with self.assertRaises(MixedBases):
            parallel(*HOURLY_PAY)


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
