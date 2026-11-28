"""The live forecast in the browser (parts/live.js omBlock) must match the hourly snapshot
(scrapekit/scrapers/om_rows.py place_block) exactly. Runs both on the same saved
Open-Meteo answers, plus edge cases, using node.

    python3 test_live.py      # ends with "all ok"
"""
import copy
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scrapekit" / "scrapers"))
import om_rows  # noqa: E402

FIX = json.loads((HERE / "fixtures" / "om-tayside-2026-11-22T2043.json").read_text(encoding="utf-8"))
NOW = datetime.fromisoformat(FIX["fetched_at"])
TODAY, WHEN = "2026-11-22", "22 Nov, 20:43"
JS = (HERE / "parts" / "live.js").read_text(encoding="utf-8")
fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def js_block(answer, offs=0, now_ms=None):
    prog = JS + "\nvar a=JSON.parse(require('fs').readFileSync(0,'utf8'));try{process.stdout.write(JSON.stringify({ok:omBlock(a.j,a.t,a.w,a.o,a.n)}))}catch(e){process.stdout.write(JSON.stringify({err:String(e.message)}))}"
    out = subprocess.run(["node", "-e", prog], input=json.dumps({"j": answer, "t": TODAY, "w": WHEN, "o": offs, "n": now_ms}),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def py_block(answer):
    try:
        return {"ok": json.loads(json.dumps(om_rows.place_block(answer, TODAY, WHEN, now=NOW)))}
    except ValueError as exc:
        return {"err": str(exc)}


now_ms = int(NOW.timestamp() * 1000)
for i, ans in enumerate(FIX["answers"]):
    p, j = py_block(ans), js_block(ans, 0, now_ms)
    check(f"place {i}: browser and snapshot builders agree exactly", "ok" in p and p == j)

a = copy.deepcopy(FIX["answers"][0])
a["hourly"]["temperature_2m"][3] = -2.5
a["daily"]["temperature_2m_min"][1] = -0.5
a["hourly"]["precipitation"][5] = 0.25
p, j = py_block(a), js_block(a, 0, now_ms)
check("halves round the same way (negative, zero, one decimal)", "ok" in p and p == j)

for label, change in [
    ("temperature in Fahrenheit", lambda x: x["hourly_units"].__setitem__("temperature_2m", "°F")),
    ("wrong time zone", lambda x: x.__setitem__("timezone", "GMT")),
    ("a reading out of range", lambda x: x["hourly"]["wind_gusts_10m"].__setitem__(2, 400)),
    ("forecast not starting today", lambda x: x["daily"]["time"].__setitem__(0, "2026-11-21")),
    ("an hour missing", lambda x: [x["hourly"][k].pop(0) for k in list(x["hourly"])]),
    ("an unknown weather code", lambda x: x["daily"]["weather_code"].__setitem__(0, 42)),
]:
    b = copy.deepcopy(FIX["answers"][0])
    change(b)
    check(f"refused by both: {label}", "err" in py_block(b) and "err" in js_block(b, 0, now_ms))
check("refused by the browser: current reading 3 hours old", "err" in js_block(FIX["answers"][0], 0, now_ms + 3 * 3600 * 1000))
check("refused by the browser: summer offset on a winter day", "err" in js_block(FIX["answers"][0], 3600, now_ms))

print("\nall ok" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
