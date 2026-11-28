"""Refresh every data block of the Plymouth & Ivybridge · Weather page (weather template) from one hour's Mac file.

Used by weather-template/refresh_data.py (mode "page_script"): refresh(page, src, now) returns
(page, done, notes). Blocks, and what used to build them:

- LOCS      all seven towns from the one multi-place Open-Meteo answer ("towns"), each through
            om_rows.place_block, after refresh_weather.check_towns has checked the whole answer
            (units, coordinates, timezone, ranges, the "current" reading's age against the fetch).
            Was: refresh_weather.py's BAKED, BAKED_NOW and HOURLY for Plymouth and OM for the
            other six, which only Plymouth had a "now" for. Every town now has its own.
- AIR, SPILLS, TIDES, TIDEX   refresh_weather.build(), unchanged rules and sanity checks.
- FLOODS    refresh_weather.build()'s FLOOD block (warnings and the six gauges). The page calls it FLOOD.

RELEASES has no source here (South West Water publishes no release history), so build.py
writes it as null and the page shows nothing for it, as before.

A block whose source fails or fails a check is left exactly as it was, with a note saying why.
LOCS needs the towns answer and Plymouth itself, or nothing is written (refresh_data.py exits 2).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scrapekit" / "scrapers"))
import importlib.util  # noqa: E402
# load this folder's refresh_weather.py by path: every area has one, and a plain import would
# reuse whichever area's module was imported first in the same process
_spec = importlib.util.spec_from_file_location("plymouth_refresh_weather", HERE / "refresh_weather.py")
rw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rw)
from om_rows import place_block  # noqa: E402

LON = ZoneInfo("Europe/London")
J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
# refresh_weather.build() name -> this page's block name
FROM_BUILD = {"AIR": "AIR", "SPILLS": "SPILLS", "FLOOD": "FLOODS", "TIDES": "TIDES", "TIDEX": "TIDEX"}


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


def when_of(src: dict) -> str:
    """The time shown on the page: when the Mac really fetched the data (refresh_weather's rule)."""
    R = src["results"]
    fetched = datetime.fromisoformat(src["fetched_at"])
    return min([datetime.fromisoformat(r["reused_from"]) for r in R.values() if r.get("reused_from")]
               or [fetched]).astimezone(LON).strftime("%-d %b, %H:%M")


def build_locs(old: dict, src: dict, today: str, notes: list[str]) -> dict | None:
    R = src["results"]
    try:
        towns = rw.check_towns(R, today, datetime.fromisoformat(src["fetched_at"]))
    except ValueError as exc:
        notes.append(f"weather: towns: {exc}; weather NOT refreshed")
        return None
    out = json.loads(json.dumps(old))
    when = when_of(src)
    for tid, om in zip(rw.TOWNS, towns):
        try:
            # now=None: check_towns has already held the "current" reading to within
            # 90 minutes of the fetch, and refresh_data.py refuses data over 6 hours old
            out[tid].update(place_block(om, today, when))
        except (ValueError, KeyError, TypeError) as exc:
            if tid == "plymouth":
                notes.append(f"weather: Plymouth: {exc}; weather NOT refreshed")
                return None
            notes.append(f"weather: {out[tid]['name']}: {exc}; left unchanged")
    return out


def refresh(html: str, src: dict, now: datetime) -> tuple[str, list[str], list[str]]:
    notes, done = [], []
    now_l = now.astimezone(LON)
    locs = build_locs(read_block(html, "LOCS"), src, now_l.date().isoformat(), notes)
    if locs is None:
        return html, done, notes
    html = set_block(html, "LOCS", locs); done.append("LOCS")
    old = {"FLOOD": read_block(html, "FLOODS"), "SPILLS": read_block(html, "SPILLS")}
    blocks, more = rw.build(src, now_l, old)
    # build() also makes the old page's OM, BAKED, BAKED_NOW and HOURLY; LOCS replaces them,
    # so its notes about those are dropped and LOCS's own notes stand instead
    notes += [n for n in more if not n.startswith("towns:")]
    stamp_ms = int(now.timestamp() * 1000)
    for name, block in FROM_BUILD.items():
        if name in blocks:
            val = blocks[name]
            if name in ("FLOOD", "SPILLS"):
                val = {**val, "asofMs": stamp_ms}  # build() stamps time.time(); use this run's clock
            html = set_block(html, block, val); done.append(block)
    return html, done, notes
