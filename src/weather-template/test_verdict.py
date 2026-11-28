"""Tests for the weather verdict line (decision 3, 26 Nov 2026).  Run: python3 test_verdict.py

Runs verdictParts(), verdictText() and vflood() from parts/app.js under node, and checks that
every board's built page carries the line, its wrap of renderGlance, and (Ammanford) Welsh
for every phrase the rules can produce.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

APP = (HERE / "parts" / "app.js").read_text(encoding="utf-8")
SRC = APP[APP.index("function verdictParts("):APP.index("function renderVerdict(")]
fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def js(expr_list):
    """Evaluate each JS expression after the verdict functions; returns their JSON values."""
    prog = "var window=globalThis;" + SRC + "\nconsole.log(JSON.stringify([" + ",".join(expr_list) + "]))"
    r = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("node failed: " + r.stderr)
    return json.loads(r.stdout)


T = lambda *a: "verdictText(verdictParts(" + ",".join(json.dumps(x) for x in a) + "))"  # noqa: E731
out = js([
    T("Plymouth", 20, "23:00", 24, None),
    T("Plymouth", 19, "23:00", 34, None),
    T("Plymouth", 49, "15:00", 35, None),
    T("Plymouth", 50, "15:00", 44, None),
    T("Plymouth", 99, "07:00", 45, None),
    T("Plymouth", 30, "", 12, None),
    T("Plymouth", 70, "", 60, None),
    T("Totnes", 0, "10:00", 20, {"lvl": "Flood alert", "town": True}),
    T("Watford", 0, "10:00", 20, {"lvl": "Flood warning", "town": False}),
    T("Dundee", None, "", 40, None),
    T("Dundee", 25, "12:00", None, None),
])
check("worked example from the decision", out[0] == "Plymouth today: showers possible (up to 20% around 23:00), light winds.")
check("19% is dry, 34 km/h is light winds", out[1] == "Plymouth today: dry, light winds.")
check("49% showers, 35 km/h breezy", out[2] == "Plymouth today: showers possible (up to 49% around 15:00), breezy, gusts to 35 km/h.")
check("50% rain likely, 44 km/h still breezy", out[3] == "Plymouth today: rain likely around 15:00 (50%), breezy, gusts to 44 km/h.")
check("45 km/h windy", out[4] == "Plymouth today: rain likely around 07:00 (99%), windy, gusts to 45 km/h.")
check("no hour: no 'around'", out[5] == "Plymouth today: showers possible (up to 30%), light winds." and out[6] == "Plymouth today: rain likely (70%), windy, gusts to 60 km/h.")
check("a town's flood notice goes first", out[7] == "Flood alert in force for Totnes. Totnes today: dry, light winds.")
check("an area-wide notice says so", out[8] == "Flood warning in force in this area. Watford today: dry, light winds.")
check("missing rain or gust figure: no stray comma", out[9] == "Dundee today: breezy, gusts to 40 km/h." and out[10] == "Dundee today: showers possible (up to 25% around 12:00).")
words = " ".join(out).lower()
check("no safety, swim or health advice", not re.search(r"\b(safe|swim|health|avoid|should|advice)\b", words))

fl = js([
    "(function(){globalThis.floodActive=function(){return [['Flood alert','x'],['Flood warning','y']]};var v=vflood();delete globalThis.floodActive;return v})()",
    "(function(){globalThis.floodActive=function(){return [{sev:3,lvl:'Flood Alert'},{sev:1}]};var v=vflood();delete globalThis.floodActive;return v})()",
    "(function(){globalThis.FLOODS={items:[{lvl:'Flood alert',area:'Tay'}]};var v=vflood();delete globalThis.FLOODS;return v})()",
    "(function(){globalThis.floodActive=function(){return []};var v=vflood();delete globalThis.floodActive;return v})()",
])
check("England list (West Herts): most severe first", fl[0] == {"lvl": "Flood warning", "town": False})
check("Wales list (NPT, Ammanford): sev 1 is a severe flood warning", fl[1] == {"lvl": "Severe flood warning", "town": False})
check("Scotland list (Tayside): SEPA level", fl[2] == {"lvl": "Flood alert", "town": False})
check("nothing in force: no flood clause", fl[3] is None)

FIX = {"west-herts": "west-herts-2026-11-22T1250", "ammanford": "ammanford-2026-11-22T1728",
       "neath-port-talbot": "neath-port-talbot-2026-11-22T1457", "tayside": "tayside-2026-11-22T1837",
       "east-kent": "east-kent-2026-11-22T1823", "plymouth": "plymouth-2026-11-26T0929"}
for area, fx in FIX.items():
    page, _ = build.build(area, HERE / "fixtures" / f"{fx}.json")
    check(f"{area}: verdict line above the tiles, drawn after every renderGlance",
          page.count('id="verdict"') == 1 and page.index('id="verdict"') < page.index('id="glance"')
          and "renderGlance0.apply(this,arguments);try{renderVerdict()}" in page)
    town_map = "T.fa.indexOf(r[0])>=0&&r[2]<4});if(!a.length)return null" in page
    check(f"{area}: flood clause per town only where the board maps notices to towns",
          town_map == (area in ("east-kent", "plymouth")))

# Welsh: every fixed phrase the rules can give has an Ammanford entry
cyw = json.loads(json.loads((HERE / "fixtures" / "ammanford-2026-11-22T1728.json").read_text(encoding="utf-8"))["CYW"])
cyw.update(build.welsh_extra(json.loads((HERE / "areas" / "ammanford" / "settings.json").read_text(encoding="utf-8")), "ammanford"))
need = ["{P} today:", "dry", "showers possible (up to #% around #:#)", "showers possible (up to #%)",
        "rain likely around #:# (#%)", "rain likely (#%)", "light winds", "breezy, gusts to # km/h",
        "windy, gusts to # km/h"] + [f"{l} in force in this area." for l in ("Flood alert", "Flood warning", "Severe flood warning")]
check("Ammanford: Welsh for every verdict phrase", all(k in cyw for k in need))

print("\nall ok" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
