"""Turn one place's Open-Meteo forecast JSON into the weather blocks the area
weather pages render (MIGRATION-PLAN Phase 2: one converter for every page).

    from om_rows import place_block, OM_PARAMS
    url = "https://api.open-meteo.com/v1/forecast?latitude=..&longitude=.." + OM_PARAMS
    block = place_block(response_json, today="2026-10-30", when="30 Oct, 09:28")
    # -> {"baked": [...], "now": {...}, "hourly": {"date", "when", "rows"}}

Row shapes match the pages' LOCS blocks (see tayside weather-refresh-playbook.md):
- baked:  [date, hi, lo, phrase, rainProb, wind, gust, emoji]
- hourly: [time, temp, rainProb, gust, wind, dir, emoji, phrase, rainMm, feelsLike,
           dewPoint, humidity, cloud, uv, visKm, None, "om"]
  Element 15 (thunderstorm %) is always None: Open-Meteo has no such field and the
  repo rule is never to derive one.

Raises ValueError on missing, short or implausible data instead of returning a
partial block. Beyond shape, it checks the things that would otherwise publish a
well-formed but wrong page: the units every figure is in, the clock the forecast is
on, and the magnitude of each value. Callers already turn a ValueError into "left
unchanged" plus a note, so a failed check keeps the previous good block on the page.
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

OM_PARAMS = (
    "&timezone=Europe%2FLondon&wind_speed_unit=kmh&forecast_days=8"
    "&current=temperature_2m,relative_humidity_2m,weather_code,"
    "wind_speed_10m,wind_direction_10m,wind_gusts_10m"
    "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
    "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,"
    "sunrise,sunset"
    "&hourly=temperature_2m,precipitation_probability,precipitation,"
    "wind_gusts_10m,wind_speed_10m,wind_direction_10m,weather_code,"
    "apparent_temperature,dew_point_2m,relative_humidity_2m,"
    "cloud_cover,uv_index,visibility"
)

# Every WMO code Open-Meteo returns. English wording follows sky/fetch_weather.py so
# the Welsh in sky/cy.py carries over; the five codes the sky list lacks are added.
PHRASE = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}

# Welsh for each phrase above (first 22 as in sky/cy.py WXP). Machine-written:
# not yet checked by a fluent speaker.
PHRASE_CY = {
    "Clear": "Clir", "Mostly clear": "Clir gan fwyaf", "Partly cloudy": "Rhannol gymylog",
    "Overcast": "Cymylog iawn", "Foggy": "Niwlog", "Rime fog": "Niwl barrug",
    "Light drizzle": "Glaw mân ysgafn", "Moderate drizzle": "Glaw mân cymedrol",
    "Heavy drizzle": "Glaw mân trwm", "Freezing drizzle": "Glaw mân rhewllyd",
    "Slight rain": "Glaw ysgafn", "Moderate rain": "Glaw cymedrol", "Heavy rain": "Glaw trwm",
    "Freezing rain": "Glaw rhewllyd",
    "Slight snow": "Eira ysgafn", "Moderate snow": "Eira cymedrol", "Heavy snow": "Eira trwm",
    "Snow grains": "Gronynnau eira",
    "Slight showers": "Cawodydd ysgafn", "Moderate showers": "Cawodydd cymedrol",
    "Violent showers": "Cawodydd ffyrnig",
    "Slight snow showers": "Cawodydd eira ysgafn", "Heavy snow showers": "Cawodydd eira trwm",
    "Thunderstorm": "Storm fellt a tharanau",
    "Thunderstorm with hail": "Storm fellt a tharanau gyda chenllysg",
}

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

TZ = "Europe/London"
CURRENT_LAG_MIN = 90   # Open-Meteo's "current" should be this close to the fetch

# The unit each field OM_PARAMS asks for comes back in. Temperature is the dangerous
# one: OM_PARAMS does not name it, so it rides on Open-Meteo's default, and a change
# there would scale every figure on the page with nothing downstream noticing.
UNITS = {
    "daily": {"temperature_2m_max": "\u00b0C", "temperature_2m_min": "\u00b0C",
              "precipitation_probability_max": "%", "wind_speed_10m_max": "km/h",
              "wind_gusts_10m_max": "km/h"},
    "hourly": {"temperature_2m": "\u00b0C", "apparent_temperature": "\u00b0C",
               "dew_point_2m": "\u00b0C", "precipitation": "mm",
               "precipitation_probability": "%", "relative_humidity_2m": "%",
               "cloud_cover": "%", "visibility": "m", "wind_speed_10m": "km/h",
               "wind_gusts_10m": "km/h", "wind_direction_10m": "\u00b0"},
    "current": {"temperature_2m": "\u00b0C", "relative_humidity_2m": "%",
                "wind_speed_10m": "km/h", "wind_gusts_10m": "km/h",
                "wind_direction_10m": "\u00b0"},
}

# A figure outside these is a bad reading, not weather. None is allowed throughout.
# These also catch a field landing in the wrong slot, which is likelier than a spike.
RANGES = {
    "temperature_2m": (-25, 45), "temperature_2m_max": (-25, 45),
    "temperature_2m_min": (-25, 45), "apparent_temperature": (-35, 50),
    "dew_point_2m": (-35, 40),
    "wind_speed_10m": (0, 200), "wind_speed_10m_max": (0, 200),
    "wind_gusts_10m": (0, 250), "wind_gusts_10m_max": (0, 250),
    "wind_direction_10m": (0, 360), "relative_humidity_2m": (0, 100),
    "precipitation_probability": (0, 100), "precipitation_probability_max": (0, 100),
    "precipitation": (0, 100), "cloud_cover": (0, 100), "uv_index": (0, 15),
    "visibility": (0, 100000), "weather_code": (0, 99),
}


def check_om(om: dict, today: str, now: datetime | None = None) -> None:
    """Raise ValueError if the response is in the wrong units, on the wrong clock, or
    carries an implausible figure. `now` enables the "current" reading's age check."""
    for part, units in UNITS.items():
        got = om.get(f"{part}_units")
        if not isinstance(got, dict):
            raise ValueError(f"response has no '{part}_units' block")
        for key, unit in units.items():
            if got.get(key) != unit:
                raise ValueError(f"{part} {key} is in {got.get(key)!r}, expected {unit!r}")
    if om.get("timezone") != TZ:
        raise ValueError(f"timezone is {om.get('timezone')!r}, expected {TZ!r}")
    want = datetime.fromisoformat(f"{today}T12:00").replace(tzinfo=ZoneInfo(TZ)).utcoffset()
    if om.get("utc_offset_seconds") != want.total_seconds():
        raise ValueError(f"utc offset is {om.get('utc_offset_seconds')}, "
                         f"expected {int(want.total_seconds())} for {TZ} on {today}")
    for part in ("daily", "hourly"):
        for key, vals in (om.get(part) or {}).items():
            lo_hi = RANGES.get(key)
            if lo_hi is None or not isinstance(vals, list):
                continue
            for v in vals:
                if v is not None and not lo_hi[0] <= v <= lo_hi[1]:
                    raise ValueError(f"{part} {key} has {v}, outside {lo_hi[0]}..{lo_hi[1]}")
    cur = om.get("current") or {}
    for key, v in cur.items():
        lo_hi = RANGES.get(key)
        if lo_hi is not None and v is not None and not lo_hi[0] <= v <= lo_hi[1]:
            raise ValueError(f"current {key} is {v}, outside {lo_hi[0]}..{lo_hi[1]}")
    seen = cur.get("time")
    if not isinstance(seen, str) or seen[:10] != today:
        raise ValueError(f"current reading is dated {seen!r}, not today ({today})")
    if now is not None:
        lag = (now - datetime.fromisoformat(seen).replace(tzinfo=ZoneInfo(TZ))).total_seconds() / 60
        if not -15 <= lag <= CURRENT_LAG_MIN:
            raise ValueError(f"current reading is {lag:.0f} min from now, "
                             f"outside -15..{CURRENT_LAG_MIN}")


def phrase(code: int) -> str:
    if code not in PHRASE:
        raise ValueError(f"unknown WMO weather code {code}")
    return PHRASE[code]


def emoji(code: int) -> str:  # same thresholds as the pages' own emoji()
    return ("☀️" if code == 0 else "🌤️" if code < 3 else "☁️" if code == 3 else
            "🌫️" if code < 50 else "🌧️" if code < 70 else "🌨️" if code < 80 else
            "🌦️" if code < 95 else "⛈️")


def compass(deg: float) -> str:
    return COMPASS[int((deg % 360) / 22.5 + 0.5) % 16]


def r0(x: float | None) -> int | None:
    """Round half up, as the playbook requires (Python's round() is half-to-even)."""
    return None if x is None else int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def r1(x: float | None) -> float | None:
    return None if x is None else r0(x * 10) / 10


def _need(d: dict, key: str) -> dict:
    if not isinstance(d.get(key), dict):
        raise ValueError(f"Open-Meteo response has no '{key}' block")
    return d[key]


def fetched_of(src: dict) -> datetime:
    """When the forecast data on this page was really fetched: the oldest
    reused_from among results open_data.py carried over, else the file's time."""
    old = [r["reused_from"] for r in src["results"].values() if r.get("reused_from")]
    return min(datetime.fromisoformat(x) for x in old) if old else datetime.fromisoformat(src["fetched_at"])


def place_block(om: dict, today: str, when: str, days: int = 8,
                now: datetime | None = None) -> dict:
    """Build {"baked", "now", "hourly"} for one place. `today` is YYYY-MM-DD (London).
    `now` is this run's clock; passing it enables the "current" reading's age check."""
    D, H, C = _need(om, "daily"), _need(om, "hourly"), _need(om, "current")
    check_om(om, today, now)
    if not D.get("time") or D["time"][0] != today or len(D["time"]) < days:
        raise ValueError(f"daily forecast does not start today ({today}) with {days} days")
    baked = [[D["time"][i], r0(D["temperature_2m_max"][i]), r0(D["temperature_2m_min"][i]),
              phrase(D["weather_code"][i]), r0(D["precipitation_probability_max"][i] or 0),
              r0(D["wind_speed_10m_max"][i]), r0(D["wind_gusts_10m_max"][i]),
              emoji(D["weather_code"][i])] for i in range(days)]

    sunrise, sunset = D["sunrise"][0][11:16], D["sunset"][0][11:16]
    rows = []
    for i, ts in enumerate(H["time"]):
        if ts[:10] != today:
            continue
        t, code = ts[11:16], H["weather_code"][i]
        night = (t[:2] + ":30" < sunrise or t[:2] + ":30" > sunset) and code < 2
        if H["temperature_2m"][i] is None or code is None:
            raise ValueError(f"hour {t} has no temperature or weather code")
        rows.append([t, r0(H["temperature_2m"][i]), r0(H["precipitation_probability"][i]),
                     r0(H["wind_gusts_10m"][i]), r0(H["wind_speed_10m"][i]),
                     compass(H["wind_direction_10m"][i] or 0),
                     "\U0001F319" if night else emoji(code), phrase(code),
                     r1(H["precipitation"][i]), r0(H["apparent_temperature"][i]),
                     r0(H["dew_point_2m"][i]), r0(H["relative_humidity_2m"][i]),
                     r0(H["cloud_cover"][i]), r1(H["uv_index"][i]),
                     r1(H["visibility"][i] / 1000) if H["visibility"][i] is not None else None,
                     None, "om"])
    if len(rows) != 24:
        raise ValueError(f"expected 24 hours for {today}, got {len(rows)}")

    now = {"t": r0(C["temperature_2m"]), "e": emoji(C["weather_code"]),
           "phrase": phrase(C["weather_code"]),
           "wind": f"{compass(C['wind_direction_10m'] or 0)} {r0(C['wind_speed_10m'])} km/h",
           "gust": r0(C["wind_gusts_10m"]), "hum": r0(C["relative_humidity_2m"]), "when": when}
    return {"baked": baked, "now": now, "hourly": {"date": today, "when": when, "rows": rows}}


# Page-editing helpers shared by the area weather/refresh_weather.py scripts
# (East Kent keeps its own set_line/read_line: its page is edited as one string).
def ok(results: dict, name: str):
    r = results.get(name) or {}
    return r.get("data") if r.get("ok") else None


def set_line(lines: list[str], name: str, value) -> None:
    idx = [i for i, l in enumerate(lines) if l.startswith(f"var {name}=")]
    if len(idx) != 1:
        raise ValueError(f"{name}: expected one 'var {name}=' line, found {len(idx)}")
    lines[idx[0]] = f"var {name}={json.dumps(value, ensure_ascii=False, separators=(',', ':'))};"


def read_line(lines: list[str], name: str):
    line = next(l for l in lines if l.startswith(f"var {name}="))
    return json.loads(line[len(f"var {name}="):].rstrip(";"))


def stamp(dt: datetime) -> str:
    return dt.astimezone(ZoneInfo(TZ)).strftime("%-d %b, %H:%M")
