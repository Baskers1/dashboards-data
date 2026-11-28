"""Tests for the age badge (plan recommendation 5, 28 Nov 2026).  Run: python3 test_age.py

Runs ageMins() and ageText() from parts/app.js under node, and checks that every board's built
page carries the badge below the verdict line, redrawn after every renderGlance and each minute,
and that both Welsh boards have Welsh for every phrase it can show.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

APP = (HERE / "parts" / "app.js").read_text(encoding="utf-8")
SRC = APP[APP.index("function ageMins("):APP.index("function renderAge(")]
fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def js(exprs):
    prog = 'var mons=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];' + SRC + \
        "\nconsole.log(JSON.stringify([" + ",".join(exprs) + "]))"
    r = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("node failed: " + r.stderr)
    return json.loads(r.stdout)


# now is UK wall-clock time, as nowLondon() gives it: new Date(y, m0, d, h, min)
M = lambda w, now: "ageMins(" + json.dumps(w) + ",new Date(" + now + "))"  # noqa: E731
T = lambda w, now: "(function(a){return a==null?null:ageText(a)})(" + M(w, now) + ")"  # noqa: E731
out = js([
    T("28 Nov, 12:00", "2026,10,28,12,1"),
    T("28 Nov, 12:00", "2026,10,28,12,45"),
    T("28 Nov, 12:00", "2026,10,28,13,59"),
    T("28 Nov, 12:00", "2026,10,28,14,59"),
    T("28 Nov, 12:00", "2026,10,28,15,0"),
    T("28 Nov, 08:23", "2026,10,29,7,0"),
    T("26 Nov, 12:00", "2026,10,28,12,0"),
    M("31 Dec, 23:00", "2027,0,1,1,0"),
    M("28 Nov, 12:30", "2026,10,28,12,0"),
    M("28 Nov, 14:00", "2026,10,28,12,0"),
    M("not yet fetched", "2026,10,28,12,0"),
    M("", "2026,10,28,12,0"),
    M("28 Foo, 12:00", "2026,10,28,12,0"),
    M(None, "2026,10,28,12,0"),
    M("1 Nov, 09:05", "2026,10,1,9,35"),
])
check("under 2 min: just now", out[0] == "Updated just now")
check("45 min", out[1] == "Updated 45 min ago")
check("1 h 59 min rounds down to 1 hour", out[2] == "Updated 1 hour ago")
check("2 h 59 min is 2 hours, not yet old", out[3] == "Updated 2 hours ago")
check("3 hours: old", out[4] == "Old data · Updated 3 hours ago")
check("overnight (22 h 37 min): old, 22 hours", out[5] == "Old data · Updated 22 hours ago")
check("48 hours: days", out[6] == "Old data · Updated 2 days ago")
check("New Year: December stamp read as last year", out[7] == 120)
check("up to 90 min in the future counts as now", out[8] == 0)
check("further in the future: no badge", out[9] is None)
check("unparsable or missing stamp: no badge", out[10:14] == [None, None, None, None])
check("single-digit day", out[14] == 30)

FIX = {"west-herts": "west-herts-2026-11-22T1250", "ammanford": "ammanford-2026-11-22T1728",
       "neath-port-talbot": "neath-port-talbot-2026-11-22T1457", "tayside": "tayside-2026-11-22T1837",
       "east-kent": "east-kent-2026-11-22T1823", "plymouth": "plymouth-2026-11-26T0929"}
for area, fx in FIX.items():
    page, _ = build.build(area, HERE / "fixtures" / f"{fx}.json")
    check(f"{area}: badge once, after the verdict and before the tiles, redrawn after renderGlance and every minute",
          page.count('id="age"') == 1 and page.index('id="verdict"') < page.index('id="age"') < page.index('id="glance"')
          and "try{renderVerdict()}catch(e){}try{renderAge()}catch(e){}" in page
          and "setInterval(function(){try{renderAge()}catch(e){}},60000)" in page)

need = ["Updated just now", "Updated # min ago", "Updated # hours ago", "Updated # days ago",
        "Old data · Updated # hours ago", "Old data · Updated # days ago"]
for area, fx in (("ammanford", "ammanford-2026-11-22T1728"), ("neath-port-talbot", "neath-port-talbot-2026-11-22T1457")):
    cyw = json.loads(json.loads((HERE / "fixtures" / f"{fx}.json").read_text(encoding="utf-8")).get("CYW", "{}"))
    cyw.update(build.welsh_extra(json.loads((HERE / "areas" / area / "settings.json").read_text(encoding="utf-8")), area))
    check(f"{area}: Welsh for every badge phrase", all(k in cyw for k in need))

print("\nall ok" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
