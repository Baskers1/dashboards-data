"""Build the two Plymouth & Ivybridge What's On companion pages from the What's On page.

    python3 build_companions.py season WHATSON.html OUT.html
    python3 build_companions.py big    WHATSON.html BIG_PAGE.html OUT.html
    python3 build_companions.py link   WHATSON.html OUT.html

season: the What's On page with its title, MODE and cross-link switched (same template,
        same data, so the two pages can never disagree).
big:    the current Big Buttons page with its `const DATA=` line replaced by the What's On
        events minus the "politics" group (as on the East Kent Big Buttons page).
link:   the What's On page with its OTHER_URL pointing at Season Ahead.
Inputs may carry the Artifact tool's host wrapper; outputs never do. Any unexpected
shape exits 2 and writes nothing.
"""

import json
import re
import sys

WHATSON_URL = "https://claude.ai/artifact/WqWnaRE8QoJi8sVpC2qMbd"
SEASON_URL = "https://claude.ai/artifact/9Wk4vNehvmPgSGjxLL71bx"
SEASON_TITLE = "<title>Plymouth &amp; Ivybridge · Season Ahead</title>"
# The season-mode month calendar is wider than a phone; without this its grid parents
# grow to fit it and the whole page scrolls sideways at 390px (East Kent's page does).
SEASON_FIX = "<style>.mast>*,.mast-top>*{min-width:0}</style>"
BIG_KEYS = ("title", "group", "town", "venue", "date", "end_date", "time", "price",
            "url", "summary", "highlight")
WRAP_HEAD = re.compile(r"\A<!doctype html><html[^>]*><head>.*?</head><body>\n?", re.S | re.I)


class Shape(Exception):
    pass


def unwrap(s: str) -> str:
    s = WRAP_HEAD.sub("", s, count=1)
    return re.sub(r"\n?</body></html>\s*\Z", "\n", s)


def sub_once(pattern: str, repl: str, s: str, what: str) -> str:
    out, n = re.subn(pattern, lambda _m: repl, s, flags=re.M)
    if n != 1:
        raise Shape(f"expected exactly one {what}, found {n}")
    return out


def data_of(s: str) -> dict:
    lines = [l for l in s.split("\n") if l.startswith("const DATA=")]
    if len(lines) != 1:
        raise Shape(f"expected one 'const DATA=' line, found {len(lines)}")
    return json.loads(lines[0][len("const DATA="):].rstrip().rstrip(";"))


def js_json(obj) -> str:
    # fetched text goes inside <script>: stop "</script>" or "<!--" ending it early
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\!--")


def season(whatson: str) -> str:
    s = unwrap(whatson)
    s = sub_once(r"^<title>.*</title>$", SEASON_TITLE + "\n" + SEASON_FIX, s, "<title> line")
    s = sub_once(r'^const MODE="near";.*$', 'const MODE="season";            // "near" | "season"', s, 'MODE="near" line')
    return sub_once(r"^const OTHER_URL=.*$", f'const OTHER_URL="{WHATSON_URL}";', s, "OTHER_URL line")


def link(whatson: str) -> str:
    s = unwrap(whatson)
    return sub_once(r"^const OTHER_URL=.*$", f'const OTHER_URL="{SEASON_URL}";', s, "OTHER_URL line")


def big(whatson: str, bigpage: str) -> str:
    d = data_of(whatson)
    if not d.get("events") or not d.get("meta", {}).get("updated"):
        raise Shape("What's On DATA has no events or no meta.updated")
    evs = [{k: e[k] for k in BIG_KEYS if k in e} for e in d["events"] if e.get("group") != "politics"]
    new = "const DATA=" + js_json({"updated": d["meta"]["updated"], "events": evs}) + ";"
    s = unwrap(bigpage)
    data_of(s)  # the Big Buttons page must already have exactly one DATA line
    return sub_once(r"^const DATA=.*$", new, s, "Big Buttons DATA line")


def main(argv: list[str]) -> int:
    try:
        if argv[:1] == ["season"] and len(argv) == 3:
            out, text = argv[2], season(open(argv[1], encoding="utf-8").read())
        elif argv[:1] == ["link"] and len(argv) == 3:
            out, text = argv[2], link(open(argv[1], encoding="utf-8").read())
        elif argv[:1] == ["big"] and len(argv) == 4:
            out = argv[3]
            text = big(open(argv[1], encoding="utf-8").read(), open(argv[2], encoding="utf-8").read())
        else:
            print(__doc__)
            return 2
    except (Shape, ValueError, OSError) as exc:
        print(f"error: {exc}; nothing written")
        return 2
    open(out, "w", encoding="utf-8").write(text)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
