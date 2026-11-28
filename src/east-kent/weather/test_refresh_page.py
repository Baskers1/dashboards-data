"""Tests for refresh_page.py and sms_text.py (East Kent, weather template).

    python3 test_refresh_page.py      # prints ok/FAIL per check, ends with "all ok"

Fixtures: one hour of sources (22 Nov 2026, 21:23, plus Southern Water Rivers and Seas Watch at
22:01; the five other towns are copies of Ramsgate's answer at their own coordinates) and the
page built from the live page of 18:23. On these the overflow rows came out identical, field for
field, to the ones the hourly task copied by hand at 18:23.
"""
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "weather-template"))
import refresh_page as rp  # noqa: E402
import sms_text  # noqa: E402
import build  # noqa: E402

SRC = json.loads((HERE / "fixtures" / "sources-2026-11-22T2123.json").read_text(encoding="utf-8"))
PAGE, _ = build.build("east-kent", HERE.parents[1] / "weather-template" / "fixtures" / "east-kent-2026-11-22T1823.json")
NOW = datetime(2026, 11, 22, 21, 30, tzinfo=timezone.utc)
fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def run(**changes):
    s = copy.deepcopy(SRC)
    for k, v in changes.items():
        if v is None:
            s["results"].pop(k, None)
        else:
            s["results"][k] = v
    return rp.refresh(PAGE, s, NOW)


html, done, notes = run()
check("every block refreshed, no notes", done == ["LOCS", "AIR", "SPILLS", "FLOODS", "RELEASES", "TIDES", "TIDEX"] and not notes)
locs = rp.read_block(html, "LOCS")
check("all six towns rebuilt with the shared builder", all(locs[k]["hourly"]["date"] == "2026-11-22" and len(locs[k]["hourly"]["rows"]) == 24
                                                         and locs[k]["now"]["when"] for k in locs))
check("fixed town fields kept", all(locs[k]["name"] and locs[k]["area"] == "Kent" for k in locs))
old_sp, new_sp = rp.read_block(PAGE, "SPILLS")["f"], rp.read_block(html, "SPILLS")["f"]
check("overflow rows match the hand-copied ones", old_sp == new_sp)
rel = rp.read_block(html, "RELEASES")
check("release history: same 11 beaches, events from the last 30 days, newest first",
      [s[0] for s in rel["sites"]] == [s[0] for s in rp.read_block(PAGE, "RELEASES")["sites"]]
      and rel["ev"] and all(e[3] >= rp.read_block(html, "RELEASES")["asofMs"] - 30 * 86400000 for e in rel["ev"])
      and [e[3] for e in rel["ev"]] == sorted((e[3] for e in rel["ev"]), reverse=True))
check("tides: yesterday to +13 days", sorted(rp.read_block(html, "TIDES")) [0] == "2026-11-21" and sorted(rp.read_block(html, "TIDES"))[-1] == "2026-12-05")

_, d, n = run(ramsgate={"ok": False, "error": "timeout"})
check("Ramsgate weather failed: nothing written", d == [] and any("NOT refreshed" in x for x in n))
h, d, n = run(other_towns={"ok": False, "error": "x"})
check("other towns failed: Ramsgate still refreshed, the rest kept", "LOCS" in d and rp.read_block(h, "LOCS")["margate"] == rp.read_block(PAGE, "LOCS")["margate"] and n)
ot = copy.deepcopy(SRC["results"]["other_towns"]); ot["data"] = list(reversed(ot["data"]))
h, d, n = run(other_towns=ot)
check("other towns out of order: refused town by town", any("not 51." in x for x in n) and rp.read_block(h, "LOCS")["margate"] == rp.read_block(PAGE, "LOCS")["margate"])
so = copy.deepcopy(SRC["results"]["storm_overflows"]); so["data"]["features"] = so["data"]["features"][:10]
_, d, n = run(storm_overflows=so)
check("too few overflow monitors: SPILLS kept", "SPILLS" not in d and n)
so = copy.deepcopy(SRC["results"]["storm_overflows"]); so["data"]["features"][0]["attributes"]["Latitude"] = 52.0
_, d, n = run(storm_overflows=so)
check("an overflow outside the box: SPILLS kept", "SPILLS" not in d)
_, d, n = run(flood_warnings={"ok": False, "error": "500"})
check("flood warnings failed: FLOOD kept", "FLOODS" not in d and n)
g = copy.deepcopy(SRC["results"]["gauge_E3810"]); g["data"]["items"][0]["value"] = 99
h, d, n = run(gauge_E3810=g)
check("a gauge out of range keeps its last reading", "FLOODS" in d and rp.read_block(h, "FLOODS")["g"]["E3810"] == rp.read_block(PAGE, "FLOODS")["g"]["E3810"])
_, d, n = run(bathing_release_history={"ok": False, "error": "x"})
check("release history failed: RELEASES kept", "RELEASES" not in d and n)

data = {"LOCS": json.dumps(locs), "TIDES": json.dumps(rp.read_block(html, "TIDES")), "SPILLS": json.dumps(rp.read_block(html, "SPILLS"))}
t = sms_text.message(data, True, datetime(2026, 11, 22, 17, 5, tzinfo=timezone.utc))
lines = t.split("\n")
check("text: four lines, ASCII, at most 155 characters", len(lines) == 4 and t.isascii() and len(t) <= 155)
check("text: line 1 as the rule says", lines[0].startswith("Hullo! Ramsgate: ") and " wind " in lines[0] and lines[0].endswith("%."))
check("text: next high tide after 17:05 today, else tomorrow", lines[1] == "Next high tide 00:59 (5.3m)." or lines[1].startswith("Next high tide "))
check("text: no overflow discharging", lines[2] == "Sewage overflow: none." and lines[3] == sms_text.LINK)
check("text: overflows not refreshed", sms_text.message(data, False, NOW).split("\n")[2] == "Sewage overflow: data unavailable.")
sp = json.loads(data["SPILLS"]); sp["f"][0][1] = 1; sp["f"][0][4], sp["f"][0][5] = 51.33, 1.42
check("text: one discharging in the Ramsgate box", sms_text.message({**data, "SPILLS": json.dumps(sp)}, True, NOW).split("\n")[2] == "Sewage overflow: 1 discharging, see link.")
long = json.loads(data["LOCS"]); long["ramsgate"]["now"]["phrase"] = "Thunderstorm with hail and a lot more words"
check("text: a long line 1 is shortened to fit", len(sms_text.message({**data, "LOCS": json.dumps(long)}, True, NOW)) <= 155)

print("\nall ok" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
