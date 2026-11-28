"""Tests for refresh_page.py (Plymouth & Ivybridge, weather template).

    python3 test_refresh_page.py      # prints ok/FAIL per check, ends with "all ok"

Fixtures: one hour of sources (26 Nov 2026, 09:29: the Mac's plymouth-ivybridge.json as pushed to
dashboards-data) and the page built from the seed weather-template/fixtures/plymouth-2026-11-26T0929.json,
which make_template_area.py made from that same hour.
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
import build  # noqa: E402

SRC = json.loads((HERE / "fixtures" / "sources-2026-11-26T0929.json").read_text(encoding="utf-8"))
PAGE, FILES = build.build("plymouth", HERE.parents[1] / "weather-template" / "fixtures" / "plymouth-2026-11-26T0929.json")
NOW = datetime(2026, 11, 26, 9, 38, tzinfo=timezone.utc)
TOWNS = ["plymouth", "ivybridge", "plympton", "plymstock", "saltash", "tavistock", "totnes"]
fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def run(now=NOW, **changes):
    s = copy.deepcopy(SRC)
    for k, v in changes.items():
        if v is None:
            s["results"].pop(k, None)
        else:
            s["results"][k] = v
    return rp.refresh(PAGE, s, now)


def towns_with(tid, fn):
    t = copy.deepcopy(SRC["results"]["towns"])
    fn(t["data"][TOWNS.index(tid)])
    return t


html, done, notes = run()
check("every block refreshed, no notes", done == ["LOCS", "AIR", "SPILLS", "FLOODS", "TIDES", "TIDEX"] and not notes)
locs = rp.read_block(html, "LOCS")
check("all seven towns, in order", list(locs) == TOWNS)
check("every town rebuilt with the shared builder, each with its own 'now'",
      all(locs[k]["hourly"]["date"] == "2026-11-26" and len(locs[k]["hourly"]["rows"]) == 24
          and len(locs[k]["baked"]) == 8 and locs[k]["now"]["when"] == "26 Nov, 09:29" for k in locs))
check("fixed town fields kept: Saltash in Cornwall, the rest in Devon",
      all(locs[k]["name"] and locs[k]["area"] == ("Cornwall" if k == "saltash" else "Devon") for k in locs))

# the same hour through the old script: the template page must show the same weather
old, _ = rp.rw.build(copy.deepcopy(SRC), NOW.astimezone(rp.LON), {"FLOOD": None, "SPILLS": None})
check("Plymouth's 8 days match the old page's BAKED (dates, words, and figures within 1)",
      [r[0] for r in locs["plymouth"]["baked"]] == [r[0] for r in old["BAKED"]]
      and all(abs(a[i] - b[i]) <= 1 for a, b in zip(locs["plymouth"]["baked"], old["BAKED"]) for i in (1, 2, 4, 5, 6)))
check("Plymouth's 'now' matches the old page's BAKED_NOW",
      {k: locs["plymouth"]["now"][k] for k in ("t", "gust", "hum", "when")} == {k: old["BAKED_NOW"][k] for k in ("t", "gust", "hum", "when")})
check("every other town's days match the old page's OM block (within 1)",
      all([r[0] for r in locs[t]["baked"]] == [r[0] for r in old["OM"]["t"][t]["d"]]
          and all(abs(a[1] - b[2]) <= 1 and abs(a[2] - b[3]) <= 1 for a, b in zip(locs[t]["baked"], old["OM"]["t"][t]["d"]))
          for t in TOWNS[1:]))
check("floods, overflows, air and tides are the old script's blocks",
      rp.read_block(html, "AIR") == old["AIR"] and rp.read_block(html, "TIDES") == old["TIDES"]
      and rp.read_block(html, "TIDEX") == old["TIDEX"] and rp.read_block(html, "SPILLS")["f"] == old["SPILLS"]["f"]
      and rp.read_block(html, "FLOODS")["items"] == old["FLOOD"]["items"])
check("flood and overflow blocks stamped with this run's clock",
      rp.read_block(html, "FLOODS")["asofMs"] == rp.read_block(html, "SPILLS")["asofMs"] == int(NOW.timestamp() * 1000))
check("Totnes keeps its own tide table", list(rp.read_block(html, "TIDEX")) == ["totnes"] and "2026-11-26" in rp.read_block(html, "TIDEX")["totnes"])

_, d, n = run(towns={"ok": False, "error": "timeout"})
check("towns source failed: nothing written", d == [] and any("NOT refreshed" in x for x in n))
_, d, n = run(towns=towns_with("totnes", lambda x: x.update(latitude=51.5)))
check("a town at the wrong coordinates: nothing written (the old script held all towns too)", d == [] and any("totnes" in x for x in n))
_, d, n = run(towns=towns_with("tavistock", lambda x: x["hourly"]["weather_code"].__setitem__(3, 999)))
check("an impossible weather code anywhere: nothing written", d == [] and any("999" in x for x in n))
# a missing hour passes the whole-answer checks but not the per-town builder
_, d, n = run(towns=towns_with("plymouth", lambda x: x["hourly"]["temperature_2m"].__setitem__(3, None)))
check("Plymouth's own forecast unusable: nothing written", d == [] and any("Plymouth" in x for x in n))
h, d, n = run(towns=towns_with("tavistock", lambda x: x["hourly"]["temperature_2m"].__setitem__(3, None)))
check("one other town unusable: the rest refreshed, Tavistock kept",
      "LOCS" in d and rp.read_block(h, "LOCS")["tavistock"] == rp.read_block(PAGE, "LOCS")["tavistock"]
      and rp.read_block(h, "LOCS")["ivybridge"]["now"]["when"] == "26 Nov, 09:29" and any("Tavistock" in x for x in n))
_, d, n = run(storm_overflows={"ok": False, "error": "x"})
check("overflows failed: SPILLS kept", "SPILLS" not in d and any("storm_overflows" in x for x in n))
_, d, n = run(flood_warnings={"ok": False, "error": "500"})
check("flood warnings failed: FLOODS kept", "FLOODS" not in d and n)
g = copy.deepcopy(SRC["results"]["gauge_46130"]); g["data"]["items"][0]["value"] = 99
h, d, n = run(gauge_46130=g)
check("a gauge out of range keeps its last reading",
      "FLOODS" in d and rp.read_block(h, "FLOODS")["g"]["46130"] == rp.read_block(PAGE, "FLOODS")["g"]["46130"])
_, d, n = run(air_406={"ok": False, "error": "x"})
check("a Defra series failed: AIR kept", "AIR" not in d and any(x.startswith("air:") for x in n))
_, d, n = run(**{k: None for k in SRC["results"] if k.startswith("tide_totnes_")})
check("Totnes tides missing: TIDEX kept, Devonport still refreshed", "TIDEX" not in d and "TIDES" in d)

# the page itself (built from the seed)
MARKERS = ("{{PART:", "{{BLOCK:", "{{CODE:", "{{TITLE}}", "{{H1}}", "{{JUMP}}", "{{SECTIONS}}", "{{ABOUT}}", "{{EXTRA}}")
check("page: builds with no marker left", not any(m in PAGE for m in MARKERS))
check("page: title", "<title>Plymouth &amp; Ivybridge · Weather</title>" in PAGE and "<h1>Plymouth &amp; Ivybridge · Weather</h1>" in PAGE)
check("page: its own sections", all(f'aria-labelledby="{a}"' in PAGE for a in ("w", "fl", "aq", "t", "bw", "sw", "k"))
      and "Plymouth Citybus" in PAGE and "Devonport" in PAGE)
check("page: four photo files for six photos (towns share them, as before)", len(FILES) == 4 and PAGE.count('src:"heroes/') == 6)
check("page: under 300 KB (was 683 KB)", len(PAGE.encode("utf-8")) < 300_000)
check("page: town remembered, chart code hooked, live forecast asked", "dash-town" in PAGE and "renderAll();liveTown(k)}" in PAGE)
check("page: Dartmoor and Plymouth Sound scenes, not Ramsgate", 'LAND=(o.inland?"dartmoor":"plymouth")' in PAGE and 'LAND="ramsgate"' not in PAGE)
check("page: no East Kent wording left", not any(w in PAGE for w in ("Ramsgate", "Thanet", "Southern Water", "East Kent")))

print("\nall ok" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
