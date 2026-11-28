"""Tests for the weather template build.  Run: python3 test_build.py

1. West Herts builds from the template, its area folder and a saved hour of data
   (fixtures/west-herts-2026-11-22T1250.json, lifted from the live page at 12:50). Before the
   layout changes of 22 Nov this build matched the live page byte for byte; see README.
2. The section list in settings.json decides which sections and jump links appear.
3. Missing data or an unknown section stops the build with a message.
"""
import copy
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

FIX = HERE / "fixtures" / "west-herts-2026-11-22T1250.json"
fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def with_settings(change):
    """Build west-herts with a modified copy of its settings."""
    path = HERE / "areas" / "west-herts" / "settings.json"
    orig = path.read_text(encoding="utf-8")
    s = json.loads(orig)
    change(s)
    path.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    try:
        return build.build("west-herts", FIX)[0]
    finally:
        path.write_text(orig, encoding="utf-8")


page, files = build.build("west-herts", FIX)
check("photos are separate files, none inlined", len(files) == 10 and "base64," not in page)
check("each photo is referenced by path", all(f'src:"{k}"' in page for k in files))
check("page is under 300 KB", len(page.encode("utf-8")) < 300_000)
check("Right now comes before the town picker and the photo",
      page.index('id="glance"') < page.index('id="tabs"') < page.index('id="hero"'))
check("Larger text sits in the header", page.index("<header>") < page.index('id="ltBtn"') < page.index("</header>"))
inline = with_settings(lambda s: s.__setitem__("photos", "inline"))
check("inline photo mode still works", inline.count("data:image/jpeg;base64,") == 10)
MARKERS = ("{{PART:", "{{BLOCK:", "{{CODE:", "{{SECTIONS}}", "{{JUMP}}", "{{ABOUT}}", "{{EXTRA}}", "{{H1}}", "{{TITLE}}")
check("no template marker left", not any(m in page for m in MARKERS))
check("west-herts: sewage code and data are in", "function renderSpills(){var S=SPILLS" in page and "var OUTLOOK=null;" in page)

no_rivers = with_settings(lambda s: s["sections"].remove("rivers"))
check("removed section is gone", 'aria-labelledby="rl"' not in no_rivers)
check("removed section has no jump link", 'href="#rl"' not in no_rivers)
check("other sections stay", 'aria-labelledby="fl"' in no_rivers and 'href="#fl"' in no_rivers)

moved = with_settings(lambda s: (s["sections"].remove("walks"), s["sections"].insert(1, "walks")))
check("section order follows settings", moved.index('aria-labelledby="k"') < moved.index('aria-labelledby="aq"'))

try:
    with_settings(lambda s: s["sections"].append("volcanoes"))
    check("unknown section is refused", False)
except SystemExit as e:
    check("unknown section is refused", "volcanoes" in str(e))

with tempfile.TemporaryDirectory() as td:
    d = json.loads(FIX.read_text(encoding="utf-8"))
    del d["AIR"]
    p = Path(td) / "d.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    try:
        build.build("west-herts", p)
        check("missing data block is refused", False)
    except SystemExit as e:
        check("missing data block is refused", "AIR" in str(e))

# Neath Port Talbot: Welsh rivers and floods (NRW), a flood outlook, no sewage section
NPT_FIX = HERE / "fixtures" / "neath-port-talbot-2026-11-22T1457.json"
npt, npt_files = build.build("neath-port-talbot", NPT_FIX)
check("npt: builds with no marker left", not any(m in npt for m in MARKERS))
check("npt: title", "<title>Neath Port Talbot · Weather</title>" in npt and "<h1>Neath Port Talbot · Weather</h1>" in npt)
check("npt: NRW river code, empty sewage code", "NRW station" in npt and "function renderSpills(){}" in npt)
check("npt: no sewage section or jump link", 'aria-labelledby="sw"' not in npt and 'href="#sw"' not in npt)
check("npt: SPILLS is null, OUTLOOK is data", "var SPILLS=null;" in npt and "var OUTLOOK={" in npt)
check("npt: one file per photo, shared by towns", len(npt_files) == 4 and all(f'src:"{k}"' in npt for k in npt_files))
check("npt: page is under 400 KB (300 KB before its Welsh dictionary, 27 Nov 2026)", len(npt.encode("utf-8")) < 400_000)
check("npt: area wording, not West Herts", "SITE" in npt and "Hertfordshire" not in npt and "Borehamwood" not in npt)
check("west-herts: no Welsh river or flood wording", "NRW station" not in page and "Natural Resources Wales" not in page)

# Ammanford: bilingual (Welsh switch), its own chart code, 30 towns sharing 7 photos
AMM_FIX = HERE / "fixtures" / "ammanford-2026-11-22T1728.json"
amm, amm_files = build.build("ammanford", AMM_FIX)
check("amm: builds with no marker left", not any(m in amm for m in MARKERS))
check("amm: title", "<title>Ammanford · Weather</title>" in amm and "<h1>Ammanford · Weather</h1>" in amm)
check("amm: Welsh switch and dictionary present", 'class="langbar"' in amm and "\nvar W={" in amm)
w = json.JSONDecoder().raw_decode(amm, amm.index("\nvar W=") + 7)[0]
amm_set = json.loads((HERE / "areas" / "ammanford" / "settings.json").read_text(encoding="utf-8"))
check("amm: template-only and shared Welsh lines are in the dictionary",
      all(w.get(k) == v for k, v in build.welsh_extra(amm_set, "ammanford").items()))
_shared = json.loads((HERE / "parts" / "cy-shared.json").read_text(encoding="utf-8"))
_extra = {a: build.welsh_extra(json.loads((HERE / "areas" / a / "settings.json").read_text(encoding="utf-8")), a)
          for a in ("ammanford", "neath-port-talbot", "west-herts", "tayside")}
check("shared Welsh: both Welsh boards get the \"all\" lines, other boards none",
      all((set(_shared["all"]) <= set(e)) == (a in ("ammanford", "neath-port-talbot")) for a, e in _extra.items()))
check("shared Welsh: only Neath Port Talbot gets its own section",
      set(_shared["neath-port-talbot"]) <= set(_extra["neath-port-talbot"])
      and not set(_shared["neath-port-talbot"]) & set(_extra["ammanford"]))
check("shared Welsh: an area's own lang_extra wins over the shared line",
      build.welsh_extra({"code": {"lang": "parts/cy.js"}, "lang_extra": {"dry": "X"}}, "ammanford")["dry"] == "X")
check("shared Welsh: every line is a non-empty string",
      all(isinstance(v, str) and v.strip() for s in ("all", "neath-port-talbot") for v in _shared[s].values()))
check("amm: one file per photo, shared by towns", len(amm_files) == 7 and all(f'src:"{k}"' in amm for k in amm_files))
check("amm: page is under 400 KB", len(amm.encode("utf-8")) < 400_000)
check("amm: grouped tabs say how many wider-area places", "tabmore" in amm and "places)" in amm)
check("amm: photo note for shared photos", "photonote" in amm and "may not show {place} itself" in amm)
check("amm: no West Herts or NPT wording", "Hertfordshire" not in amm and "Port Talbot · Weather" not in amm)
check("west-herts: no Welsh switch", 'class="langbar"' not in page and "{{BLOCK:CYW}}" not in page and "var CYL=" not in page)
check("npt: Welsh switch, shared engine and NPT place names (decision 6, 26 Nov 2026)",
      'class="langbar"' in npt and "\nvar W={" in npt and "Castell-nedd" in npt and "window.__cyKeys" in npt)
check("amm and npt: the same shared Welsh engine", all("window.__cyKeys" in pg and pg.count("var W={") == 1 for pg in (amm, npt)))
check("every area has the Larger text rules (Ammanford's own chart CSS once left them out)",
      all("html.bigtext.bigtext.bigtext body{font-size:22px" in pg and ".lt-btn{" in pg for pg in (page, npt, amm)))

# Tayside: the first coastal board (tides, bathing water); its own air, walks and "Right now"
# tiles come through the "extra" slot and replace the shared versions
tay, tay_files = build.build("tayside", HERE / "fixtures" / "tayside-2026-11-22T1837.json")
check("tay: builds with no marker left", not any(m in tay for m in MARKERS))
check("tay: title", "<title>Tayside · Weather</title>" in tay and "<h1>Tayside · Weather</h1>" in tay)
check("tay: tides and bathing sections with jump links",
      'aria-labelledby="t"' in tay and 'aria-labelledby="bw"' in tay and 'href="#t">Tides<' in tay and 'href="#bw">Bathing<' in tay)
check("tay: tide and bathing data present", "\nvar TIDES={" in tay and "\nvar BATHING={" in tay and "\nvar TIDEST={" in tay)
check("tay: its own versions come last, so they are the ones used",
      tay.rfind("function renderGlance(") > tay.rfind("{{") and "Next tide" in tay[tay.rfind("function renderGlance("):]
      and "Starting from" in tay[tay.rfind("function drawWalks("):] and "TD=TIDES[LOC.tide]" in tay[tay.rfind("function setTab("):])
check("tay: two photo files", sorted(tay_files) == ["heroes/car.jpg", "heroes/dun.jpg"])
check("tay: page is under 300 KB", len(tay.encode("utf-8")) < 300_000)
check("tay: Larger text rules and the 60+ text size", "html.bigtext.bigtext.bigtext body{font-size:22px" in tay and "60+ accessibility" in tay)
check("other areas: no tides or bathing", all('aria-labelledby="t"' not in pg and "var TIDES=" not in pg for pg in (page, npt, amm)))

# live forecast: every board carries it and asks for the shown town; the browser builder
# matches om_rows.place_block exactly (test_live.py, which needs node)
check("every board has the live forecast", all("function liveTown(k)" in pg and "function omBlock(" in pg for pg in (page, npt, amm, tay)))
check("every board asks for the shown town", all(pg[pg.rfind("function setTab("):].split("\n\n")[0].count("liveTown(k)") == 1 for pg in (page, npt, amm, tay)))
check("Welsh for the live conditions line", "Amodau byw Open-Meteo" in amm)
import subprocess  # noqa: E402
check("browser and snapshot builders agree (test_live.py)",
      subprocess.run([sys.executable, str(HERE / "test_live.py")], capture_output=True, text=True).returncode == 0)
check("verdict line rules and placement (test_verdict.py)",
      subprocess.run([sys.executable, str(HERE / "test_verdict.py")], capture_output=True, text=True).returncode == 0)
check("age badge rules and placement (test_age.py)",
      subprocess.run([sys.executable, str(HERE / "test_age.py")], capture_output=True, text=True).returncode == 0)

# East Kent: six towns with their own floods, gauges, beaches, releases and tide tables (extra slot),
# and its own markup for the air, tides, bathing and walks sections
ek, ek_files = build.build("east-kent", HERE / "fixtures" / "east-kent-2026-11-22T1823.json")
check("ek: builds with no marker left", not any(m in ek for m in MARKERS))
check("ek: title", "<title>East Kent · Weather</title>" in ek and "<h1>East Kent · Weather</h1>" in ek)
check("ek: its own sections", all(f'aria-labelledby="{a}"' in ek for a in ("w", "fl", "aq", "t", "bw", "sw", "k")) and 'id="bwl"' in ek and 'id="wnote"' in ek)
check("ek: six photo files", len(ek_files) == 6)
check("ek: page under 300 KB (was 957 KB with a full year of tides)", len(ek.encode("utf-8")) < 300_000)
check("ek: town remembered, chart code hooked, live forecast asked", "dash-town" in ek and "renderAll();liveTown(k)}" in ek)
check("ek: no blanket 15px rule (the tiny temperature, F2)", "span{font-size:15px!important}" not in ek)
check("every board has the live forecast (East Kent too)", "function liveTown(k)" in ek)

print("\nall ok" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
