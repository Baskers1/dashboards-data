"""One-off: split a published weather page into the template, an area folder and a data file.

    python3 extract_page.py <published index.html> <area> <data out.json>

Used once per board when it moves onto the template. It writes:
  shell.html, parts/*, sections/*.html, sections/catalogue.json   (shared; only if absent)
  areas/<area>/settings.json, static/*.js, heroes.json, heroes/*  (this board)
  <data out.json>                                                  (this hour's data blocks)
then builds the page back and refuses to keep anything unless the rebuild, hardened,
equals the published page byte for byte.
"""
import base64
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from blocks import lift  # noqa: E402

DATA_BLOCKS = ["LOCS", "AIR", "RIVERS", "FLOODS", "SPILLS"]      # refreshed every hour
STATIC_BLOCKS = ["TABS", "AREAS", "WALKS", "WSETS"]               # change only by hand
CSP = re.compile(r'<meta http-equiv="Content-Security-Policy"[^>]*>')
GUARD = re.compile(r'<script id="dash-guard">.*?</script>', re.S)
TAG = re.compile(r"<(script|style)([^>]*)>(.*?)</\1>", re.S)
SECTION = re.compile(r'<section class="(?:card(?: wide)?|wide)" aria-labelledby="([a-z]+)">.*?</section>', re.S)
ABOUT = re.compile(r'<details class="about">.*?</details>', re.S)
JUMP = re.compile(r'<nav class="jump" aria-label="Jump to a section">(.*?)</nav>', re.S)
TITLE = re.compile(r"<title>(.*?)</title>")
H1 = re.compile(r"<h1>(.*?)</h1>")
SEC_NAMES = {"w": "weather", "aq": "air", "rl": "rivers", "fl": "floods", "sw": "sewage", "k": "walks",
             "t": "tides", "bw": "bathing"}


def write(p, text, only_if_absent=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    if only_if_absent and p.exists():
        if p.read_text(encoding="utf-8") != text:
            print(f"NOTE: {p.relative_to(HERE)} already exists and differs; kept the existing one")
        return
    p.write_text(text, encoding="utf-8")


def heroes_spec(literal, area_dir):
    """Split the HEROES literal into photo files and a JSON list of their captions."""
    spec = []
    for m in re.finditer(r'([a-z]+):\{src:"data:([^;]+);base64,([A-Za-z0-9+/=]+)",(.*?)\}(?=,[a-z]+:\{src:|$)',
                         literal[1:-1]):
        key, mime, b64, rest = m.groups()
        ext = {"image/jpeg": "jpg", "image/webp": "webp", "image/png": "png"}[mime]
        (area_dir / "heroes").mkdir(parents=True, exist_ok=True)
        (area_dir / "heroes" / f"{key}.{ext}").write_bytes(base64.b64decode(b64))
        meta = [[k, json.loads(v)] for k, v in re.findall(r'([a-z]+):("(?:[^"\\]|\\.)*")', rest)]
        spec.append([key, {"file": f"{key}.{ext}", "mime": mime, "meta": meta}])
    return spec


def main(argv):
    src_path, area, data_out = argv[1], argv[2], Path(argv[3])
    published = Path(src_path).read_text(encoding="utf-8")
    page = GUARD.sub("", CSP.sub("", published, count=1), count=1)
    area_dir = HERE / "areas" / area

    # scripts and styles become parts; the biggest script is the app
    parts, order = {}, []
    tags = list(TAG.finditer(page))
    app = max((t for t in tags if t.group(1) == "script"), key=lambda t: len(t.group(3)))
    for i, t in enumerate(tags):
        idm = re.search(r'id="([^"]+)"', t.group(2))
        name = "app.js" if t is app else f"{i:02d}-{idm.group(1) if idm else t.group(1)}.{'js' if t.group(1) == 'script' else 'css'}"
        parts[name] = t.group(3)
        order.append((t.start(3), t.end(3), name))
    shell = page
    for a, b, name in reversed(order):
        shell = shell[:a] + "{{PART:" + name + "}}" + shell[b:]

    # sections: each card between the jump nav and </main>
    secs = list(SECTION.finditer(shell))
    sec_ids, about = [], {}
    for s in secs:
        sid = SEC_NAMES[s.group(1)]
        body = s.group(0)
        ab = ABOUT.search(body)
        if ab:
            about[sid] = ab.group(0)
            body = body[:ab.start()] + "{{ABOUT}}" + body[ab.end():]
        write(HERE / "sections" / f"{sid}.html", body, only_if_absent=True)
        sec_ids.append(sid)
    shell = shell[:secs[0].start()] + "{{SECTIONS}}" + shell[secs[-1].end():]

    # jump nav, title, h1
    jm = JUMP.search(shell)
    jump = {}
    for href, label in re.findall(r'<a class="jl" href="#([a-z]+)">([^<]+)</a>', jm.group(1)):
        jump[SEC_NAMES[href]] = {"anchor": href, "jump": label}
    shell = shell[:jm.start()] + "{{JUMP}}" + shell[jm.end():]
    title = TITLE.search(shell).group(1)
    shell = TITLE.sub("<title>{{TITLE}}</title>", shell, count=1)
    h1 = H1.search(shell).group(1)
    shell = H1.sub("<h1>{{H1}}</h1>", shell, count=1)

    # data blocks out of the app
    app_tpl, blocks = lift(parts["app.js"], DATA_BLOCKS + STATIC_BLOCKS + ["HEROES"])
    parts["app.js"] = app_tpl
    for name in STATIC_BLOCKS:
        write(area_dir / "static" / f"{name}.js", blocks[name])
    write(area_dir / "heroes.json", json.dumps(heroes_spec(blocks["HEROES"], area_dir), ensure_ascii=False, indent=1))
    data_out.write_text(json.dumps({k: blocks[k] for k in DATA_BLOCKS}, ensure_ascii=False), encoding="utf-8")

    write(HERE / "shell.html", shell, only_if_absent=True)
    for name, text in parts.items():
        write(HERE / "parts" / name, text, only_if_absent=True)
    cat_path = HERE / "sections" / "catalogue.json"
    cat = json.loads(cat_path.read_text()) if cat_path.exists() else {}
    for k, v in jump.items():
        cat.setdefault(k, v)
    write(cat_path, json.dumps(cat, ensure_ascii=False, indent=1))
    settings = {"title": title.replace("&amp;", "&"), "h1_html": h1, "sections": sec_ids,
                "parts": [n for _, _, n in order], "static_blocks": STATIC_BLOCKS,
                "data_blocks": DATA_BLOCKS, "about": about}
    write(area_dir / "settings.json", json.dumps(settings, ensure_ascii=False, indent=1))
    print(f"extracted {area}: {len(sec_ids)} sections {sec_ids}, {len(parts)} parts")


if __name__ == "__main__":
    main(sys.argv)
