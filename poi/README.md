# POI clock

Unix time counts seconds from the Unix epoch: 1970-01-01 00:00:00 UTC. The epoch is that zero. This clock follows the same count. A reading is a unix second plus a place.

The three sky clocks already kept in [poi-world](https://github.com/Azdwarf5Azdwarf/poi-world/blob/main/docs/features/mylla.md) sit on top of it:

- the sky turns 15 degrees an hour
- the sun walks about one degree a day (`360 / 365.2425`)
- the stars drift one degree every 72 years

## The year bars

The year is two bars. Yellow is the time the sun is up. The rest is the sun down. Yellow widens through the climb and narrows after the high sun. The width is the day length at that place, so Stockholm's yellow bar swings harder than the bar at the equator.

```
hook   ·  one degree every 72 years
bars   ████████░░░░░░   yellow, then sun down
       ^         ^ ^
       evenings  high evenings
       start     sun  start earlier
       later
```

Three tangents mark the year. They are sky events at the place, dated by mean solar time at that longitude:

1. **Beginning.** Sunset starts getting later. The year opens here.
2. **High sun.** The noon sun is at its highest.
3. **Earlier evenings.** Sunset starts getting earlier. In Stockholm this falls two days after the high sun.

North of the equator the year opens in December and crests in June. South of the equator it opens in June and crests in December. Where the sun never sets, the evening tangent falls on the high sun itself, and the yellow bar is the whole day or none of it.

## Fourteen months

The months follow the speed of the yellow bar. The bar is nearly still at the opening and under the high sun, so those months are short. It races near the equinoxes, so those months are long.

A 365-day year, which is the common length from one beginning to the next:

| Month | Days | Beginning, middle, end | Stockholm, 2025-12-16 year |
| --- | --- | --- | --- |
| 1 | 17 | 6 + 6 + 5 | 16 Dec – 1 Jan |
| 2 | 25 | 8 + 9 + 8 | 2 Jan – 26 Jan |
| 3 | 32 | 11 + 11 + 10 | 27 Jan – 27 Feb |
| 4 | 33 | 11 + 11 + 11 | 28 Feb – 1 Apr |
| 5 | 32 | 11 + 11 + 10 | 2 Apr – 3 May |
| 6 | 26 | 9 + 9 + 8 | 4 May – 29 May |
| 7 | 17 | 6 + 6 + 5 | 30 May – 15 Jun |
| 8 | 17 | 6 + 6 + 5 | 16 Jun – 2 Jul |
| 9 | 26 | 9 + 9 + 8 | 3 Jul – 28 Jul |
| 10 | 32 | 11 + 11 + 10 | 29 Jul – 29 Aug |
| 11 | 33 | 11 + 11 + 11 | 30 Aug – 1 Oct |
| 12 | 32 | 11 + 11 + 10 | 2 Oct – 2 Nov |
| 13 | 26 | 9 + 9 + 8 | 3 Nov – 28 Nov |
| 14 | 17 | 6 + 6 + 5 | 29 Nov – 15 Dec |

Month 1 is the opening month, 17 days, in the short band of 15 to 17. Month 2 is 25 days. Month 4 is the first 33-day month, and it ends on 1 April, before the high sun on 21 June. The high sun and the evening turn both fall in month 8, the short month under the crest. Month 11 is the second 33-day month, on the way down, when the bar is racing again.

Each month is cut into the same three parts: beginning, middle, end. The parts differ by at most one day. A leftover day goes to the middle first.

Some years have 366 days, when the next beginning lands a day later. That year is the same table with month 2 at 26 days.

The Stockholm dates above are an example. Another place keeps these lengths and moves the dates to its own tangents.

## The hook

Above the bars, the star hook moves one degree every 72 tropical years of 365.2425 days. That is the poi-world precession figure, used exactly. It is a slow drift, counted from the Unix epoch, where the hook sits at 0. On 22 November 2026 it has moved 0.790 degrees.

## A reading

Stockholm, 22 November 2026, noon UTC: month 13, day 20 of 26, the end third. Yellow 0.299, sun down 0.701. The year opened 16 December 2025, the high sun was 21 June 2026, and evenings turned earlier on 23 June 2026.

```
python3 -m poi
python3 -m poi 59.3293 18.0686
python3 -m unittest poi.test_clock
```
