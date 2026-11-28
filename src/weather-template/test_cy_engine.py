"""Tests for the shared Welsh engine parts/cy.js, run under node (27 Nov 2026).

    python3 test_cy_engine.py

Fills the engine with Neath Port Talbot's dictionary (static CYW plus parts/cy-shared.json and
its lang_extra, exactly as build.py merges them) and place list, gives it a small RIVERS, SPILLS,
AIR and FLOODS, stubs the browser, and checks what window.__cyTr makes of English sentences.
Skips, saying so, when node is not installed.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

fails = []


def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        fails.append(name)


node = shutil.which("node")
if not node:
    print("skip: node is not installed, so parts/cy.js is not tested here")
    sys.exit(0)

area = HERE / "areas" / "neath-port-talbot"
settings = json.loads((area / "settings.json").read_text(encoding="utf-8"))
w = json.loads((area / "static" / "CYW.js").read_text(encoding="utf-8"))
w.update(build.welsh_extra(settings, "neath-port-talbot"))
engine = (HERE / "parts" / "cy.js").read_text(encoding="utf-8")
engine = engine.replace("{{BLOCK:CYW}}", json.dumps(w, ensure_ascii=False)).replace(
    "{{BLOCK:CYPL}}", (area / "static" / "CYPL.js").read_text(encoding="utf-8"))

DATA = {
    "RIVERS": {"st": [{"r": "River Neath", "n": "Glynneath"}, {"r": "River Afan", "n": "Marcroft Weir"},
                      {"r": "Ffrwdwyllt", "n": "Taibach"}, {"r": "River Dulais", "n": "Cilfrew"}]},
    "SPILLS": {"f": [["DCWW1", 0, None, None, 51.6, -3.8, "River Neath", "Bonymaen Road No. 2"]]},
    "AIR": {"st": [{"n": "Port Talbot Margam"}]},
    "FLOODS": {"items": [{"area": "River Neath at Neath"}, {"area": "Afan Estuary"}]},
}
STUB = """
var NodeFilter={SHOW_TEXT:4};
global.window=global;
global.localStorage={getItem:function(){return null},setItem:function(){}};
global.MutationObserver=function(){this.observe=function(){};this.disconnect=function(){}};
global.document={title:"Neath Port Talbot · Weather",documentElement:{},body:{},
 querySelectorAll:function(){return []},createTreeWalker:function(){return{nextNode:function(){return null}}}};
"""
CASES = [
    # (what it shows, English, expected Welsh or None for "left in English")
    ("a place is mutated after 'yn' (nasal)", "Walking weather today in Glynneath:", "Tywydd cerdded heddiw yng Nglyn-nedd:"),
    ("a place is mutated after 'o' (soft)", "That station is about 9 km south of Port Talbot, so treat this as a regional picture rather than Port Talbot itself.",
     "Mae’r orsaf tua 9 km i’r de o Bort Talbot, felly darlun rhanbarthol yw hwn, nid Port Talbot ei hun."),
    ("a gauge name is lifted out whole and kept", "River Afan at Marcroft Weir: 0.50 metres, in the middle of its usual range (0.206 to 1.196 metres), rising",
     "River Afan at Marcroft Weir: 0.50 metr, yng nghanol ei hystod arferol (0.206 i 1.196 metr), yn codi"),
    ("a list of names gets Welsh 'a'", "2 gauges are rising: River Afan at Marcroft Weir and Ffrwdwyllt at Taibach.",
     "Mae 2 medrydd yn codi: River Afan at Marcroft Weir a Ffrwdwyllt at Taibach."),
    ("a list joined with commas keeps them", "2 gauges are rising: Ffrwdwyllt at Taibach, River Afan at Marcroft Weir.",
     "Mae 2 medrydd yn codi: Ffrwdwyllt at Taibach, River Afan at Marcroft Weir."),
    ("a name holding a full stop is not split", "Bonymaen Road No. 2", "Bonymaen Road No. 2"),
    ("an air station name with a place inside it stays whole", "Index 1 to 10 at Port Talbot Margam.", "Mynegai 1 i 10 yn Port Talbot Margam."),
    ("the compass letters do not eat the name marker", "Port Talbot Margam, near the steelworks, is the only Defra station in the borough, so it stands in for every town on this page.",
     "Port Talbot Margam, ger y gwaith dur, yw’r unig orsaf Defra yn y fwrdeistref, felly mae’n cynrychioli pob tref ar y dudalen hon."),
    ("pollutant names in capitals are found ('; ' parts)", "Air quality index 2 out of 10, Low, at Port Talbot Margam. nitrogen dioxide: index 1; ozone: no reading; fine particles (PM2.5): index 2; particles (PM10): index 2",
     "Mynegai ansawdd aer 2 allan o 10, Isel, yn Port Talbot Margam. nitrogen deuocsid: mynegai 1; osôn: dim darlleniad; gronynnau mân (PM2.5): mynegai 2; gronynnau (PM10): mynegai 2"),
    ("a weather word becomes Welsh in its slot", "It's partly cloudy in Neath at 4°C, but it feels more like 1°C.",
     "Ar hyn o bryd yng Nghastell-nedd: rhannol gymylog, 4°C, ond mae’n teimlo’n debycach i 1°C."),
    ("wind direction and number order are kept", "The wind is from the east-north-east at 9 km/h, with gusts reaching 35 km/h around 23:00, so it will feel breezy.",
     "Mae’r gwynt yn chwythu o’r dwyrain-gogledd-ddwyrain ar 9 km/a, gyda hyrddiau hyd at 35 km/a tua 23:00, felly bydd yn awelog."),
    ("a split before a number translates every sentence", "All 7 gauges with a published usual range are within it. 1 gauge is rising: River Dulais at Cilfrew. 2 other readings are more than 3 hours old.",
     "Mae pob un o’r 7 medrydd sydd ag ystod arferol gyhoeddedig o fewn yr ystod. Mae 1 medrydd yn codi: River Dulais at Cilfrew. Mae 2 darlleniad arall yn hŷn na 3 awr."),
    ("flood areas are names, lists joined with '; '", "There are 2 flood notices in force in Neath Port Talbot, the most serious being a flood alert (flooding is possible, so be prepared): River Neath at Neath; Afan Estuary.",
     "Mae 2 neges llifogydd mewn grym yng Nghastell-nedd Port Talbot, a’r fwyaf difrifol yw hysbysiad llifogydd (mae llifogydd yn bosibl, felly byddwch yn barod): River Neath at Neath; Afan Estuary."),
    ("the outlook frame is Welsh (the quote itself is marked data-notx)", "Natural Resources Wales' flood outlook, issued Wed 26 Nov, 10:30, says: “",
     "Mae rhagolwg llifogydd Cyfoeth Naturiol Cymru, a gyhoeddwyd Mer 26 Tach, 10:30, yn dweud: “"),
    ("all or nothing: one unknown sentence leaves the whole text English", "It should stay dry for the rest of today. Purple elephants dance.", None),
    ("an unknown text is left as it is", "Purple elephants dance on the Afan.", None),
    ("an older dictionary line still wins over the new tries", "River Amman, level rising", w.get("River Amman, level rising")),
    ("the board title", "Neath Port Talbot · Weather", "Castell-nedd Port Talbot · Tywydd"),
]
js = STUB + "".join(f"global.{k}={json.dumps(v)};\n" for k, v in DATA.items()) + engine + \
    "\nconsole.log(JSON.stringify(" + json.dumps([c[1] for c in CASES]) + ".map(function(s){return window.__cyTr(s)})));" + \
    "\nconsole.log(JSON.stringify(window.__cyKeys('Purple elephants dance. It should stay dry for the rest of today.')));"
r = subprocess.run([node], input=js, capture_output=True, text=True)
if r.returncode:
    print(r.stderr)
    check("engine runs under node", False)
else:
    out, keys = [json.loads(x) for x in r.stdout.strip().split("\n")]
    for (name, en, want), got in zip(CASES, out):
        check(name, got == want if want is not None else got is None)
        if want is not None and got != want:
            print("     got: ", got, "\n     want:", want)
    check("__cyKeys names only the missing sentence", keys == ["Purple elephants dance."])

# the shared file itself
_sh = json.loads((HERE / "parts" / "cy-shared.json").read_text(encoding="utf-8"))
shared = {**_sh["all"], **_sh["neath-port-talbot"]}
SLOTS = ("{D}", "{X}", "{Q}", "{L}", "#")
check("cy-shared.json: every line keeps its numbers, dates, words and names",
      all(k.count(s) == v.count(s) for k, v in shared.items() for s in SLOTS))
check("cy-shared.json: every place in the English has a place slot in the Welsh",
      all(k.count("{P}") == sum(v.count(s) for s in ("{P}", "{Pm}", "{Pe}", "{Px}")) for k, v in shared.items()))
SAME = {"#:#:# GMT", "#:#:# BST", "#mm", "{Q}", ".", "{Q} · # km", "{P} · # km", "Active Traveller", "AllTrails"}
check("cy-shared.json: no line is left in English by mistake (only names, units and marks stay the same)",
      [k for k, v in shared.items() if v == k and k not in SAME] == [])

print("\nall ok" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
