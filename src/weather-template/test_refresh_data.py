"""Tests for refresh_data.py (rivers, floods, sewage).  Run: python3 test_refresh_data.py

Weather and air come from the area's refresh_weather.py, which has its own tests.

1. Real data: the 13:31 source of 22 Nov gives the same RIVERS readings, FLOODS items and
   SPILLS rows the hourly task published at 13:54 from that source.
2. Each failure keeps the old block (or station) and says why.
3. Flood text is reduced to the area plus the first sentence; overflows are filtered by river.
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import refresh_data as R  # noqa: E402

SRC = json.loads((HERE / "fixtures" / "west-herts-source-2026-11-22T1331-rivers.json").read_text(encoding="utf-8"))
PUB = {k: json.loads(v) for k, v in json.loads(
    (HERE / "fixtures" / "west-herts-published-2026-11-22T1354-blocks.json").read_text(encoding="utf-8")).items()}
CFG = json.loads((HERE / "areas" / "west-herts" / "refresh.json").read_text(encoding="utf-8"))
NOW = 1795354315000
fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


res = SRC["results"]

# 1. real data matches what was published
rv, notes = R.rivers(PUB["RIVERS"], res, CFG["rivers"], NOW)
check("rivers: same readings and times as published", all(a["v"] == b["v"] and a["t"] == b["t"]
                                                       for a, b in zip(rv["st"], PUB["RIVERS"]["st"])))
check("rivers: 96 readings per station", all(len(s["v"]) == 96 for s in rv["st"]))
check("rivers: station names and ranges kept", all({k: v for k, v in a.items() if k not in ("v", "t")} ==
                                                   {k: v for k, v in b.items() if k not in ("v", "t")}
                                                   for a, b in zip(rv["st"], PUB["RIVERS"]["st"])))
fl, _ = R.floods(PUB["FLOODS"], res, CFG["floods"], NOW)
check("floods: same items as published", fl["items"] == PUB["FLOODS"]["items"])
sp, notes = R.spills(PUB["SPILLS"], res, CFG["spills"], PUB["AREAS"])
check("spills: same rows as published", sp["f"] == PUB["SPILLS"]["f"] and sp["asofMs"] == PUB["SPILLS"]["asofMs"])
check("spills: no new-overflow notes for known Ids", notes == [])

# 2. failures keep the old block
bad = copy.deepcopy(res)
bad["river_chess_rickmansworth"]["ok"] = False
rv2, notes = R.rivers(PUB["RIVERS"], bad, CFG["rivers"], NOW)
chess = [s for s in rv2["st"] if s["id"] == "2859TH"][0]
old_chess = [s for s in PUB["RIVERS"]["st"] if s["id"] == "2859TH"][0]
check("rivers: a failed station keeps its old readings", chess["v"] == old_chess["v"] and any("2859TH" in n for n in notes))
bad["flood_warnings"]["ok"] = False
fl2, notes = R.floods(PUB["FLOODS"], bad, CFG["floods"], NOW)
check("floods: failed source keeps old block", fl2 is PUB["FLOODS"] and notes)
bad["storm_overflows"]["ok"] = False
sp2, notes = R.spills(PUB["SPILLS"], bad, CFG["spills"], PUB["AREAS"])
check("spills: failed source keeps old block", sp2 is PUB["SPILLS"] and notes)
only_other = copy.deepcopy(res)
only_other["storm_overflows"]["data"]["features"] = [f for f in res["storm_overflows"]["data"]["features"]
                                                     if "Wealdstone" in (f["attributes"]["ReceivingWaterCourse"] or "")]
sp3, notes = R.spills(PUB["SPILLS"], only_other, CFG["spills"], PUB["AREAS"])
check("spills: nothing left after filtering keeps old block", sp3 is PUB["SPILLS"] and "unusual" in notes[0])

# 3. formatting and filtering
item = {"severity": "Flood alert", "description": "River Colne at Rickmansworth",
        "message": "River levels are rising.  Flooding of low lying land is possible. Avoid the towpath."}
fx = copy.deepcopy(res)
fx["flood_warnings"]["data"]["items"] = [item, {"severity": "Flood warning", "eaAreaName": "Herts and North London"}]
fl3, _ = R.floods(PUB["FLOODS"], fx, CFG["floods"], NOW)
check("floods: area plus first sentence", fl3["items"][0] == ["Flood alert", "River Colne at Rickmansworth - River levels are rising."])
check("floods: falls back to area name when no message", fl3["items"][1] == ["Flood warning", "Herts and North London"])
check("floods: time is when the data was fetched", fl3["asofMs"] == NOW)
check("spills: Wealdstone and Yeading Brook left out", not any("Wealdstone" in r[6] or "Yeading" in r[6] for r in sp["f"]))
new = copy.deepcopy(res)
f0 = copy.deepcopy(new["storm_overflows"]["data"]["features"][-1])
f0["attributes"].update(Id="TWL99999", Status=1, StatusStart=1795350000000, ReceivingWaterCourse="River Chess")
new["storm_overflows"]["data"]["features"].append(f0)
sp4, notes = R.spills(PUB["SPILLS"], new, CFG["spills"], PUB["AREAS"])
row = [r for r in sp4["f"] if r[0] == "TWL99999"][0]
check("spills: discharging row has start and no end", row[1:4] == [1, 1795350000000, None])
check("spills: a new Id is reported", any("TWL99999" in n for n in notes))

# hostile flood text cannot become markup: the page escapes it before showing it
app = (HERE / "areas" / "west-herts" / "code" / "rivers.js").read_text(encoding="utf-8")
check("page escapes flood text in both places", "esc(x[0])" in app and "e(x[0])" in app and "e(x[1])" in app)

# page_script mode (Neath Port Talbot): weather that cannot be built means nothing is written
from datetime import datetime, timezone  # noqa: E402
if (HERE.parent / "neath-port-talbot" / "weather" / "refresh_weather.py").exists():
    npt_page = (HERE / "fixtures" / "neath-port-talbot-2026-11-22T1457.json")
    import build  # noqa: E402
    pg, _ = build.build("neath-port-talbot", npt_page)
    out, lines = R.refresh("neath-port-talbot", pg, {"fetched_at": datetime.now(timezone.utc).isoformat(), "results": {}},
                           datetime.now(timezone.utc))
    check("npt: no weather means nothing written", out is None and any("nothing written" in l for l in lines))
    old = datetime(2026, 11, 22, 3, 0, tzinfo=timezone.utc)
    out, lines = R.refresh("neath-port-talbot", pg, {"fetched_at": old.isoformat(), "results": {}}, datetime.now(timezone.utc))
    check("npt: data over 6 hours old is refused", out is None and "h old" in lines[0])
else:
    print("skip npt page_script tests: neath-port-talbot/weather/refresh_weather.py not beside the template")

# Ammanford: the Welsh dictionary is `var W=` in its own script, and the template's own
# Welsh lines (lang_extra) are taken out again so the data holds only what the area makes
import build  # noqa: E402
amm_pg, _ = build.build("ammanford", HERE / "fixtures" / "ammanford-2026-11-22T1728.json")
amm_names = json.loads((HERE / "areas" / "ammanford" / "settings.json").read_text(encoding="utf-8"))["data_blocks"]
blk = R.page_blocks(amm_pg, amm_names, {"CYW": "W"})
check("amm: every block found, CYW read from var W", set(blk) == set(amm_names) and json.loads(blk["CYW"]))
try:
    R.page_blocks(amm_pg, ["CYW"])
    check("amm: CYW without var_names is refused", False)
except ValueError:
    check("amm: CYW without var_names is refused", True)
try:
    R.page_blocks(amm_pg + "\nvar LOCS={}", ["LOCS"])
    check("two lines for one block are refused", False)
except ValueError as exc:
    check("two lines for one block are refused", "found 2" in str(exc))


class _Stub:  # stands in for ammanford/weather/refresh_weather.py: changes nothing, reports LOCS done
    @staticmethod
    def refresh(page, src, now):
        return page, ["LOCS"], []


_real = R.load_weather_module
R.load_weather_module = lambda path: _Stub
try:
    now = datetime.now(timezone.utc)
    out, lines = R.refresh("ammanford", amm_pg, {"fetched_at": now.isoformat(), "results": {}}, now)
finally:
    R.load_weather_module = _real
extra = build.welsh_extra(json.loads((HERE / "areas" / "ammanford" / "settings.json").read_text(encoding="utf-8")), "ammanford")
check("amm: template-only and shared Welsh lines are not written to the data",
      out is not None and not any(k in json.loads(out["CYW"]) for k in extra))


class _Own:  # the area's own script wrote its own Welsh for a key the shared file also has
    @staticmethod
    def refresh(page, src, now):
        i = page.index("\nvar W=") + 7
        w, end = json.JSONDecoder().raw_decode(page, i)
        w["dry"] = "AREA OWN"
        return page[:i] + json.dumps(w, ensure_ascii=False) + page[end:], ["LOCS"], []


R.load_weather_module = lambda path: _Own
try:
    out, _ = R.refresh("ammanford", amm_pg, {"fetched_at": now.isoformat(), "results": {}}, now)
finally:
    R.load_weather_module = _real
check("amm: Welsh the area's script wrote itself is kept, not stripped",
      out is not None and json.loads(out["CYW"]).get("dry") == "AREA OWN")
check("amm: unchanged blocks are reported as kept", "AIR kept" in lines and "LOCS refreshed" in lines)
if (HERE.parent / "ammanford" / "weather" / "refresh_weather.py").exists():
    out, lines = R.refresh("ammanford", amm_pg, {"fetched_at": now.isoformat(), "results": {}}, now)
    check("amm: no weather means nothing written", out is None and any("nothing written" in l for l in lines))
else:
    print("skip amm page_script test: ammanford/weather/refresh_weather.py not beside the template")

# Tayside: all seven blocks found on the template page, and refreshed by tayside/weather/refresh_page.py
tay_pg, _ = build.build("tayside", HERE / "fixtures" / "tayside-2026-11-22T1837.json")
tay_names = json.loads((HERE / "areas" / "tayside" / "settings.json").read_text(encoding="utf-8"))["data_blocks"]
check("tay: every data block found on the page", set(R.page_blocks(tay_pg, tay_names)) == set(tay_names))
if (HERE.parent / "tayside" / "weather" / "refresh_page.py").exists():
    now = datetime.now(timezone.utc)
    out, lines = R.refresh("tayside", tay_pg, {"fetched_at": now.isoformat(), "results": {}}, now)
    check("tay: no weather means nothing written", out is None and any("nothing written" in l for l in lines))
else:
    print("skip tay page_script test: tayside/weather/refresh_page.py not beside the template")

# East Kent: every data block found on the template page, refreshed by east-kent/weather/refresh_page.py
ek_pg, _ = build.build("east-kent", HERE / "fixtures" / "east-kent-2026-11-22T1823.json")
ek_names = json.loads((HERE / "areas" / "east-kent" / "settings.json").read_text(encoding="utf-8"))["data_blocks"]
check("ek: every data block found on the page", set(R.page_blocks(ek_pg, ek_names)) == set(ek_names))
ek_src = HERE.parent / "east-kent" / "weather" / "fixtures" / "sources-2026-11-22T2123.json"
if ek_src.exists():
    from datetime import datetime as _dt, timezone as _tz
    out, lines = R.refresh("east-kent", ek_pg, json.loads(ek_src.read_text(encoding="utf-8")), _dt(2026, 11, 22, 21, 30, tzinfo=_tz.utc))
    check("ek: refresh writes every block", out is not None and all(f"{n} refreshed" in lines for n in ek_names))
    out, lines = R.refresh("east-kent", "<title>East Kent · Weather</title><script>var BAKED=[];</script>",
                           json.loads(ek_src.read_text(encoding="utf-8")), _dt(2026, 11, 22, 21, 30, tzinfo=_tz.utc))
    check("ek: first run on the old page starts from the seed and says so",
          out is not None and all(f"{n} refreshed" in lines for n in ek_names) and any("started from the seed" in l for l in lines))
    try:
        R.refresh("west-herts", "<p>not a page</p>", {"fetched_at": _dt.now(_tz.utc).isoformat(), "results": {}}, _dt.now(_tz.utc))
        check("an area with no seed still refuses a non-template page", False)
    except ValueError:
        check("an area with no seed still refuses a non-template page", True)
else:
    print("skip ek page_script test: east-kent/weather/ not beside the template")

print("\nall ok" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
