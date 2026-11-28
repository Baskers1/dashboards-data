"""Refresh every data block of the Tayside · Weather page from one hour's Mac file.

    python3 refresh_page.py page.html tayside.json out.html

LOCS and AIR come from refresh_weather.py, unchanged. This module adds the five blocks
the hourly task used to copy out of page text by hand (task prompt steps 4 to 7, as they
stood on 22 Nov 2026):

- RIVERS   SEPA station pages for the Tay at Ballathie and Dighty Water at Balmossie
- FLOODS   SEPA live flooding page (head, items) and the Scottish Flood Forecast (fc)
- TIDES    tidetimes.org.uk day pages for Dundee and Arbroath, yesterday to +6 days
- BATHING  SEPA bathing water results for Broughty Ferry and Carnoustie
- SPILLS   Scottish Water storm overflow monitors (ArcGIS layer)

Each block is built from its own sources and checked before it is written. A block whose
source failed, or whose text no longer reads as expected, is left exactly as it was, with
a line saying why: a scraper must never put guessed or partial figures on the page.

Floods: when SEPA lists any alert or warning in force, the list's wording has not yet been
seen in a saved page, so FLOODS is written with items [] and unparsed true (the page then
sends readers to SEPA) and a note says so. Upgrade the parser the first time one is live.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scrapekit" / "scrapers"))
import importlib.util  # noqa: E402
# load this folder's refresh_weather.py by path: every area has one, and a plain import would
# reuse whichever area's module was imported first in the same process
_spec = importlib.util.spec_from_file_location("tayside_refresh_weather", HERE / "refresh_weather.py")
rw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rw)
from om_rows import ok, read_line, set_line  # noqa: E402

LON = ZoneInfo("Europe/London")
RIVER_SOURCES = {"14937": "river_tay_ballathie", "14919": "river_dighty_balmossie"}
BATHING_SOURCES = {"bf": "bathing_broughty_ferry", "cn": "bathing_carnoustie"}
TIDE_PLACES = ("dundee", "arbroath")
CLASSES = "Excellent|Good|Sufficient|Poor"
MONTHS = "January February March April May June July August September October November December".split()


class Unreadable(ValueError):
    """The source was fetched, but its text no longer reads as expected."""


def text_of(results: dict, name: str) -> str:
    data = ok(results, name)
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        err = (results.get(name) or {}).get("error") or "missing"
        raise Unreadable(f"{name} not available ({err})")
    return re.sub(r"\s+", " ", data["text"])


def need(pattern: str, text: str, what: str, flags=0):
    m = re.search(pattern, text, flags)
    if not m:
        raise Unreadable(f"no {what} found")
    return m


def num(s: str) -> float:
    return float(s)


# ---------- RIVERS (task step 4) ----------

def parse_river(text: str) -> dict:
    t = need(r"Latest at (.+?) View station details", text, "'Latest at' line").group(1).strip()
    lv = need(r"known as the Gauge Datum\. (-?[\d.]+)m Trend", text, "level").group(1)
    trend = need(r"from the last value\. (.+?) State ", text, "trend").group(1).strip()
    state = need(r"for more information\. (.+?) (?:Normal range|Level in metres)", text, "state").group(1).strip()
    mx = need(r"(-?[\d.]+)m The maximum level recorded at the station \(recorded on (.+?) \)", text, "maximum")
    top = need(r"(-?[\d.]+)m This level is at the top of the normal range", text, "top of normal range").group(1)
    mn = need(r"(-?[\d.]+)m Lowest level ever recorded", text, "lowest level").group(1)
    if len(t) > 60 or len(trend) > 40 or len(state) > 40:
        raise Unreadable("river text did not split where expected")
    return {"t": t, "lv": num(lv), "trend": trend, "state": state, "top": num(top),
            "max": num(mx.group(1)), "maxd": mx.group(2).strip(), "min": num(mn)}


def build_rivers(old: dict, results: dict, now_ms: int, notes: list[str]) -> dict | None:
    out = json.loads(json.dumps(old))
    changed = 0
    for st in out["st"]:
        src = RIVER_SOURCES.get(st["id"])
        if not src:
            notes.append(f"rivers: no source for station {st['id']}; left unchanged")
            continue
        try:
            st.update(parse_river(text_of(results, src)))
            changed += 1
        except Unreadable as exc:
            notes.append(f"rivers: {st['n']}: {exc}; left unchanged")
    if not changed:
        return None
    out["asofMs"] = now_ms
    return out


# ---------- FLOODS (task step 4A) ----------

def d_mon(day: int, month: int) -> str:
    return f"{day} {MONTHS[month - 1][:3]}"


def parse_warnings(text: str) -> dict:
    m = need(r"Last updated: (\d{1,2})(?:st|nd|rd|th) (\w+) (\d{4}) at (\d\d:\d\d)", text, "'Last updated' stamp")
    sepa = f"{int(m.group(1))} {m.group(2)[:3]}, {m.group(4)}"
    head = need(r"(There (?:are|is) [^.]*? in force in Scotland)", text, "statement of what is in force").group(1)
    if re.fullmatch(r"There are no flood alerts or warnings currently in force in Scotland", head):
        return {"sepa": sepa, "head": head, "items": [], "elsewhere": 0, "unparsed": False}
    return {"sepa": sepa, "head": head, "items": [], "elsewhere": 0, "unparsed": True}


def parse_forecast(text: str) -> dict:
    m = need(r"Last updated on (\d\d)/(\d\d)/(\d{4}) at (\d\d:\d\d)", text, "forecast 'Last updated on' stamp")
    upd = f"{d_mon(int(m.group(1)), int(m.group(2)))}, {m.group(4)}"
    summ = need(r"Summary (.+?) (?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day \d{1,2} \w+ \d{4}", text, "summary").group(1)
    days = []
    for m in re.finditer(r"Flood risks for (\w+day) (\d{1,2}) (\w+) \d{4} - (.+?)(?= Flood risks for | Sign up)", text):
        sent = m.group(4).strip()
        half = len(sent) // 2
        if len(sent) % 2 == 1 and sent[:half] == sent[half + 1:]:
            sent = sent[:half]  # the page states each impact twice (visible and screen-reader text)
        days.append([f"{m.group(1)[:3]} {int(m.group(2))} {m.group(3)[:3]}", sent])
    if len(days) != 3:
        raise Unreadable(f"expected 3 forecast days, found {len(days)}")
    return {"upd": upd, "sum": summ.strip(), "days": days}


def build_floods(old: dict, results: dict, now_ms: int, notes: list[str]) -> dict | None:
    try:
        a = parse_warnings(text_of(results, "flood_warnings"))
    except Unreadable as exc:
        notes.append(f"floods: live page: {exc}; FLOODS left unchanged")
        return None
    if a["unparsed"]:
        notes.append(f"floods: SEPA lists alerts or warnings in force ('{a['head']}'); the list could not be "
                     "read, so the page shows it as unreadable and points to SEPA")
    try:
        fc = parse_forecast(text_of(results, "flood_forecast"))
    except Unreadable as exc:
        notes.append(f"floods: forecast page: {exc}; forecast kept")
        fc = old.get("fc")
    return {"asofMs": now_ms, **a, "fc": fc}


# ---------- TIDES (task step 5) ----------

def parse_tides(text: str) -> list:
    seg = need(r"Tide Times (?:BST|GMT|UTC): Hi/Lo Time Height (.+?) NOT TO BE USED", text, "tide table").group(1)
    rows = re.findall(r"(High|Low) (\d\d:\d\d) ([\d.]+)m", seg)
    if not 2 <= len(rows) <= 4 or len(re.findall(r"\b(?:High|Low)\b", seg)) != len(rows):
        raise Unreadable(f"tide table did not read cleanly ({len(rows)} rows)")
    rise = need(r"Sunrise : (\d\d:\d\d)", text, "sunrise").group(1)
    sset = need(r"Sunset : (\d\d:\d\d)", text, "sunset").group(1)
    out = sorted(([r[0][0], r[1], num(r[2])] for r in rows), key=lambda x: x[1])
    return out + [["R", rise], ["S", sset]]


def build_tides(old: dict, results: dict, today: date, notes: list[str]) -> dict | None:
    out, got, missing = {}, 0, []
    first, last = today - timedelta(days=1), today + timedelta(days=7)
    for place in TIDE_PLACES:
        days = {k: v for k, v in (old.get(place) or {}).items() if first.isoformat() <= k <= last.isoformat()}
        for i in range(-1, 7):
            d = (today + timedelta(days=i)).isoformat()
            name = f"tide_{place}_{d}"
            try:
                days[d] = parse_tides(text_of(results, name))
                got += 1
            except Unreadable as exc:
                missing.append(f"{name}: {exc}")
        out[place] = dict(sorted(days.items()))
    if missing:
        notes.append("tides: kept the existing day for " + "; ".join(missing))
    return out if got else None


# ---------- BATHING (task step 6) ----------

def parse_bathing(text: str) -> dict:
    m = need(r"Current classification : (\w+) \(Awarded in (\d{4})\)", text, "current classification")
    grid = need(r"Grid ref : (\S+)", text, "grid reference").group(1)
    seg = need(r"Intestinal enterococci \(cfu/100ml\) (.+?) Historic results", text, "sample results").group(1)
    samples = re.findall(r"(\d{2} \w+ \d{4}) (\S+) (\S+)", seg)
    hseg = need(r"Year Classification (.+?)(?: UKAS| Results explained|$)", text, "historic results").group(1)
    hist = [[int(y), c] for y, c in re.findall(rf"(\d{{4}}) ({CLASSES})\b", hseg)]
    if not samples or not hist:
        raise Unreadable("no sample or historic rows")
    return {"grid": grid, "cls": m.group(1), "yr": int(m.group(2)),
            "s": [list(r) for r in samples[::-1][:6]], "h": hist}


def build_bathing(old: dict, results: dict, notes: list[str]) -> dict | None:
    out, got = json.loads(json.dumps(old)), 0
    for key, src in BATHING_SOURCES.items():
        try:
            out.setdefault(key, {}).update(parse_bathing(text_of(results, src)))
            got += 1
        except Unreadable as exc:
            notes.append(f"bathing: {key}: {exc}; left unchanged")
    return out if got else None


# ---------- SPILLS (task step 7) ----------

def build_spills(old: dict, results: dict, now_ms: int, notes: list[str]) -> dict | None:
    data = ok(results, "storm_overflows")
    feats = (data or {}).get("features") if isinstance(data, dict) else None
    if not isinstance(feats, list):
        notes.append("overflows: Scottish Water layer not available; SPILLS left unchanged")
        return None
    if not feats:
        notes.append("overflows: Scottish Water layer returned no monitors; SPILLS left unchanged")
        return None
    short = {r[0]: r[12] for r in old.get("f", [])}
    rows = []
    for f in feats:
        a = f["attributes"]
        name = a["ASSET_NAME"]
        if name not in short:
            notes.append(f"overflows: new monitor {name} at {a['DISCHARGE_OVERFLOW_LOCATION_LATITUDE']}, "
                         f"{a['DISCHARGE_OVERFLOW_LOCATION_LONGITUDE']}")
        rows.append([name, (a["OVERFLOW_STATUS_DESCRIPTION"] or "")[:2], a["OVERFLOW_START_DATETIME"],
                     a["OVERFLOW_END_DATETIME"], a["DISCHARGE_OVERFLOW_LOCATION_LATITUDE"],
                     a["DISCHARGE_OVERFLOW_LOCATION_LONGITUDE"], a["RECEIVING_WATER"],
                     a["DISCHARGE_OVERFLOW_LOCATION_POSTCODE"], a["OVERFLOW_DURATION_MIN"],
                     a.get("TOTAL_OVERFLOWS_DURATION_MIN_PAST_48_HRS"), a["LAST_TRANSMITTED_DATETIME"],
                     a["OVERFLOW_TYPE"], short.get(name) or name.title()])
    bad = [r[0] for r in rows if r[1] not in ("NO", "RO", "DA")]
    if bad:
        notes.append(f"overflows: unexpected status for {', '.join(bad)}; SPILLS left unchanged")
        return None
    return {"asofMs": now_ms, "f": rows}


# ---------- the page ----------

def refresh(html: str, src: dict, now: datetime) -> tuple[str, list[str], list[str]]:
    html, done, notes = rw.refresh(html, src, now)
    if "LOCS" not in done:
        return html, done, notes
    results = src["results"]
    lines = html.split("\n")
    now_ms = int(now.timestamp() * 1000)
    today = now.astimezone(LON).date()
    builders = {
        "RIVERS": lambda old: build_rivers(old, results, now_ms, notes),
        "FLOODS": lambda old: build_floods(old, results, now_ms, notes),
        "TIDES": lambda old: build_tides(old, results, today, notes),
        "BATHING": lambda old: build_bathing(old, results, notes),
        "SPILLS": lambda old: build_spills(old, results, now_ms, notes),
    }
    for name, build in builders.items():
        new = build(read_line(lines, name))
        if new is None:
            notes.append(f"{name} left unchanged")
            continue
        set_line(lines, name, new)
        done.append(name)
    return "\n".join(lines), done, notes


def main() -> int:
    page, srcp, outp = sys.argv[1:4]
    src = json.loads(Path(srcp).read_text(encoding="utf-8"))
    age = datetime.now(timezone.utc) - datetime.fromisoformat(src["fetched_at"])
    print(f"source fetched_at {src['fetched_at']} ({age.total_seconds() / 3600:.1f} h old); "
          f"failed: {src.get('sources_failed')}")
    if age > timedelta(hours=rw.MAX_AGE_H):
        print(f"source is more than {rw.MAX_AGE_H} hours old: nothing refreshed")
        return 2
    html, done, notes = refresh(Path(page).read_text(encoding="utf-8"), src, datetime.now(timezone.utc))
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
