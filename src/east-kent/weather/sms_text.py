"""The Ramsgate text message, from the East Kent page's data (weather template).

    python3 sms_text.py data.json --spills refreshed|unchanged [--now 2026-11-23T09:05:00+00:00]

Prints the message: four lines, plain ASCII, at most 155 characters. The rules are the ones the
hourly task prompt gave by hand until 22 Nov 2026 (STEP 7), now in code:

  1  "Hullo! Ramsgate: <now>C (high <today's high>C), <phrase, at most 3 words, lower case>,
     <compass> wind <speed> km/h, rain <today's rain chance>%."
  2  "Next high tide HH:MM (X.Xm)." -- the first high water later than now today, else tomorrow's first
  3  "Sewage overflow: none." / "Sewage overflow: N discharging, see link." -- overflows with Status 1
     in the original Ramsgate box (lat 51.30-51.42, lon 1.30-1.50), only if SPILLS was refreshed this
     run; otherwise "Sewage overflow: data unavailable."
  4  the short link

If the whole is over 155 characters, line 1 is shortened first (phrase dropped, then the wind).
Exits 1, printing why, if a figure it needs is missing: never sends a guessed number.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LON = ZoneInfo("Europe/London")
LINK = "https://tinyurl.com/araxtuh4"
LIMIT = 155


def ascii_only(s: str) -> str:
    return s.encode("ascii", "ignore").decode("ascii")


def next_high(tides: dict, now: datetime) -> str:
    n = now.astimezone(LON)
    today, hm = n.date().isoformat(), n.strftime("%H:%M")
    tomorrow = (n.date() + timedelta(days=1)).isoformat()
    for day, later in ((today, True), (tomorrow, False)):
        for r in tides.get(day, []):
            if r[0] == "H" and (not later or r[1] > hm) and r[2] is not None:
                return f"Next high tide {r[1]} ({r[2]:.1f}m)."
    raise ValueError(f"no high water for {today} or {tomorrow} in TIDES")


def sewage_line(spills: dict, refreshed: bool) -> str:
    if not refreshed:
        return "Sewage overflow: data unavailable."
    n = sum(1 for r in spills["f"] if r[1] == 1 and 51.30 <= r[4] <= 51.42 and 1.30 <= r[5] <= 1.50)
    return "Sewage overflow: none." if n == 0 else f"Sewage overflow: {n} discharging, see link."


def first_line(ram: dict, today: str, parts: int = 3) -> str:
    now, day = ram["now"], next(d for d in ram["baked"] if d[0] == today)
    phrase = " ".join(now["phrase"].lower().split()[:3])
    compass, speed = now["wind"].split(" ", 1)
    bits = [f"Hullo! Ramsgate: {now['t']}C (high {day[1]}C)"]
    if parts >= 3:
        bits.append(phrase)
    if parts >= 2:
        bits.append(f"{compass} wind {speed}")
    return ascii_only(", ".join(bits) + f", rain {day[4]}%.")


def message(data: dict, spills_refreshed: bool, now: datetime) -> str:
    locs = json.loads(data["LOCS"]) if isinstance(data["LOCS"], str) else data["LOCS"]
    tides = json.loads(data["TIDES"]) if isinstance(data["TIDES"], str) else data["TIDES"]
    spills = json.loads(data["SPILLS"]) if isinstance(data["SPILLS"], str) else data["SPILLS"]
    ram, today = locs["ramsgate"], now.astimezone(LON).date().isoformat()
    rest = [ascii_only(next_high(tides, now)), sewage_line(spills, spills_refreshed), LINK]
    for parts in (3, 2, 1):
        text = "\n".join([first_line(ram, today, parts)] + rest)
        if len(text) <= LIMIT:
            return text
    raise ValueError(f"message is {len(text)} characters even with line 1 shortened")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--spills", choices=("refreshed", "unchanged"), required=True)
    ap.add_argument("--now")
    a = ap.parse_args(argv)
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc)
    try:
        print(message(json.load(open(a.data, encoding="utf-8")), a.spills == "refreshed", now))
    except (KeyError, StopIteration, ValueError) as exc:
        print(f"no text message: {exc!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
