"""Tests for refresh_page.py (Tayside rivers, floods, tides, bathing, overflows).

    python3 test_refresh_page.py      # prints ok/FAIL per check, ends with "all ok"

The fixtures are real: one hour of sources (22 Nov 2026, 20:43) and the blocks the hourly
task wrote by hand at 18:37 that day. On those, the code reproduced the hand-written tides,
bathing and overflows exactly, and rivers and floods to the newer readings.
"""
import copy
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import refresh_page as rp  # noqa: E402

SRC = json.loads((HERE / "fixtures" / "sources-2026-11-22T2043.json").read_text(encoding="utf-8"))
OLD = json.loads((HERE / "fixtures" / "page-blocks-2026-11-22T1837.json").read_text(encoding="utf-8"))
NOW_MS = 1795380000000
TODAY = date(2026, 11, 22)
fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def results(**changes):
    r = copy.deepcopy(SRC["results"])
    for k, v in changes.items():
        if v is None:
            r.pop(k, None)
        else:
            r[k] = v
    return r


def with_text(name, fn):
    r = copy.deepcopy(SRC["results"][name])
    r["data"]["text"] = fn(r["data"]["text"])
    return r


# rivers
notes = []
rv = rp.build_rivers(OLD["RIVERS"], results(), NOW_MS, notes)
b = rv["st"][0]
check("rivers: Ballathie read", (b["t"], b["lv"], b["trend"], b["state"], b["top"], b["max"], b["maxd"], b["min"]) ==
      ("8:30 pm on 22 November 2026", 0.871, "Level falling", "Normal", 4.416, 7.099, "17 January 1993", -0.023))
check("rivers: fixed fields kept", all(rv["st"][i][k] == OLD["RIVERS"]["st"][i][k] for i in (0, 1)
                                       for k in ("id", "n", "r", "opened", "area", "url")) and "lat" not in b)
check("rivers: asofMs set", rv["asofMs"] == NOW_MS and not notes)
notes = []
rv = rp.build_rivers(OLD["RIVERS"], results(river_tay_ballathie={"ok": False, "error": "timeout"}), NOW_MS, notes)
check("rivers: a failed station is left as it was", rv["st"][0] == OLD["RIVERS"]["st"][0] and
      rv["st"][1]["t"].startswith("8:30") and any("timeout" in n for n in notes))
notes = []
r = results(river_tay_ballathie=with_text("river_tay_ballathie", lambda t: t.replace("Latest at", "Most recent")),
            river_dighty_balmossie={"ok": False, "error": "x"})
check("rivers: nothing readable means RIVERS untouched", rp.build_rivers(OLD["RIVERS"], r, NOW_MS, notes) is None
      and any("Latest at" in n for n in notes))

# floods
notes = []
fl = rp.build_floods(OLD["FLOODS"], results(), NOW_MS, notes)
check("floods: all clear read", fl["sepa"] == "22 Nov, 20:43" and fl["items"] == [] and fl["unparsed"] is False
      and fl["head"] == OLD["FLOODS"]["head"] and not notes)
check("floods: forecast matches the hand-written one", fl["fc"] == OLD["FLOODS"]["fc"])
notes = []
r = results(flood_warnings=with_text("flood_warnings", lambda t: t.replace(
    "There are no flood alerts or warnings currently in force in Scotland",
    "There are 3 flood alerts and 1 flood warning currently in force in Scotland")))
fl = rp.build_floods(OLD["FLOODS"], r, NOW_MS, notes)
check("floods: warnings in force are flagged unreadable, never guessed",
      fl["unparsed"] is True and fl["items"] == [] and "3 flood alerts" in fl["head"] and notes)
notes = []
fl = rp.build_floods(OLD["FLOODS"], results(flood_forecast={"ok": False, "error": "503"}), NOW_MS, notes)
check("floods: failed forecast keeps the old forecast", fl["fc"] == OLD["FLOODS"]["fc"] and fl["sepa"] == "22 Nov, 20:43")
notes = []
check("floods: failed live page leaves FLOODS", rp.build_floods(OLD["FLOODS"], results(flood_warnings=None), NOW_MS, notes)
      is None and notes)

# tides
notes = []
td = rp.build_tides(OLD["TIDES"], results(), TODAY, notes)
check("tides: same as the hand-written block", td == OLD["TIDES"] and not notes)
check("tides: a three-tide day", td["dundee"]["2026-11-21"][:3] == [["L", "05:37", 1.61], ["H", "12:01", 4.91], ["L", "17:57", 1.85]])
r = results(**{"tide_dundee_2026-11-22": with_text("tide_dundee_2026-11-22", lambda t: t.replace("Tide Times UTC:", "Tide Times BST:"))})
check("tides: the BST heading reads too", rp.build_tides(OLD["TIDES"], r, TODAY, [])["dundee"]["2026-11-22"] == OLD["TIDES"]["dundee"]["2026-11-22"])
notes = []
r = results(**{"tide_arbroath_2026-11-28": {"ok": False, "error": "404"}})
td = rp.build_tides(OLD["TIDES"], r, TODAY, notes)
check("tides: an unpublished day keeps the old day", td["arbroath"]["2026-11-28"] == OLD["TIDES"]["arbroath"]["2026-11-28"] and notes)
td = rp.build_tides(OLD["TIDES"], results(), date(2026, 11, 24), [])
check("tides: days before yesterday are dropped", min(td["dundee"]) == "2026-11-23")
r = results(**{"tide_dundee_2026-11-22": with_text("tide_dundee_2026-11-22", lambda t: t.replace("Low 06:29 1.40m", "Low 06:29 n/a"))})
notes = []
td = rp.build_tides(OLD["TIDES"], r, TODAY, notes)
check("tides: a half-read table is refused", td["dundee"]["2026-11-22"] == OLD["TIDES"]["dundee"]["2026-11-22"] and notes)

# bathing
notes = []
check("bathing: same as the hand-written block", rp.build_bathing(OLD["BATHING"], results(), notes) == OLD["BATHING"] and not notes)
notes = []
bt = rp.build_bathing(OLD["BATHING"], results(bathing_carnoustie={"ok": False, "error": "x"}), notes)
check("bathing: a failed beach is left as it was", bt["cn"] == OLD["BATHING"]["cn"] and notes)
check("bathing: 'See above' year skipped", 2020 not in [y for y, _ in bt["bf"]["h"]])

# overflows
notes = []
check("overflows: same as the hand-written block", rp.build_spills(OLD["SPILLS"], results(), NOW_MS, notes)["f"] == OLD["SPILLS"]["f"] and not notes)
so = copy.deepcopy(SRC["results"]["storm_overflows"])
so["data"]["features"][0]["attributes"]["ASSET_NAME"] = "NEW TEST CSO"
notes = []
sp = rp.build_spills(OLD["SPILLS"], results(storm_overflows=so), NOW_MS, notes)
check("overflows: a new monitor is named in Title Case and reported", sp["f"][0][12] == "New Test Cso" and any("NEW TEST CSO" in n for n in notes))
so = copy.deepcopy(SRC["results"]["storm_overflows"]); so["data"]["features"] = []
notes = []
check("overflows: an empty layer leaves SPILLS", rp.build_spills(OLD["SPILLS"], results(storm_overflows=so), NOW_MS, notes) is None and notes)
so = copy.deepcopy(SRC["results"]["storm_overflows"]); so["data"]["features"][0]["attributes"]["OVERFLOW_STATUS_DESCRIPTION"] = "ZZ - odd"
notes = []
check("overflows: an unknown status leaves SPILLS", rp.build_spills(OLD["SPILLS"], results(storm_overflows=so), NOW_MS, notes) is None and notes)

print("\nall ok" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
