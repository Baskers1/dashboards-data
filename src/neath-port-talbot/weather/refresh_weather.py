#!/usr/bin/env python3
"""Refresh the "Neath Port Talbot · Weather" page from the Mac's scrapekit file.

    python3 refresh_weather.py page.html neath-port-talbot.json out.html

page.html              the live artifact page (Artifact read, path index.html)
neath-port-talbot.json scrapekit/out/neath-port-talbot.json, written by
                       `open_data.py neath-port-talbot`

Replaces only the single-line blocks LOCS, RIVERS, FLOODS, OUTLOOK (if the page has
the line) and AIR; npt_flood_areas.json must sit beside this script. A block whose
source failed is left as it was and the reason is printed. English only; the
borough has no storm-overflow or tide source, so the page has neither section.

Exit 2, writing nothing, if the source file is over 6 hours old or no block
could be refreshed.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scrapekit" / "scrapers"))
from om_rows import ok, place_block, read_line, set_line  # noqa: E402

LON = ZoneInfo("Europe/London")
J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
MAX_AGE_H = 6
NEW_STATIONS = ("4226", "4285")  # added 4 Nov 2026 after the first eight
AREAS_FILE = Path(__file__).resolve().with_name("npt_flood_areas.json")
AIR_SERIES = {"P": ("Port Talbot Margam", {"no2": "421", "o3": "423", "pm10": "2277", "pm25": "2281"})}


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def build_locs(old: dict, results: dict, keys: list[str], today: str, when: str,
               now: datetime) -> dict:
    places = ok(results, "towns") or []
    if len(places) != len(keys):
        raise ValueError(f"Open-Meteo returned {len(places)} places, page has {len(keys)}")
    out = {}
    for key, om in zip(keys, places):
        p = old[key]
        out[key] = {k: v for k, v in p.items() if k not in ("aw", "baked", "now", "hourly")}
        out[key].update(place_block(om, today, when, now=now))
    return out


def build_rivers(old: dict, results: dict, now_ms: int, notes: list[str]) -> dict:
    stations = ok(results, "nrw_stations")
    if stations is None:
        notes.append("RIVERS left unchanged: nrw_stations failed")
        return None
    by_id = {str(x["location"]): x for x in stations}
    olds = {s["id"]: s for s in old["st"]}
    st, updated = [], 0
    for sid in [*olds, *(i for i in NEW_STATIONS if i not in olds)]:
        s, api = dict(olds.get(sid) or {}), by_id.get(sid)
        lvl = next((p for p in (api or {}).get("parameters", []) if p.get("paramNameEN") == "River Level"), None)
        try:
            t = ms(datetime.fromisoformat(lvl["latestTime"].replace("Z", "+00:00")))
            val = float(lvl["latestValue"])
        except (TypeError, ValueError, KeyError, AttributeError):
            lvl = None
        if not lvl:
            notes.append(f"river {sid} ({s.get('r', '?')}): no reading, kept {s.get('t')}")
            if s:
                st.append(s)
            continue
        if not s:  # a station new to the page: name it from NRW's title, no history yet
            river, _, site = api["titleEn"].partition(" at ")
            s = {"id": sid, "n": site, "r": river, "lat": api["latitude"], "lon": api["longitude"],
                 "lo": None, "hi": None, "t": 0, "tr": None, "v": [], "vt": []}
        status = lvl.get("parameterStatusEN") or ""
        s["tr"] = status.removeprefix("Level ") or None
        s["trend"] = s["tr"].lower() if s["tr"] else None
        v, vt = list(s.get("v", [])), list(s.get("vt", []))
        if not vt or t > vt[-1]:
            v.append(val)
            vt.append(t)
        keep = [i for i, x in enumerate(vt) if x >= now_ms - 24 * 3600_000]
        s.update(t=t, v=[v[i] for i in keep], vt=[vt[i] for i in keep])
        st.append(s)
        updated += 1
    if not updated:
        notes.append("RIVERS left unchanged: no station had a usable reading")
        return None
    return {"asofMs": now_ms, "st": st}


def build_floods(results: dict, now_ms: int) -> dict | None:
    """NRW warnings in force in the borough; none kept means all clear for NPT."""
    data = ok(results, "nrw_warnings")
    if data is None:
        return None
    areas = json.loads(AREAS_FILE.read_text(encoding="utf-8"))["areas"]
    items = []
    areas = {k.strip().upper(): v for k, v in areas.items()}
    for f in data["features"]:
        p = f["properties"]
        if "FWACODE" not in p or "SEVERITYVALUE" not in p:
            raise ValueError(f"warning without FWACODE/SEVERITYVALUE: {sorted(p)}")
        sev, code = int(p["SEVERITYVALUE"]), str(p["FWACODE"]).strip().upper()
        if sev not in (1, 2, 3, 4):
            raise ValueError(f"unknown SEVERITYVALUE {p['SEVERITYVALUE']!r}")
        if code not in areas or sev == 4:
            continue
        try:  # naive UK local "dd/mm/yyyy HH:MM"; a bad stamp must not hide a live warning
            raised = ms(datetime.strptime(p["TIMERAISED"], "%d/%m/%Y %H:%M").replace(tzinfo=LON))
        except (TypeError, ValueError, KeyError):
            raised = None
        items.append({"id": code, "lvl": p.get("SEVERITY"), "sev": sev,
                      "area": areas[code], "text": (p.get("RIM_ENGLISH") or "")[:400], "raised": raised})
    return {"asofMs": now_ms, "items": sorted(items, key=lambda i: i["sev"])}


def build_outlook(results: dict) -> dict | None:
    d = ok(results, "nrw_forecast")
    if not d or not d.get("Summary_en") or not d.get("IssueDate"):
        return None
    day, clock, ampm = d["IssueDate"].split()  # US order "M/D/YYYY H:MM:SS AM"; no locale-dependent %p
    issued = datetime.strptime(f"{day} {clock}", "%m/%d/%Y %H:%M:%S").replace(tzinfo=LON)
    issued = issued.replace(hour=issued.hour % 12 + (12 if ampm.upper() == "PM" else 0))
    return {"issued": issued.isoformat(), "summary": d["Summary_en"][:600]}


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


def refresh(html: str, src: dict, now: datetime) -> tuple[str, list[str], list[str]]:
    """Return (new html, refreshed block names, notes)."""
    results, notes, done = src["results"], [], []
    lines = html.split("\n")
    today = now.astimezone(LON).date().isoformat()
    when = datetime.fromisoformat(src["fetched_at"]).astimezone(LON).strftime("%-d %b, %H:%M")
    now_ms = ms(now)

    old_locs = read_line(lines, "LOCS")
    try:
        set_line(lines, "LOCS", build_locs(old_locs, results, list(old_locs), today, when, now))
        done.append("LOCS")
    except ValueError as exc:
        notes.append(f"weather: {exc}; LOCS left unchanged")
    def guarded(name, fn, *args):  # one malformed NRW body must not stop the other blocks
        try:
            return fn(*args)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{name} not refreshed: {type(exc).__name__}: {exc}; block left as it was")

    rivers = guarded("RIVERS", build_rivers, read_line(lines, "RIVERS"), results, now_ms, notes)
    if rivers:
        set_line(lines, "RIVERS", rivers)
        done.append("RIVERS")
    outlook = guarded("OUTLOOK", build_outlook, results)
    if not any(l.startswith("var OUTLOOK=") for l in lines):
        notes.append("OUTLOOK not written: the page has no 'var OUTLOOK=' line yet")
    elif outlook is None:
        notes.append("OUTLOOK left unchanged: nrw_forecast failed or has no summary")
    else:
        set_line(lines, "OUTLOOK", outlook)
        done.append("OUTLOOK")
    for name, value, why in (
            ("FLOODS", guarded("FLOODS", build_floods, results, now_ms), "nrw_warnings failed or unreadable"),
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
    if "LOCS" not in done:
        print("weather not refreshed: page not written")
        return 2
    Path(outp).write_text(html, encoding="utf-8")
    print("refreshed:", ", ".join(done))
    return 0


if __name__ == "__main__":
    sys.exit(main())
