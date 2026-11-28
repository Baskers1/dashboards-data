"""Refresh every data block of the East Kent · Weather page (weather template) from one hour's Mac file.

Used by weather-template/refresh_data.py (mode "page_script"): refresh(page, src, now) returns
(page, done, notes). Blocks, and what used to build them:

- LOCS      all six towns from Open-Meteo through om_rows.place_block: Ramsgate from "ramsgate",
            the other five from "other_towns" (one multi-place answer, in TOWN_ORDER). Was:
            refresh_weather.py for Ramsgate (BAKED, BAKED_NOW, HOURLY) plus task step 4f by hand (OM).
- AIR       refresh_weather.build_air (Defra UK-AIR), unchanged.
- SPILLS    Southern Water storm overflows (task step 4d, by hand until 22 Nov 2026).
- FLOODS    Environment Agency warnings and three gauges (task step 4g, by hand). The page calls it FLOOD.
- RELEASES  Southern Water Rivers and Seas Watch: beach status ("bathing_releases") and the last
            30 days of release events ("bathing_release_history"). Was: copied by hand, last 2 Oct 2026.
- TIDES, TIDEX  yesterday to +13 days cut from the full tables in
            weather-template/areas/east-kent/tides/ (TideTimes, already adjusted for BST).

Each block is built from its own sources and checked first. A block that fails is left exactly as
it was, with a note saying why; LOCS needs Ramsgate, or nothing is written.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scrapekit" / "scrapers"))
import importlib.util  # noqa: E402
# load this folder's refresh_weather.py by path: every area has one, and a plain import would
# reuse whichever area's module was imported first in the same process
_spec = importlib.util.spec_from_file_location("east_kent_refresh_weather", HERE / "refresh_weather.py")
rw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rw)
from om_rows import fetched_of, ok, place_block, stamp  # noqa: E402

LON = ZoneInfo("Europe/London")
TIDE_DIR = HERE.parents[1] / "weather-template" / "areas" / "east-kent" / "tides"
TOWN_ORDER = ["margate", "broadstairs", "deal", "sandwich", "canterbury"]  # as in open_data.py "other_towns"
GAUGES = ("1003SO", "E3826", "E3810")
RELEASE_DAYS = 30
J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731


def read_block(html: str, name: str):
    hits = re.findall(rf"(?m)^var {name}=(.*);$", html)
    if len(hits) != 1:
        raise ValueError(f"expected one 'var {name}=' line, found {len(hits)}")
    return json.loads(hits[0])


def set_block(html: str, name: str, value) -> str:
    pat = re.compile(rf"(?m)^var {name}=.*;$")
    if len(pat.findall(html)) != 1:
        raise ValueError(f"expected one 'var {name}=' line")
    return pat.sub(lambda _: f"var {name}={J(value)};", html)


# ---------- LOCS ----------

def build_locs(old: dict, results: dict, today: str, when: str, now: datetime, notes: list[str]) -> dict | None:
    out = json.loads(json.dumps(old))
    ram = ok(results, "ramsgate")
    try:
        if not isinstance(ram, dict):
            raise ValueError("Open-Meteo 'ramsgate' source failed")
        out["ramsgate"].update(place_block(ram, today, when, now=now))
    except ValueError as exc:
        notes.append(f"weather: Ramsgate: {exc}; weather NOT refreshed")
        return None
    others = ok(results, "other_towns")
    if not isinstance(others, list) or len(others) != len(TOWN_ORDER):
        notes.append("weather: other towns' Open-Meteo answer missing or not 5 places; Margate, Broadstairs, "
                     "Deal, Sandwich and Canterbury left unchanged")
        return out
    for key, om in zip(TOWN_ORDER, others):
        loc = out[key]
        if abs(om.get("latitude", 0) - loc["lat"]) > 0.05 or abs(om.get("longitude", 0) - loc["lon"]) > 0.05:
            notes.append(f"weather: {loc['name']}: answer is for {om.get('latitude')}, {om.get('longitude')}, "
                         f"not {loc['lat']}, {loc['lon']}; left unchanged")
            continue
        try:
            loc.update(place_block(om, today, when, now=now))
        except ValueError as exc:
            notes.append(f"weather: {loc['name']}: {exc}; left unchanged")
    return out


# ---------- SPILLS (task step 4d) ----------

def build_spills(results: dict, now_ms: int, notes: list[str]) -> dict | None:
    data = ok(results, "storm_overflows")
    feats = data.get("features") if isinstance(data, dict) else None
    if not isinstance(feats, list) or len(feats) < 25:
        notes.append(f"overflows: Southern Water feed failed or has {len(feats) if isinstance(feats, list) else 0} "
                     "monitors (need 25); SPILLS left unchanged")
        return None
    rows = []
    for f in feats:
        a = f.get("attributes") or {}
        r = [a.get("Id"), a.get("Status"), a.get("LatestEventStart"), a.get("LatestEventEnd"),
             a.get("Latitude"), a.get("Longitude"), a.get("ReceivingWaterCourse")]
        if (r[1] not in (-1, 0, 1) or not all(x is None or isinstance(x, int) for x in r[2:4])
                or not isinstance(r[4], (int, float)) or not 51.16 <= r[4] <= 51.42
                or not isinstance(r[5], (int, float)) or not 0.98 <= r[5] <= 1.50):
            notes.append(f"overflows: monitor {r[0]} failed validation; SPILLS left unchanged")
            return None
        rows.append(r)
    return {"asofMs": now_ms, "f": rows}


# ---------- FLOODS (task step 4g) ----------

def build_floods(old: dict, results: dict, now_ms: int, notes: list[str]) -> dict | None:
    data = ok(results, "flood_warnings")
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        notes.append("floods: Environment Agency warnings failed; FLOOD left unchanged")
        return None
    rows = []
    for it in items:
        fa = it.get("floodAreaID") or (it.get("floodArea") or {}).get("notation")
        rows.append([fa, it.get("description"), it.get("severityLevel"), it.get("severity"), it.get("message"),
                     it.get("timeRaised"), it.get("timeSeverityChanged")])
    g = dict(old.get("g") or {})
    for gid in GAUGES:
        d = ok(results, f"gauge_{gid}")
        its = d.get("items") if isinstance(d, dict) else None
        try:
            it = its[0]
            v = float(it["value"])
            t = int(datetime.fromisoformat(it["dateTime"].replace("Z", "+00:00")).timestamp() * 1000)
            if not -2 <= v <= 10:
                raise ValueError(f"value {v} outside -2..10")
            g[gid] = [t, v]
        except (TypeError, KeyError, IndexError, ValueError) as exc:
            notes.append(f"floods: gauge {gid} kept its last reading ({exc.__class__.__name__})")
    return {"asofMs": now_ms, "items": rows, "g": g}


# ---------- RELEASES ----------

def build_releases(old: dict, results: dict, now_ms: int, notes: list[str]) -> dict | None:
    names = [s[0] for s in old.get("sites", [])]
    status = ok(results, "bathing_releases")
    hist = ok(results, "bathing_release_history")
    sf = status.get("features") if isinstance(status, dict) else None
    hf = hist.get("features") if isinstance(hist, dict) else None
    if not isinstance(sf, list) or not isinstance(hf, list) or not hf:
        notes.append("releases: Southern Water Rivers and Seas Watch failed; RELEASES left unchanged")
        return None
    by = {(f.get("attributes") or {}).get("Name"): f["attributes"] for f in sf}
    missing = [n for n in names if n not in by]
    if missing:
        notes.append(f"releases: no status for {', '.join(missing)}; RELEASES left unchanged")
        return None
    sites = [[n, str(by[n]["ReleaseStatus"]), by[n]["SpillMessage"] or "", by[n]["Current_EA_Classification"] or ""]
             for n in names]
    since = now_ms - RELEASE_DAYS * 86_400_000
    ev = {}
    for f in hf:
        a = f.get("attributes") or {}
        if a.get("BathingSite") not in names or not isinstance(a.get("Start"), int) or a["Start"] < since:
            continue
        e = ev.setdefault(a["Event_ID"], [a["Event_ID"], a.get("Status"), a.get("Outfall"), a["Start"],
                                          a.get("End_"), a.get("End_Text"), {}])
        e[6][a["BathingSite"]] = a.get("Impact_Status")
    events = [e[:6] + [[[n, e[6][n]] for n in names if n in e[6]]] for e in ev.values()]
    events.sort(key=lambda e: (e[3], e[0]), reverse=True)
    return {"asofMs": now_ms, "sites": sites, "ev": events}


# ---------- TIDES ----------

def tide_window(table: dict, today) -> dict:
    lo, hi = (today - timedelta(days=1)).isoformat(), (today + timedelta(days=13)).isoformat()
    return {k: v for k, v in table.items() if lo <= k <= hi}


def build_tides(today, notes: list[str]):
    try:
        ram = json.loads((TIDE_DIR / "ramsgate.json").read_text(encoding="utf-8"))
        oth = json.loads((TIDE_DIR / "other-towns.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        notes.append(f"tides: tables not readable ({exc}); TIDES and TIDEX left unchanged")
        return None, None
    tides = tide_window(ram, today)
    tidex = {t: tide_window(v, today) for t, v in oth.items()}
    if today.isoformat() not in tides:
        notes.append(f"tides: the tables have no {today.isoformat()} (they cover 2026-2027); "
                     "TIDES and TIDEX left unchanged")
        return None, None
    return tides, tidex


# ---------- the page ----------

def refresh(html: str, src: dict, now: datetime) -> tuple[str, list[str], list[str]]:
    results, notes, done = src["results"], [], []
    now_ms = int(now.timestamp() * 1000)
    today = now.astimezone(LON).date()
    when = stamp(fetched_of(src))
    locs = build_locs(read_block(html, "LOCS"), results, today.isoformat(), when, now, notes)
    if locs is None:
        return html, done, notes
    html = set_block(html, "LOCS", locs); done.append("LOCS")
    air = rw.build_air(read_block(html, "AIR"), results)
    if air is None:
        notes.append("air: a Defra series failed or every reading was missing; AIR left unchanged")
    else:
        html = set_block(html, "AIR", air); done.append("AIR")
    for name, block in (("SPILLS", build_spills(results, now_ms, notes)),
                        ("FLOODS", build_floods(read_block(html, "FLOODS"), results, now_ms, notes)),
                        ("RELEASES", build_releases(read_block(html, "RELEASES"), results, now_ms, notes))):
        if block is not None:
            html = set_block(html, name, block); done.append(name)
    tides, tidex = build_tides(today, notes)
    if tides is not None:
        html = set_block(html, "TIDES", tides); html = set_block(html, "TIDEX", tidex)
        done += ["TIDES", "TIDEX"]
    return html, done, notes
