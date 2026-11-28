"""Refresh the weather and air blocks of the Tayside · Weather page from the Mac file.

    python3 refresh_weather.py page.html tayside.json out.html

Migration Phase 3 (AccuWeather -> Open-Meteo). Replaces only:
- LOCS  weather for Dundee and Carnoustie, from results["towns"] (Open-Meteo, two places)
- AIR   Scottish Air Quality site pages, with Dundee Mains Loan NO2 taken from
        Defra UK-AIR (series 4554) whenever Defra is newer than the Scottish page
and rewords the page's AccuWeather credits. Rivers, floods, tides, bathing and
overflows stay with the hourly task. Exits 2 (writing nothing) if the source is
more than 6 hours old or LOCS could not be built.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scrapekit" / "scrapers"))
from om_rows import fetched_of, ok, place_block, read_line, set_line, stamp  # noqa: E402

LON = ZoneInfo("Europe/London")
J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
MAX_AGE_H = 6
SITE_MAX_H = 3  # a Scottish site page older than this is not shown (the cache-fallback served 9-day-old pages)
AIR_SITES = ["DUN1", "DUN5", "DUNM", "DUN4", "AFR1"]
DEFRA_NO2 = ("DUN1", "air_4554")
NAMES = {"PM 2.5": "Fine particles (PM2.5)", "PM 10": "Particles (PM10)", "NO 2": "Nitrogen dioxide (NO₂)"}
ROW = re.compile(r"(PM 2\.5|PM 10|NO 2) (\d+|No Data) (?:[A-Z]+(?: HIGH)? )?([\d.]+) µg/m 3 (?:\([^)]*\) )?"
                 r"(24 Hour mean|hourly mean)")
UPD = re.compile(r"Updated (\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d)")
NO2_BANDS = [67, 134, 200, 267, 334, 400, 467, 534, 600]  # DAQI hourly NO2 upper bounds, bands 1-9

REWORD = [
    ("Source: AccuWeather. The hour-by-hour chart covers the full day: AccuWeather hourly values "
     "where available, Open-Meteo model values for the other hours.",
     "Source: Open-Meteo.com (CC BY 4.0). The hour-by-hour chart covers the full day."),
    (" Feels like is AccuWeather RealFeel.", " Feels like is Open-Meteo apparent temperature."),
    ('"AccuWeather hourly forecast, fetched "', '"Open-Meteo hourly forecast, fetched "'),
    ('"Hours with no AccuWeather hourly forecast (earlier and later in the day) are filled with '
     'Open-Meteo model values so the chart covers the full day; AccuWeather values replace them as '
     'they arrive."', '"Forecast data: Open-Meteo.com (CC BY 4.0)."'),
    ('"AccuWeather conditions for "', '"Open-Meteo model conditions for "'),
    ("Scottish Air Quality website (<a href=\"https://www.scottishairquality.scot/latest/summary\" "
     "target=\"_blank\" rel=\"noopener\">scottishairquality.scot</a>; data are provisional).",
     "Scottish Air Quality website (<a href=\"https://www.scottishairquality.scot/latest/summary\" "
     "target=\"_blank\" rel=\"noopener\">scottishairquality.scot</a>; data are provisional). When "
     "Defra UK-AIR (<a href=\"https://uk-air.defra.gov.uk\" target=\"_blank\" rel=\"noopener\">"
     "uk-air.defra.gov.uk</a>) has a newer hourly reading for Dundee Mains Loan, that station shows "
     "nitrogen dioxide from Defra only."),
    ("that station shows nitrogen dioxide from Defra only.",
     "that station shows nitrogen dioxide from Defra only. A station shows n/a and dashes when its newest "
     "reading is more than 3 hours old, for example while the Scottish Air Quality website is offline."),
    (">Latest readings on the Scottish Air Quality network: '",
     ">Latest readings (Scottish Air Quality network and Defra UK-AIR): '"),
]
# The page holds these inside single-quoted JS strings: no apostrophes allowed.
assert all(new.count("'") == old.count("'") for old, new in REWORD)


def num(s: str):
    f = float(s)
    return int(f) if f.is_integer() else f


def no2_band(v: float) -> int:
    return next((i + 1 for i, b in enumerate(NO2_BANDS) if v <= b + 0.5), 10)


def build_locs(old: dict, results: dict, today: str, when: str, now: datetime) -> dict:
    places = ok(results, "towns")
    if not isinstance(places, list) or len(places) != len(old):
        raise ValueError(f"Open-Meteo 'towns' did not return {len(old)} places")
    out = {}
    for key, om in zip(old, places):  # LOCS order is Dundee, Carnoustie, as the request
        out[key] = {k: v for k, v in old[key].items() if k not in ("baked", "now", "hourly")}
        out[key].update(place_block(om, today, when, now=now))
    return out


def parse_site(text: str):
    """(update time UTC, p rows) from a scottishairquality.scot site page, or None."""
    m = UPD.search(text or "")
    if not m:
        return None
    d, mo, y, h, mi = map(int, m.groups())
    upd = datetime(y, mo, d, h, mi, tzinfo=timezone.utc)  # the site states GMT
    rows = {name: [NAMES[name], 0 if idx == "No Data" else int(idx), num(conc),
                   "24-hour mean" if per.startswith("24") else "hourly mean"]
            for name, idx, conc, per in ROW.findall(text)}
    p = [rows[k] for k in NAMES if k in rows]
    return (upd, p) if p else None


def build_air(old: dict, results: dict, notes: list[str], now: datetime) -> dict:
    st, latest = [], []
    for s in old["st"]:
        s = dict(s)
        got = parse_site((ok(results, f"air_{s['id'].lower()}") or {}).get("text"))
        if got is not None and now - got[0] > timedelta(hours=SITE_MAX_H):
            s["p"], s["upd"] = [], stamp(got[0])
            notes.append(f"AIR {s['id']}: newest site reading is {stamp(got[0])}, over {SITE_MAX_H} h old; values hidden")
            got = None
        elif got is None:
            s["p"] = []
            notes.append(f"AIR {s['id']}: site page failed or unreadable; values hidden")
        else:
            upd, s["p"] = got
            s["upd"] = stamp(upd)
            latest.append(upd)
        if s["id"] == DEFRA_NO2[0]:
            vals = [v for v in (ok(results, DEFRA_NO2[1]) or {}).get("values", [])
                    if v.get("value") is not None and v["value"] >= 0]
            if vals:
                v = max(vals, key=lambda x: x["timestamp"])
                t = datetime.fromtimestamp(v["timestamp"] / 1000, timezone.utc)
                if now - t > timedelta(hours=SITE_MAX_H):
                    notes.append(f"AIR {s['id']}: newest Defra NO2 is {stamp(t)}, over {SITE_MAX_H} h old; not shown")
                elif got is None or t > got[0]:
                    s["p"] = [[NAMES["NO 2"], no2_band(v["value"]), num(f"{v['value']:.0f}"), "hourly mean"]]
                    s["upd"] = stamp(t)
                    latest.append(t)
                    notes.append(f"AIR {s['id']}: NO2 from Defra UK-AIR at {stamp(t)}")
            else:
                notes.append("AIR: Defra series 4554 failed or empty")
        st.append(s)
    when = stamp(max(latest)) if latest else old["when"]
    return {**old, "when": when, "st": st}


def reword(html: str) -> str:
    """Apply REWORD once. A new text that extends its old text was re-appended on every run
    until 30 Oct 2026, so collapse any repeats of the extension first."""
    for old, new in REWORD:
        extra = new[len(old):] if new.startswith(old) else ""
        while extra and extra + extra in html:
            html = html.replace(extra + extra, extra)
        if new not in html:
            html = html.replace(old, new)
    return html


def refresh(html: str, src: dict, now: datetime) -> tuple[str, list[str], list[str]]:
    results, notes, done = src["results"], [], []
    html = reword(html)
    lines = html.split("\n")
    today = now.astimezone(LON).date().isoformat()
    when = stamp(fetched_of(src))
    try:
        set_line(lines, "LOCS", build_locs(read_line(lines, "LOCS"), results, today, when, now))
        done.append("LOCS")
    except ValueError as exc:
        notes.append(f"weather: {exc}; LOCS left unchanged")
    set_line(lines, "AIR", build_air(read_line(lines, "AIR"), results, notes, now))
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
