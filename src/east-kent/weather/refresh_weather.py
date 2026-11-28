"""Refresh Ramsgate's weather and the air block of the East Kent · Weather page from the Mac file.

    python3 refresh_weather.py page.html east-kent.json out.html

Migration Phase 3 (AccuWeather -> Open-Meteo). Replaces only:
- BAKED, BAKED_NOW, HOURLY  Ramsgate's forecast, from results["ramsgate"] (Open-Meteo).
  HOURLY gets src "om", so the page labels every hour as Open-Meteo.
- AIR  Defra UK-AIR hourly series for Rochester Stoke and St Osyth
and rewords the page's AccuWeather credits. The other towns (OM block), floods, gauges
and overflows stay with the hourly task. Exits 2 (writing nothing) if the source is more
than 6 hours old or Ramsgate's weather could not be built.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scrapekit" / "scrapers"))
from om_rows import fetched_of, ok, place_block, stamp  # noqa: E402

LON = ZoneInfo("Europe/London")
J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
MAX_AGE_H = 6
AIR_SERIES = {"R": {"no2": "432", "o3": "434", "pm10": "2288", "pm25": "2292"},
              "S": {"no2": "388", "o3": "390", "pm10": "4909", "pm25": "4910"}}
REWORD = [
    ('"Forecast snapshot from AccuWeather, "', '"Forecast snapshot from Open-Meteo, "'),
    ("Open-Meteo is a computer weather model, not AccuWeather like the Ramsgate figures, "
     "so the two can differ a little. ", "Open-Meteo is a computer weather model. "),
    ('" Feels like is AccuWeather RealFeel."', '" Feels like is the Open-Meteo apparent temperature."'),
    ("the rest AccuWeather. ", "the rest Open-Meteo forecast. "),
    ('"AccuWeather hourly forecast, fetched "', '"Open-Meteo model forecast, fetched "'),
]
BAKED_RE = re.compile(r"^var BAKED=\[.*?\];$", re.M | re.S)  # spans several lines on the old page


def build_air(old: dict, results: dict) -> dict | None:
    """Each pollutant array keeps its length, ending at the newest Defra hour; None if any series failed."""
    got = {}
    for k, series in AIR_SERIES.items():
        for pol, sid in series.items():
            vals = (ok(results, f"air_{sid}") or {}).get("values")
            if vals is None:
                return None
            got[(k, pol)] = {v["timestamp"]: (v["value"] if v["value"] is not None and v["value"] >= 0 else None)
                             for v in vals}  # Defra marks a missing hour as -99
    stamps = [t for s in got.values() for t, v in s.items() if v is not None]
    if not stamps:
        return None
    newest = max(stamps)
    st = []
    for s in old["st"]:  # keep each station's name, distance and direction
        s = dict(s)
        for pol in AIR_SERIES.get(s["k"], {}):
            n = len(s.get(pol) or []) or 30
            s[pol] = [got[(s["k"], pol)].get(newest - 3600_000 * (n - 1 - j)) for j in range(n)]
        st.append(s)
    return {**old, "last": newest, "when": stamp(datetime.fromtimestamp(newest / 1000, timezone.utc)), "st": st}


def set_line(html: str, name: str, value) -> str:
    pat = BAKED_RE if name == "BAKED" else re.compile(rf"^var {name}=.*;$", re.M)
    found = pat.findall(html)
    if len(found) != 1:
        raise ValueError(f"{name}: expected one 'var {name}=' block, found {len(found)}")
    return pat.sub(lambda _: f"var {name}={J(value)};", html)


def read_line(html: str, name: str):
    return json.loads(re.search(rf"^var {name}=(.*);$", html, re.M).group(1))


def refresh(html: str, src: dict, now: datetime) -> tuple[str, list[str], list[str]]:
    results, notes, done = src["results"], [], []
    for old, new in REWORD:
        html = html.replace(old, new)
    today = now.astimezone(LON).date().isoformat()
    when = stamp(fetched_of(src))
    try:
        om = ok(results, "ramsgate")
        if not isinstance(om, dict):
            raise ValueError("Open-Meteo 'ramsgate' source failed")
        b = place_block(om, today, when, now=now)
        html = set_line(html, "BAKED", b["baked"])
        html = set_line(html, "BAKED_NOW", b["now"])
        html = set_line(html, "HOURLY", {"date": today, "src": "om", "when": when, "rows": b["hourly"]["rows"]})
        done.append("RAMSGATE")
    except ValueError as exc:
        notes.append(f"weather: {exc}; Ramsgate weather left unchanged")
    air = build_air(read_line(html, "AIR"), results)
    if air is None:
        notes.append("AIR left unchanged: a Defra series failed or every reading was missing")
    else:
        html = set_line(html, "AIR", air)
        done.append("AIR")
    return html, done, notes


def main() -> int:
    page, srcp, outp = sys.argv[1:4]
    src = json.loads(Path(srcp).read_text(encoding="utf-8"))
    age = datetime.now(timezone.utc) - datetime.fromisoformat(src["fetched_at"])
    print(f"source fetched_at {src['fetched_at']} ({age.total_seconds() / 3600:.1f} h old); "
          f"failed: {src.get('sources_failed')}")
    if age > timedelta(hours=MAX_AGE_H):
        print(f"source is more than {MAX_AGE_H} hours old: nothing refreshed")
        return 2
    html, done, notes = refresh(Path(page).read_text(encoding="utf-8"), src, datetime.now(timezone.utc))
    for n in notes:
        print("note:", n)
    if "RAMSGATE" not in done:
        print("weather not refreshed: page not written")
        return 2
    if "AccuWeather" in html:
        print("note: 'AccuWeather' still appears on the page")
    Path(outp).write_text(html, encoding="utf-8")
    print("refreshed:", ", ".join(done))
    return 0


if __name__ == "__main__":
    sys.exit(main())
