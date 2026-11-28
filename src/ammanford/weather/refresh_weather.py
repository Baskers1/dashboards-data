#!/usr/bin/env python3
"""Refresh the "Ammanford · Weather" page from the Mac's scrapekit file.

    python3 refresh_weather.py page.html ammanford.json out.html

page.html      the live artifact page (Artifact read, path index.html)
ammanford.json scrapekit/out/ammanford.json, written by
               `open_data.py ammanford` (launchd uk.baskers.scrapekit.open-data-ammanford)

Replaces only the single-line blocks LOCS, RIVERS, FLOODS, SPILLS and AIR, plus
the Welsh dictionary line (var W=). A block whose source failed is left as it
was and the reason is printed. Every run also swaps the old AccuWeather credits
for Open-Meteo ones, so republishing an old copy cannot bring them back.

If the weather (LOCS) cannot be refreshed the other blocks are still written and
a "note:" line says the weather was left unchanged. Exit 2, writing nothing, if
the source file is over 6 hours old or no block at all could be refreshed.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scrapekit" / "scrapers"))
from om_rows import PHRASE_CY, fetched_of, ok, place_block, read_line, set_line  # noqa: E402

LON = ZoneInfo("Europe/London")
J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
MAX_AGE_H = 6
AIR_SERIES = {"S": ("Swansea Roadside", {"no2": "485", "pm10": "2340", "pm25": "487"}),
              "P": ("Port Talbot Margam", {"no2": "421", "o3": "423", "pm10": "2277", "pm25": "2281"})}

# (old, new) English wording, and the Welsh dictionary entries that go with it.
REWORD = [
    (" Feels like is AccuWeather RealFeel.", " Feels like is the Open-Meteo apparent temperature."),
    ("AccuWeather conditions for ", "Open-Meteo conditions for "),
    ("AccuWeather hourly forecast, fetched ", "Open-Meteo model forecast, fetched "),
    ("Earlier hours of today are filled from Open-Meteo modelled data (shown as modelled, not "
     "forecasts or station readings). Many villages here share an AccuWeather forecast grid, so "
     "neighbouring places can show identical figures.",
     "Forecasts are Open-Meteo model data (CC BY 4.0, modified). The model works on a grid, so "
     "neighbouring villages can show identical figures."),
    ("may differ slightly from AccuWeather\\'s figures", "may differ slightly from the forecast hours"),
]
W_OLD = [
    "AccuWeather conditions for {P} at {D}.",
    "AccuWeather hourly forecast, fetched {D}. Feels like is AccuWeather RealFeel. Gusts: bold "
    "amber or red means # km/h or more.",
    "Hours #:# to #:# are filled in from Open-Meteo's modelled hourly analysis for this location, "
    "not from forecasts or station readings, so they have no rain-chance bars and may differ "
    "slightly from AccuWeather's figures.",
    "Walk rating: Good = low rain and light gusts; Fair = showers possible or gusty; Poor = wet "
    "or windy (#%+ rain or gusts # km/h+). Earlier hours of today are filled from Open-Meteo "
    "modelled data (shown as modelled, not forecasts or station readings). Many villages here "
    "share an AccuWeather forecast grid, so neighbouring places can show identical figures.",
]
W_NEW = {
    "Open-Meteo conditions for {P} at {D}.": "Amodau Open-Meteo ar gyfer {P} am {D}.",
    "Open-Meteo model forecast, fetched {D}. Feels like is the Open-Meteo apparent temperature. "
    "Gusts: bold amber or red means # km/h or more.":
        "Rhagolwg model Open-Meteo, a gafwyd {D}. “Teimlo fel” yw tymheredd ymddangosiadol "
        "Open-Meteo. Hyrddiau: mae oren neu goch trwm yn golygu # km/a neu fwy.",
    "Walk rating: Good = low rain and light gusts; Fair = showers possible or gusty; Poor = wet "
    "or windy (#%+ rain or gusts # km/h+). Forecasts are Open-Meteo model data (CC BY #, "
    "modified). The model works on a grid, so neighbouring villages can show identical figures.":
        "Sgôr cerdded: Da = ychydig o law a hyrddiau ysgafn; Gweddol = cawodydd yn bosibl neu’n "
        "wyntog; Gwael = gwlyb neu wyntog (#%+ glaw neu hyrddiau # km/a+). Data model Open-Meteo "
        "yw’r rhagolygon (CC BY #, wedi’u haddasu). Mae’r model yn gweithio ar grid, felly gall "
        "pentrefi cyfagos ddangos ffigurau union yr un fath.",
    "Show the other # hours": "Dangos y # awr arall",
    **PHRASE_CY,
}


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def build_locs(old: dict, results: dict, keys: list[str], today: str, when: str,
               now: datetime) -> dict:
    places = (ok(results, "towns_0") or []) + (ok(results, "towns_1") or [])
    if len(places) != len(keys):
        raise ValueError(f"Open-Meteo returned {len(places)} places, page has {len(keys)}")
    out = {}
    for key, om in zip(keys, places):
        p = old[key]
        out[key] = {k: v for k, v in p.items() if k not in ("aw", "baked", "now", "hourly")}
        out[key].update(place_block(om, today, when, now=now))
    return out


def build_rivers(old: dict, results: dict, now_ms: int, notes: list[str]) -> dict:
    by_id = {str(x.get("location")): x for x in ok(results, "nrw_stations") or []}
    st = []
    for s in old["st"]:
        s = dict(s)
        lvl = next((p for p in by_id.get(s["id"], {}).get("parameters", [])
                    if p.get("paramNameEN") == "River Level"), None)
        try:
            t = ms(datetime.fromisoformat(lvl["latestTime"].replace("Z", "+00:00")))
            val = float(lvl["latestValue"])
        except (TypeError, ValueError, KeyError):
            notes.append(f"river {s['id']} ({s['r']}): no reading, kept {s.get('t')}")
            st.append(s)
            continue
        s["tr"] = (lvl.get("parameterStatusEN") or "").removeprefix("Level ") or None
        v, vt = list(s.get("v", [])), list(s.get("vt", []))
        if not vt or t > vt[-1]:
            v.append(val)
            vt.append(t)
        keep = [i for i, x in enumerate(vt) if x >= now_ms - 24 * 3600_000]
        s.update(t=t, v=[v[i] for i in keep], vt=[vt[i] for i in keep])
        st.append(s)
    return {"asofMs": now_ms, "st": st}


def build_floods(results: dict, now_ms: int) -> dict | None:
    """Only a Wales-wide all-clear can be stated from the counts.

    shortcut: when any warning or alert is in force in Wales the block is left as
    it was (and reported), because the list markup has not yet been seen with an
    item in it to filter by area. Upgrade the first time a warning is live.
    """
    text = (ok(results, "flood_warnings") or {}).get("text", "")
    counts = re.findall(r"(\d+) Severe\s*\S*Flood\s*\S*Warnings.*?(\d+) Flood\s*\S*Warnings.*?(\d+) Flood\s*\S*Alerts",
                        text)
    if not counts:
        return None
    if all(int(n) == 0 for n in counts[0]):
        return {"asofMs": now_ms, "items": []}
    return None


def build_spills(results: dict) -> dict | None:
    data = ok(results, "storm_overflows")
    feats = (data or {}).get("features")
    if not isinstance(feats, list) or len(feats) < 50:
        return None

    def lt(s):
        return ms(datetime.fromisoformat(s[:19]).replace(tzinfo=LON)) if s else None

    f = []
    for x in feats:
        a, g, s = x["attributes"], x["geometry"], x["attributes"]["status"] or ""
        code = 1 if s == "Overflow Operating" else 2 if "last 24" in s else -1 if "Investigation" in s else 0
        start, end = lt(a["start_date_time_discharge"]), lt(a["stop_date_time_discharge"])
        if code == 1:
            end = None
        if code == -1:
            start = end = None
        name = re.sub(r"\s+Storm Overflow$", "", (a["asset_name"] or "").strip())
        f.append([a["DCWW_ID"], code, start, end, round(g["y"], 5), round(g["x"], 5),
                  a["Receiving_Water"] or "", name])
    return {"asofMs": max(x["attributes"]["EditDate"] for x in feats), "f": f}


def build_air(results: dict) -> dict | None:
    got = {}
    for k, (_, series) in AIR_SERIES.items():
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
    for k, (name, series) in AIR_SERIES.items():
        o = {"n": name, "k": k}
        for pol in series:
            o[pol] = [got[(k, pol)].get(g) for g in grid]
        st.append(o)
    return {"last": newest, "when": datetime.fromtimestamp(newest / 1000, LON).strftime("%-d %b, %H:%M"),
            "st": st}


def reword(html: str) -> str:
    # Dictionary first: rewording first would turn old W keys into new English.
    i = html.index("\nvar W={") + len("\nvar W=")
    w, end = json.JSONDecoder().raw_decode(html, i)
    for k in W_OLD:
        w.pop(k, None)
    w.update(W_NEW)
    html = html[:i] + json.dumps(w, ensure_ascii=False) + html[end:]
    for old, new in REWORD:
        html = html.replace(old, new)
    return html


def refresh(html: str, src: dict, now: datetime) -> tuple[str, list[str], list[str]]:
    """Return (new html, refreshed block names, notes)."""
    results, notes, done = src["results"], [], []
    lines = reword(html).split("\n")
    today = now.astimezone(LON).date().isoformat()
    when = fetched_of(src).astimezone(LON).strftime("%-d %b, %H:%M")
    now_ms = ms(now)

    old_locs = read_line(lines, "LOCS")
    try:
        set_line(lines, "LOCS", build_locs(old_locs, results, list(old_locs), today, when, now))
        done.append("LOCS")
    except ValueError as exc:
        notes.append(f"weather: {exc}; LOCS left unchanged (weather NOT refreshed, page keeps its earlier forecast)")
    old_rivers = read_line(lines, "RIVERS")
    set_line(lines, "RIVERS", build_rivers(old_rivers, results, now_ms, notes))
    if ok(results, "nrw_stations"):
        done.append("RIVERS")
    for name, value, why in (
            ("FLOODS", build_floods(results, now_ms),
             "NRW page unreadable, or a warning/alert is in force somewhere in Wales; check NRW"),
            ("SPILLS", build_spills(results), "Welsh Water feed failed or too few rows"),
            ("AIR", build_air(results), "a Defra series failed or every reading was missing")):
        if value is None:
            notes.append(f"{name} left unchanged: {why}")
        else:
            set_line(lines, name, value)
            done.append(name)
    return "\n".join(lines), done, notes


def main() -> int:
    page, srcp, outp = sys.argv[1:4]
    src = json.loads(Path(srcp).read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    age = now - datetime.fromisoformat(src["fetched_at"])
    print(f"source fetched_at {src['fetched_at']} ({age.total_seconds() / 3600:.1f} h old); "
          f"failed: {src.get('sources_failed')}")
    if age > timedelta(hours=MAX_AGE_H):
        print(f"source is more than {MAX_AGE_H} hours old: nothing refreshed")
        return 2
    html, done, notes = refresh(Path(page).read_text(encoding="utf-8"), src, now)
    for n in notes:
        print("note:", n)
    if not done:
        print("no block refreshed: page not written")
        return 2
    Path(outp).write_text(html, encoding="utf-8")
    print("refreshed:", ", ".join(done))
    return 0


if __name__ == "__main__":
    sys.exit(main())
