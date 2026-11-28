"""Build one area's weather page from the shared template, the area's settings and its data.

    python3 build.py <area> <data.json> <out_dir>

  <area>       folder name under areas/ (e.g. west-herts)
  <data.json>  the hourly data blocks, {"LOCS": "<js literal>", "AIR": ..., ...}

Writes <out_dir>/index.html and, when the area's "photos" setting is "files", one file per
town photo in <out_dir>/heroes/. Publish the whole folder: the page loads only the photo
for the town on show. The output is the unhardened page, the same thing the hourly task
publishes to the artifact. tools/sync.py in the dashboards repo adds the CSP and dash-guard when it mirrors
the page, so nothing here emits them.

Exits 1 with a message, writing nothing, if a section, block or photo is missing.
"""
import base64
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from blocks import fill  # noqa: E402


def read(p):
    return Path(p).read_text(encoding="utf-8")


def heroes_literal(area_dir, mode):
    """The HEROES object literal, plus the photo files to publish beside the page.

    mode "inline": every photo inlined as base64 (the page as it was before the template).
    mode "files":  each photo is a separate file, heroes/<file>, fetched only when shown.
    """
    spec = json.loads(read(area_dir / "heroes.json"))
    parts, files = [], {}
    for key, fields in spec:
        img = area_dir / "heroes" / fields["file"]
        raw = img.read_bytes()
        if mode == "files":
            files["heroes/" + fields["file"]] = raw
            kv = [f'src:"heroes/{fields["file"]}"']
        elif mode == "inline":
            kv = [f'src:"data:{fields["mime"]};base64,{base64.b64encode(raw).decode("ascii")}"']
        else:
            raise SystemExit(f"build.py: unknown photos setting {mode!r}")
        for k, v in fields["meta"]:
            kv.append(f"{k}:{json.dumps(v, ensure_ascii=False)}")
        parts.append(f"{key}:{{{','.join(kv)}}}")
    return "{" + ",".join(parts) + "}", files


def jump_nav(settings, catalogue):
    links = "".join(f'<a class="jl" href="#{catalogue[s]["anchor"]}">{html.escape(catalogue[s]["jump"])}</a>'
                    for s in settings["sections"])
    return f'<nav class="jump" aria-label="Jump to a section">{links}</nav>'


def build(area, data_path):
    area_dir = HERE / "areas" / area
    settings = json.loads(read(area_dir / "settings.json"))
    catalogue = json.loads(read(HERE / "sections" / "catalogue.json"))
    unknown = [s for s in settings["sections"] if s not in catalogue]
    if unknown:
        raise SystemExit(f"build.py: unknown sections in {area}: {unknown}")

    sections = []
    for s in settings["sections"]:
        own = area_dir / "sections" / f"{s}.html"  # an area may keep its own markup for a section
        part = read(own if own.exists() else HERE / "sections" / f"{s}.html")
        about = settings.get("about", {}).get(s, "")
        extra = settings.get("extra", {}).get(s, "")
        sections.append(part.replace("{{ABOUT}}", about).replace("{{EXTRA}}", extra))

    blocks = {}
    for name in settings["static_blocks"]:
        blocks[name] = read(area_dir / "static" / f"{name}.js")
    blocks["HEROES"], files = heroes_literal(area_dir, settings.get("photos", "inline"))
    dynamic = json.loads(read(data_path))
    missing = [b for b in settings["data_blocks"] if b not in dynamic]
    if missing:
        raise SystemExit(f"build.py: data file has no {missing}")
    for name in settings["data_blocks"]:
        blocks[name] = dynamic[name]

    # fill the shell's own markers first, then drop the scripts and styles in, so text
    # inside a script can never be mistaken for a marker
    page = read(HERE / "shell.html")
    for marker, value in (("{{TITLE}}", html.escape(settings["title"], quote=False)),
                          ("{{H1}}", settings["h1_html"]),
                          ("{{JUMP}}", jump_nav(settings, catalogue)),
                          ("{{SECTIONS}}", "\n\n".join(sections)),
                          ("{{LANGBAR}}", settings.get("langbar_html", ""))):
        if page.count(marker) != 1:
            raise SystemExit(f"build.py: shell.html has {marker} {page.count(marker)} times")
        page = page.replace(marker, value)
    for name in settings.get("null_blocks", []):  # blocks this area has no data for
        blocks[name] = "null"
    code = settings.get("code", {})
    for name in settings["parts"]:
        marker = "{{PART:" + name + "}}"
        if page.count(marker) != 1:
            raise SystemExit(f"build.py: shell.html has {marker} {page.count(marker)} times")
        text = read(HERE / "parts" / name)
        for slot in re.findall(r"\{\{CODE:([a-z]+)\}\}", text):  # area-specific code (rivers, floods...)
            text = text.replace("{{CODE:" + slot + "}}", code_text(area_dir, code, slot, name))
        page = page.replace(marker, text)
    lang = code_text(area_dir, code, "lang", "shell.html")
    page = page.replace("{{LANGSCRIPT}}", "\n<script>" + lang + "</script>" if lang else "")
    extra = welsh_extra(settings, area)
    if "CYW" in blocks and extra:  # Welsh for wording the template added
        w = json.loads(blocks["CYW"])
        w.update(extra)
        blocks["CYW"] = json.dumps(w, ensure_ascii=False)
    return fill(page, blocks), files


def welsh_extra(settings, area):
    """Welsh that build.py adds to an area's CYW dictionary (and refresh_data.py takes out again).

    First the shared lines in parts/cy-shared.json (for every area whose "lang" code is the shared
    engine parts/cy.js): its "all" section, then the section named after the area, if any. Then
    the area's own lang_extra, which wins. One shared file means one place to fix a Welsh line
    for Ammanford and Neath Port Talbot; the per-area section keeps Ammanford's page from carrying
    lines only Neath Port Talbot shows (Ammanford's own chart code writes most of its Welsh).
    """
    extra = {}
    if settings.get("code", {}).get("lang") == "parts/cy.js":
        shared = json.loads(read(HERE / "parts" / "cy-shared.json"))
        extra.update(shared["all"])
        extra.update(shared.get(area, {}))
    extra.update(settings.get("lang_extra", {}))
    return extra


# optional slots: "extra" sits just before init() in app.js, so an area's own sections
# (Tayside's tides and bathing water) and any shared function it must replace go there
OPTIONAL_CODE = {"css", "lang", "extra"}


# slots every area gets unless its settings name another file ("code/empty.js" opts out)
DEFAULT_CODE = {"live": "parts/live.js"}


def code_text(area_dir, code, slot, where):
    """The file named for a code slot: "parts/..." is shared, anything else is in the area folder."""
    code = {**DEFAULT_CODE, **code}
    if slot not in code:
        if slot in OPTIONAL_CODE:
            return ""
        raise SystemExit(f"build.py: {where} needs code '{slot}' and settings.json names none")
    p = code[slot]
    return read(HERE / p if p.startswith("parts/") else area_dir / p)


def main(argv):
    if len(argv) != 4:
        raise SystemExit(__doc__)
    page, files = build(argv[1], argv[2])
    out = Path(argv[3])
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    for rel, raw in files.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_bytes(raw)
    print(f"OK {argv[1]} page {len(page.encode('utf-8'))} bytes, {len(files)} photo files "
          f"({sum(len(r) for r in files.values())} bytes)")


if __name__ == "__main__":
    main(sys.argv)
