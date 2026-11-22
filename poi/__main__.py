"""Print one reading of the POI clock.

    python3 -m poi
    python3 -m poi 59.3293 18.0686
    python3 -m poi 59.3293 18.0686 1763812800
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone

from poi.clock import read

# The worked place in the notes: Stockholm.
STOCKHOLM = (59.3293, 18.0686)


def main(argv: list[str]) -> None:
    if len(argv) not in (0, 2, 3):
        raise SystemExit("usage: python3 -m poi [latitude longitude [unix]]")
    latitude, longitude = STOCKHOLM
    unix = time.time()
    if len(argv) >= 2:
        latitude = float(argv[0])
        longitude = float(argv[1])
    if len(argv) == 3:
        unix = float(argv[2])
    reading = read(unix, latitude, longitude)
    when = datetime.fromtimestamp(reading.unix, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def day(ordinal: int) -> str:
        return datetime.fromtimestamp(ordinal * 86400, timezone.utc).strftime("%Y-%m-%d")

    print(f"{when}")
    print(f"place  {reading.latitude:.4f}, {reading.longitude:.4f}")
    print(f"month  {reading.month} of {len(reading.lengths)}, day {reading.month_day} of {reading.month_length}")
    print(f"third  {reading.third} ({reading.third_length} days)")
    print(f"bars   yellow {reading.yellow:.3f}   night {reading.night:.3f}")
    print(f"hook   {reading.precession_degrees:.4f}° since the Unix epoch")
    print(f"year   {day(reading.beginning)}  →  {day(reading.high_sun)} high sun  →  {day(reading.earlier_sunset)} evenings turn  →  {day(reading.beginning + reading.year_days)}")
    print(f"days   {reading.year_days}   lengths {', '.join(str(n) for n in reading.lengths)}")


if __name__ == "__main__":
    main(sys.argv[1:])
