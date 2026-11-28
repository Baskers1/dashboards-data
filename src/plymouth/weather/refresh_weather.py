#!/usr/bin/env python3
"""Refresh the data blocks of the Plymouth & Ivybridge weather page from the Mac's
scrapekit file (out/plymouth-ivybridge.json).

usage: python3 refresh_weather.py page.html plymouth-ivybridge.json out.html

Replaces only these single-line blocks: TIDES, TIDEX, BAKED, BAKED_NOW, HOURLY, OM, FLOOD, SPILLS and AIR.
A block whose source failed or fails validation is left exactly as it was, and the
reason is printed. Exit status 2 if nothing at all could be refreshed, 1 if the page
handed in is unusable (still wrapped in Artifact's skeleton) or the source is stale.

Validation is in two layers. Shape: the counts and days each block needs. Sanity: the
units, place, clock and magnitude of the figures, so that a well-formed but wrong
payload (a unit flip, a wrong location, a stale reading) leaves the block alone
instead of publishing silently.
"""
import json, re, sys, time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LON = ZoneInfo("Europe/London")
TOWNS = ["plymouth", "ivybridge", "plympton", "plymstock", "saltash", "tavistock", "totnes"]  # order of the 'towns' source
# What scrapekit/scrapers/open_data.py asks Open-Meteo for, in TOWNS order.
COORDS = [(50.3755, -4.1427), (50.3896, -3.9203), (50.3860, -4.0510),
          (50.3590, -4.0900), (50.4080, -4.2120), (50.5490, -4.1440), (50.4319, -3.6847)]
# Open-Meteo answers on its own grid, so the echoed point sits up to ~0.02 deg off the
# request. 0.05 clears that and still catches a lat/lon swap, a wrong region or a
# different dataset.
# shortcut: too loose to spot Plympton and Plymstock (4 km apart) swapped with each
# other, when a tide or air station starts disagreeing with the forecast's place.
TOL = 0.05
UNITS = {"daily": {"temperature_2m_max": "°C", "temperature_2m_min": "°C", "precipitation_probability_max": "%",
                   "wind_speed_10m_max": "km/h", "wind_gusts_10m_max": "km/h"},
         "hourly": {"temperature_2m": "°C", "apparent_temperature": "°C", "dew_point_2m": "°C",
                    "precipitation": "mm", "precipitation_probability": "%", "relative_humidity_2m": "%",
                    "wind_speed_10m": "km/h", "wind_gusts_10m": "km/h", "cloud_cover": "%"},
         "current": {"temperature_2m": "°C", "apparent_temperature": "°C", "relative_humidity_2m": "%",
                     "wind_speed_10m": "km/h", "wind_gusts_10m": "km/h"}}
# A figure outside these is a bad reading, not weather. None is allowed throughout.
RANGES = {"temperature_2m": (-15, 40), "temperature_2m_max": (-15, 40), "temperature_2m_min": (-15, 40),
          "apparent_temperature": (-25, 45), "dew_point_2m": (-25, 35),
          "wind_speed_10m": (0, 200), "wind_speed_10m_max": (0, 200),
          "wind_gusts_10m": (0, 250), "wind_gusts_10m_max": (0, 250), "wind_direction_10m": (0, 360),
          "relative_humidity_2m": (0, 100), "precipitation_probability": (0, 100),
          "precipitation_probability_max": (0, 100), "precipitation": (0, 100), "cloud_cover": (0, 100),
          "uv_index": (0, 15), "visibility": (0, 100000), "weather_code": (0, 99)}
AIR_LAG_H = 4      # a Defra series this far behind the fetch is stale, not a reading
CURRENT_LAG_MIN = 90   # Open-Meteo's "current" should be within this of the fetch
GAUGES = ("46130", "46118", "47121", "E72139", "46122", "46155")
# Defra UK-AIR hourly series per station; the page works out each station's distance per town.
AIR_SERIES = {"P": {"no2": "406", "o3": "408", "pm10": "2262", "pm25": "2266"}, "S": {"pm10": "2294", "pm25": "2295"}}
AIR_NAMES = {"P": "Plymouth Centre", "S": "Saltash Callington Road"}
AIR_HOURS = 30
CP = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
WMO = {0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Fog",48:"Freezing fog",51:"Light drizzle",53:"Drizzle",55:"Heavy drizzle",56:"Freezing drizzle",57:"Freezing drizzle",61:"Light rain",63:"Rain",65:"Heavy rain",66:"Freezing rain",67:"Freezing rain",71:"Light snow",73:"Snow",75:"Heavy snow",77:"Snow grains",80:"Light showers",81:"Showers",82:"Heavy showers",85:"Snow showers",86:"Heavy snow showers",95:"Thunderstorm",96:"Thunderstorm with hail",99:"Thunderstorm with hail"}

def emoji(c):  # same mapping as the page's emoji()
    return "☀️" if c == 0 else "🌤️" if c < 3 else "☁️" if c == 3 else "🌫️" if c < 50 else "🌧️" if c < 70 else "🌨️" if c < 80 else "🌦️" if c < 95 else "⛈️"

def comp(deg): return CP[int(round((deg or 0) / 22.5)) % 16]
def r0(x): return None if x is None else int(round(x))
def r1(x): return None if x is None else round(x, 1)
J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))

def ms(s): return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)

def check_towns(R, today, fetched):
    """The 'towns' source, or ValueError saying why it cannot be trusted."""
    t = R.get("towns") or {}
    if not t.get("ok"):
        raise ValueError("source failed")
    towns = t.get("data")
    if not isinstance(towns, list) or len(towns) != len(TOWNS):
        raise ValueError(f"expected {len(TOWNS)} towns, got {len(towns) if isinstance(towns, list) else type(towns).__name__}")
    for tid, (lat, lon), x in zip(TOWNS, COORDS, towns):
        D = x.get("daily") or {}
        if len(D.get("time") or []) < 8:
            raise ValueError(f"{tid} has only {len(D.get('time') or [])} days")
        if D["time"][0] != today:
            raise ValueError(f"{tid} starts at {D['time'][0]}, not today ({today})")
        if abs(x.get("latitude", 0) - lat) > TOL or abs(x.get("longitude", 0) - lon) > TOL:
            raise ValueError(f"{tid} is at {x.get('latitude')},{x.get('longitude')}, expected near {lat},{lon}")
        if x.get("timezone") != "Europe/London":
            raise ValueError(f"{tid} timezone is {x.get('timezone')!r}, expected 'Europe/London'")
        want = fetched.astimezone(LON).utcoffset().total_seconds()
        if x.get("utc_offset_seconds") != want:
            raise ValueError(f"{tid} utc offset is {x.get('utc_offset_seconds')}, expected {int(want)}")
        for part, units in UNITS.items():
            got = x.get(f"{part}_units") or {}
            for k, u in units.items():
                if got.get(k) != u:
                    raise ValueError(f"{tid} {part} {k} is in {got.get(k)!r}, expected {u!r}")
        for part in ("daily", "hourly"):
            for k, vals in (x.get(part) or {}).items():
                lo, hi = RANGES.get(k, (None, None))
                if lo is None or not isinstance(vals, list):
                    continue
                for v in vals:
                    if v is not None and not lo <= v <= hi:
                        raise ValueError(f"{tid} {part} {k} has {v}, outside {lo}..{hi}")
        c = x.get("current") or {}
        for k, v in c.items():
            lo, hi = RANGES.get(k, (None, None))
            if lo is not None and v is not None and not lo <= v <= hi:
                raise ValueError(f"{tid} current {k} is {v}, outside {lo}..{hi}")
    c = towns[0]["current"]
    seen = datetime.fromisoformat(c["time"]).replace(tzinfo=LON)
    if seen.date().isoformat() != today:
        raise ValueError(f"current reading is dated {seen.date()}, not today ({today})")
    lag = (fetched - seen).total_seconds() / 60
    if not -15 <= lag <= CURRENT_LAG_MIN:
        raise ValueError(f"current reading is {lag:.0f} min from the fetch, outside -15..{CURRENT_LAG_MIN}")
    return towns

def tides_from(results, sun, place="plymouth"):
    out = {}
    for k, v in sorted(results.items()):
        if not k.startswith(f"tide_{place}_") or not v.get("ok"):
            continue
        day = k.rsplit("_", 1)[1]
        text = (v.get("data") or {}).get("text", "")
        i = text.find("Hi/Lo Time Height")
        rows, last = [], ""
        for hl, tm, ht in re.findall(r"(High|Low) (\d\d:\d\d) ([\d.]+)m", text[i:] if i >= 0 else ""):
            if tm < last:  # the page lists BST then repeats in GMT; stop at the repeat
                break
            rows.append([hl[0], tm, float(ht)]); last = tm
        if 2 <= len(rows) <= 5 and all(0 <= r[2] <= 7 for r in rows):
            if day in sun:
                rows += [["R", sun[day][0]], ["S", sun[day][1]]]
            out[day] = rows
    return out

def build_air(R, fetched):
    """(AIR block, None) from the Defra series, each pollutant AIR_HOURS long ending at
    the newest hour; (None, reason) if any series failed or the newest hour is stale."""
    got = {}
    for k, series in AIR_SERIES.items():
        for pol, sid in series.items():
            r = R.get(f"air_{sid}") or {}
            vals = (r.get("data") or {}).get("values") if r.get("ok") else None
            if not isinstance(vals, list):
                return None, f"series {sid} failed"
            got[(k, pol)] = {v["timestamp"]: (v["value"] if v.get("value") is not None and v["value"] >= 0 else None) for v in vals}  # -99 = missing
    stamps = [t for s in got.values() for t, v in s.items() if v is not None]
    if not stamps:
        return None, "every reading was missing"
    last = max(stamps)
    lag = (fetched.timestamp() * 1000 - last) / 3600_000
    if lag > AIR_LAG_H:
        return None, f"newest reading is {lag:.1f} h behind the fetch (limit {AIR_LAG_H})"
    for (k, pol), s in got.items():
        bad = [v for v in s.values() if v is not None and not 0 <= v <= 1000]
        if bad:
            return None, f"{AIR_NAMES[k]} {pol} has {bad[0]}, outside 0..1000"
    st = [{"n": AIR_NAMES[k], "k": k, "km": 0, "dir": "",
           **{pol: [got[(k, pol)].get(last - 3600_000 * (AIR_HOURS - 1 - j)) for j in range(AIR_HOURS)] for pol in series}}
          for k, series in AIR_SERIES.items()]
    when = datetime.fromtimestamp(last / 1000, timezone.utc).astimezone(LON).strftime("%-d %b, %H:%M")
    return {"last": last, "when": when, "st": st}, None

def build(src, now, old):
    R = src["results"]; blocks = {}; notes = []
    today = now.date().isoformat()
    fetched = datetime.fromisoformat(src["fetched_at"])
    when = min([datetime.fromisoformat(r["reused_from"]) for r in R.values() if r.get("reused_from")] or [fetched]).astimezone(LON).strftime("%-d %b, %H:%M")  # when the Mac fetched it
    try:
        towns = check_towns(R, today, fetched)
        om = {"when": when, "t": {}}
        for tid, x in zip(TOWNS, towns):
            D, H = x["daily"], x["hourly"]
            d = [[D["time"][i], D["weather_code"][i], r0(D["temperature_2m_max"][i]), r0(D["temperature_2m_min"][i]),
                  r0(D["precipitation_probability_max"][i] or 0), r0(D["wind_speed_10m_max"][i]), r0(D["wind_gusts_10m_max"][i])] for i in range(8)]
            h = [[H["time"][i][11:16], r0(H["temperature_2m"][i]), r0(H["precipitation_probability"][i] or 0), r0(H["wind_gusts_10m"][i]),
                  r0(H["wind_speed_10m"][i]), r0(H["wind_direction_10m"][i]), H["weather_code"][i], r1(H["precipitation"][i]),
                  r0(H["apparent_temperature"][i]), r0(H["dew_point_2m"][i]), r0(H["relative_humidity_2m"][i]), r0(H["cloud_cover"][i]),
                  r1(H["uv_index"][i]), r1((H["visibility"][i] or 0) / 1000)] for i, ts in enumerate(H["time"]) if ts[:10] == today]
            if len(h) < 24:
                raise ValueError(f"{tid} has only {len(h)} hours for today")
            om["t"][tid] = {"d": d, "h": h}
        p = towns[0]; D = p["daily"]; c = p["current"]
        blocks["OM"] = om
        blocks["BAKED"] = [[D["time"][i], r0(D["temperature_2m_max"][i]), r0(D["temperature_2m_min"][i]), WMO.get(D["weather_code"][i], ""),
                            r0(D["precipitation_probability_max"][i] or 0), r0(D["wind_speed_10m_max"][i]), r0(D["wind_gusts_10m_max"][i]),
                            emoji(D["weather_code"][i])] for i in range(8)]
        blocks["BAKED_NOW"] = {"t": r0(c["temperature_2m"]), "e": emoji(c["weather_code"]), "phrase": WMO.get(c["weather_code"], ""),
                               "wind": f"{comp(c['wind_direction_10m'])} {r0(c['wind_speed_10m'])} km/h", "gust": r0(c["wind_gusts_10m"]),
                               "hum": r0(c["relative_humidity_2m"]), "when": when}
        sr, ss = D["sunrise"][0][11:16], D["sunset"][0][11:16]
        night = lambda r: (r[0][:2] + ":30" < sr or r[0][:2] + ":30" > ss) and r[6] < 2
        blocks["HOURLY"] = {"date": today, "when": when, "back": "",
                            "rows": [[r[0], r[1], r[2], r[3], r[4], comp(r[5]), "\U0001F319" if night(r) else emoji(r[6]), ("Clear" if night(r) else WMO.get(r[6], "")), r[7], r[8], r[9], r[10], r[11], r[12], r[13],
                                      None] for r in om["t"]["plymouth"]["h"]]}
        suns = {tid: {x["daily"]["time"][i]: [x["daily"]["sunrise"][i][11:16], x["daily"]["sunset"][i][11:16]]
                      for i in range(len(x["daily"]["time"]))} for tid, x in zip(TOWNS, towns)}
    except ValueError as exc:
        notes.append(f"towns: {exc}: OM, BAKED, BAKED_NOW, HOURLY left unchanged")
        suns = {}
    # TIDES/TIDEX take their sunrise/sunset rows from the towns payload, so a towns
    # failure has to hold them too: refreshing without those rows renders the page's
    # eight day cards as "Sunrise undefined" (the 2 Nov 15:44 regression).
    nosun = "towns failed, so no sunrise/sunset rows"
    sun = suns.get("plymouth") or {}
    tides = tides_from(R, sun) if sun else {}
    why = nosun if not sun else f"only {len(tides)} usable days (need today + 2)"
    if len(tides) >= 3 and today in tides:
        blocks["TIDES"] = tides
    else:
        notes.append(f"tides: {why}: TIDES left unchanged")
    sunx = suns.get("totnes") or {}
    tx = tides_from(R, sunx, "totnes") if sunx else {}  # TIDEX: towns with their own table
    why = nosun if not sunx else f"only {len(tx)} usable days (need today + 2)"
    if len(tx) >= 3 and today in tx:
        blocks["TIDEX"] = {"totnes": tx}
    else:
        notes.append(f"totnes tides: {why}: TIDEX left unchanged")
    asof = int(time.time() * 1000)
    fw = R.get("flood_warnings", {})
    if fw.get("ok") and isinstance((fw.get("data") or {}).get("items"), list):
        g = {}
        for sid in GAUGES:
            it = ((R.get(f"gauge_{sid}") or {}).get("data") or {}).get("items") or []
            if it and isinstance(it[0].get("value"), (int, float)) and -2 <= it[0]["value"] <= 10:
                g[sid] = [ms(it[0]["dateTime"]), it[0]["value"]]
        for sid, v in ((old.get("FLOOD") or {}).get("g") or {}).items():
            g.setdefault(sid, v)  # a gauge that failed keeps its last reading
        blocks["FLOOD"] = {"asofMs": asof, "items": [[i.get("floodAreaID") or i["floodArea"]["notation"], i.get("description", ""), i.get("severityLevel"),
                                                       i.get("severity", ""), i.get("message", ""), i.get("timeRaised", ""), i.get("timeSeverityChanged", "")]
                                                      for i in fw["data"]["items"]], "g": g}
    else:
        notes.append("flood_warnings failed: FLOOD left unchanged")
    so = R.get("storm_overflows", {})
    feats = (so.get("data") or {}).get("features") if so.get("ok") else None
    try:
        if not isinstance(feats, list) or len(feats) < 50:
            raise ValueError(f"source failed or too few rows ({len(feats) if isinstance(feats, list) else 'none'})")
        rows = []
        for f in feats:
            a = f["attributes"]
            if a.get("status") not in (-1, 0, 1):
                raise ValueError(f"unexpected status {a.get('status')!r} for {a.get('Id')}")
            if not (50.25 < (a.get("latitude") or 0) < 50.65 and -4.40 < (a.get("longitude") or 0) < -3.55):
                continue  # outside the seven towns' area
            rows.append([a["Id"], a["status"], a.get("latestEventStart"), a.get("latestEventEnd"), a["latitude"], a["longitude"], a.get("receivingWaterCourse") or ""])
        was = len((old.get("SPILLS") or {}).get("f") or [])
        if was and len(rows) * 2 < was:
            raise ValueError(f"{len(rows)} rows in the area, less than half the {was} on the page")
        blocks["SPILLS"] = {"asofMs": asof, "f": rows}
    except ValueError as exc:
        notes.append(f"storm_overflows: {exc}: SPILLS left unchanged")
    air, why = build_air(R, fetched)
    if air:
        blocks["AIR"] = air
    else:
        notes.append(f"air: {why}: AIR left unchanged")
    return blocks, notes

def oldblock(L, name):
    for l in L:
        if l.startswith(f"var {name}="):
            return json.loads(l[len(name) + 5:].rstrip(";"))
    return None

def main():
    page, srcp, outp = sys.argv[1:4]
    html = open(page, encoding="utf-8").read(); L = html.split("\n")
    for marker in ("<!doctype html>", "</html>", "</body>"):
        n = html.lower().count(marker)
        if n != 1:
            sys.exit(f"page has {n} '{marker}', expected 1: strip Artifact's skeleton before refreshing")
    src = json.load(open(srcp, encoding="utf-8"))
    fetched = datetime.fromisoformat(src["fetched_at"])
    age_h = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
    print(f"source fetched_at {src['fetched_at']} ({age_h:.1f} h old); failed: {src.get('sources_failed')}")
    if age_h > 6:
        print("source is more than 6 hours old: nothing refreshed"); sys.exit(2)
    old = {n: oldblock(L, n) for n in ("FLOOD", "SPILLS")}
    blocks, notes = build(src, datetime.now(LON), old)
    for name, val in blocks.items():
        idx = [i for i, l in enumerate(L) if l.startswith(f"var {name}=")]
        assert len(idx) == 1, f"{name}: expected one line, found {len(idx)}"
        L[idx[0]] = f"var {name}={J(val)};"
    open(outp, "w", encoding="utf-8").write("\n".join(L))
    print("refreshed:", ", ".join(blocks) or "nothing")
    for n in notes: print("note:", n)
    sys.exit(0 if blocks else 2)

if __name__ == "__main__":
    main()
