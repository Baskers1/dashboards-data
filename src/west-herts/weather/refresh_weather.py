"""Refresh the weather and air blocks of the West Herts · Weather page from the Mac file.

    python3 refresh_weather.py page.html west-herts.json out.html

Migration Phase 3 (AccuWeather -> Open-Meteo). Replaces only:
- LOCS  weather for the ten towns, from results["towns"] (one Open-Meteo call, LOCS order)
- AIR   Defra UK-AIR hourly series for Borehamwood Meadow Park and London Hillingdon
and rewords the page's AccuWeather credits. Rivers, floods and overflows stay with
the hourly task. Exits 2 (writing nothing) if the source is more than 6 hours old or
LOCS could not be built.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scrapekit" / "scrapers"))
from om_rows import fetched_of, ok, place_block, read_line, set_line, stamp  # noqa: E402

LON = ZoneInfo("Europe/London")
J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
MAX_AGE_H = 6
AIR_SERIES = {"B": {"no2": "4565", "pm10": "4890", "pm25": "4892"},
              "H": {"no2": "241", "o3": "243", "pm10": "4911", "pm25": "4914"}}
REWORD = [
    (" Feels like is AccuWeather RealFeel.", " Feels like is the Open-Meteo apparent temperature."),
    ("AccuWeather conditions for ", "Open-Meteo conditions for "),
    ("AccuWeather hourly forecast, fetched ", "Open-Meteo model forecast, fetched "),
    ("may differ slightly from AccuWeather\\'s figures", "may differ slightly from the forecast hours"),
    ('$("hnote").textContent=""}', '$("hnote").textContent="Forecast data: Open-Meteo.com (CC BY 4.0)."}'),
]


def build_locs(old: dict, results: dict, today: str, when: str, now: datetime) -> dict:
    places = ok(results, "towns")
    if not isinstance(places, list) or len(places) != len(old):
        raise ValueError(f"Open-Meteo 'towns' did not return {len(old)} places")
    out = {}
    for key, om in zip(old, places):  # LOCS order is the request order
        out[key] = {k: v for k, v in old[key].items() if k not in ("baked", "now", "hourly")}
        out[key].update(place_block(om, today, when, now=now))
    return out


def build_air(old: dict, results: dict) -> dict | None:
    """28 hourly values per pollutant, ending at the newest Defra hour; None if any series failed."""
    got = {}
    for k, series in AIR_SERIES.items():
        for pol, sid in series.items():
            vals = (ok(results, f"air_{sid}") or {}).get("values")
            if vals is None:
                return None
            got[(k, pol)] = {v["timestamp"]: (v["value"] if v["value"] is not None and v["value"] >= 0 else None)
                             for v in vals}
    stamps = [t for s in got.values() for t, v in s.items() if v is not None]
    if not stamps:
        return None
    newest = max(stamps)
    grid = [newest - 3600_000 * (27 - j) for j in range(28)]
    st = []
    for s in old["st"]:  # keep each station's name, distances and direction
        s = dict(s)
        for pol in AIR_SERIES.get(s["k"], {}):
            s[pol] = [got[(s["k"], pol)].get(g) for g in grid]
        st.append(s)
    return {**old, "last": newest, "when": stamp(datetime.fromtimestamp(newest / 1000, timezone.utc)), "st": st}


def refresh(html: str, src: dict, now: datetime) -> tuple[str, list[str], list[str]]:
    results, notes, done = src["results"], [], []
    for old, new in REWORD:
        html = html.replace(old, new)
    lines = html.split("\n")
    today = now.astimezone(LON).date().isoformat()
    when = stamp(fetched_of(src))
    try:
        set_line(lines, "LOCS", build_locs(read_line(lines, "LOCS"), results, today, when, now))
        done.append("LOCS")
    except ValueError as exc:
        notes.append(f"weather: {exc}; LOCS left unchanged")
    air = build_air(read_line(lines, "AIR"), results)
    if air is None:
        notes.append("AIR left unchanged: a Defra series failed or every reading was missing")
    else:
        set_line(lines, "AIR", air)
        done.append("AIR")
    return "\n".join(lines), done, notes


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
    if "LOCS" not in done:
        print("weather not refreshed: page not written")
        return 2
    if "AccuWeather" in html:
        print("note: 'AccuWeather' still appears on the page")
    Path(outp).write_text(html, encoding="utf-8")
    print("refreshed:", ", ".join(done))
    return 0


if __name__ == "__main__":
    sys.exit(main())
