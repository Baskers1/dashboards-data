#!/usr/bin/env python3
"""Data helper for the Ammanford Community Watch and Consultation Watch pages.

Each page's refreshable data is held either inline as JSON constants in the page script or, once
the page has been through the data.json split (R2), in a data.json beside the page that the page
fetches at load. This tool pulls the refreshable constants out into a state file, checks them, and
writes them back to whichever of the two they came from -- so a half-split page works too. Photos
(PHOTOS, the CSS base64) and code-like constants (Consultation Watch LENSES, which holds regexes)
are never touched.

KIND is "community" or "consultation" (Ammanford), or "community:east-kent", "community:tayside",
"community:west-herts", "community:neath-port-talbot" or "community:plymouth". Those pages hold their data as JavaScript literals rather than JSON; they
are read with page_consts (Node) and written back as JSON, which is still valid JavaScript.

Commands:
  unwrap  SAVED.html PAGE.html           -> strips the host wrapper from a file saved by Artifact read
  extract KIND PAGE.html OUT.json       -> writes the data constants to OUT.json, reading each from
                                           PAGE.html's sibling data.json where it lives there
  check   KIND STATE.json                -> validates; exit 1 if anything would block publishing
  apply   KIND STATE.json PAGE.html OUTDIR
                                          -> validates, then writes the new data to OUTDIR: PAGE for
                                           constants still inline, data.json for ones that moved

apply refuses to write if check finds errors (non-http(s) or blocked links, missing id/title/url,
duplicate ids, bad dates or statuses, unknown place keys, Welsh lists out of step with English).
Missing Welsh is a warning: the page shows English with a note.
"""
import datetime as dt
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # works under python3 -I too
from amm_whatson import find_obj, put_obj, check_url, parse_date, report, read, write, load_json, to_script_json  # noqa: E402
from page_consts import eval_consts, find_decl  # noqa: E402

COMMUNITY_AREAS = set(
    "ammanford pantyffynnont betws glanamman garnant brynamman tycroes saron penybanc llandybie "
    "capelhendre penygroes gorslas crosshands tumble cefneithin drefach llannon pontyberem llandeilo "
    "ffairfach trapp bethlehem llanarthne llanelli felinfoel hendy llangennech pontarddulais gorseinon "
    "clydach cwmgors gcg pontardawe ystalyfera ystradgynlais carms swansea npt powys wales".split())
CONSULT_PLACES = set("ammanford amman llandybie crosshands llandeilo llanelli swansea npt ystrad".split())

KINDS = {
    "community": {
        "consts": ["ITEMS", "GROUPS", "SOON", "SOON_CY", "WATCH", "WATCH_CY", "LAST_CHECKED"],
        "statuses": {"open", "decision", "ongoing", "closed"},
    },
    "consultation": {
        "consts": ["ITEMS", "PETITIONS", "WATCH", "WATCH_CY", "COLLECTED", "COLLECTED_CY", "WATCH_NOTE",
                   "WATCH_NOTE_CY", "EMPTY_CHARITY", "EMPTY_CHARITY_CY", "STATUS", "PLACE"],
        "statuses": {"open", "closed", "decision"},
    },
}
# English-only Community Watch pages. Allowed place keys = the page's AREAS (towns) plus AREAL (the
# wide keys: thanet, herts, bucks, tayside, everywhere; on two pages AREAL repeats the towns too).
for _area in ("east-kent", "tayside", "west-herts", "neath-port-talbot", "plymouth"):
    KINDS[f"community:{_area}"] = {
        "consts": ["ITEMS", "GROUPS", "SOON", "WATCH", "BIG"],
        "statuses": {"open", "decision", "ongoing", "closed"},
        "js_literals": True,
    }
AREA_KEYS = "_area_keys"  # stored in the state file by extract; never written to the page or data.json


DATA_SIBLING = "data.json"


def data_key(const):
    """The data.json key for a page constant. The R2 splitter lowercases the name."""
    return const.lower()


def data_path(page):
    return os.path.join(os.path.dirname(os.path.abspath(page)), DATA_SIBLING)


def load_sources(kind, page):
    """Read every constant for KIND from wherever it now lives.

    R2 moves a page's refreshable data out of the page script into a sibling data.json. A page can
    be half-split -- some constants moved, some not -- so a constant is looked up in data.json
    first and in the page second, and where it was found
    is recorded so apply writes it back to the same place. A constant in neither is still a hard
    error, from find_obj.

    Returns (state, origin, page_text, data_obj_or_None); origin[const] is "data" or "page".
    """
    s = read(page)
    dp = data_path(page)
    d = load_json(dp) if os.path.exists(dp) else None
    cfg = kind_cfg(kind)
    st, origin = {}, {}
    for c in cfg["consts"]:
        k = data_key(c)
        if d is not None and k in d:
            st[c], origin[c] = d[k], "data"
        elif not cfg.get("js_literals"):
            st[c], origin[c] = find_obj(s, c)[0], "page"
        else:
            origin[c] = "page"
    inline = [c for c in cfg["consts"] if origin[c] == "page"]
    if cfg.get("js_literals"):
        st.update(eval_consts(s, inline + ["AREAS", "AREAL"]))
        st[AREA_KEYS] = sorted(set(st.pop("AREAS")) | set(st.pop("AREAL")))
    return st, origin, s, d


def where(origin):
    n = sum(1 for v in origin.values() if v == "data")
    return f"{n} from {DATA_SIBLING}, {len(origin) - n} from the page"


def kind_cfg(kind):
    if kind not in KINDS:
        raise SystemExit(f"KIND must be one of {', '.join(KINDS)}")
    return KINDS[kind]


def check_items(items, statuses, errors, warnings, welsh=True):
    ids = set()
    for i, it in enumerate(items):
        where = f"item {i} '{str(it.get('title', ''))[:40]}'"
        iid = it.get("id")
        if not iid:
            errors.append(f"{where}: no id")
        elif iid in ids:
            errors.append(f"{where}: duplicate id {iid}")
        ids.add(iid)
        if not str(it.get("title", "")).strip():
            errors.append(f"{where}: no title")
        if not it.get("url"):
            errors.append(f"{where}: no url")
        else:
            check_url(it["url"], f"{where} url", errors, warnings)
        if it.get("status") not in statuses:
            errors.append(f"{where}: bad status {it.get('status')!r}")
        if it.get("deadline") not in (None, "") and parse_date(it["deadline"]) is None:
            errors.append(f"{where}: bad deadline {it.get('deadline')!r}")
        if welsh and (not isinstance(it.get("cy"), dict) or not it["cy"].get("title")):
            warnings.append(f"{where}: no Welsh (cy.title)")
    return ids


def check_watch_list(watch, errors, warnings):
    for i, w in enumerate(watch):
        if not (isinstance(w, list) and len(w) >= 2):
            errors.append(f"WATCH {i}: expected [label, url]")
            continue
        check_url(w[1], f"WATCH {i} '{str(w[0])[:40]}'", errors, warnings)


def validate_community(st):
    errors, warnings = [], []
    ids = check_items(st["ITEMS"], KINDS["community"]["statuses"], errors, warnings)
    for i, it in enumerate(st["ITEMS"]):
        where = f"item {i} ({it.get('id')})"
        bad = [a for a in it.get("at") or [] if a not in COMMUNITY_AREAS]
        if bad:
            errors.append(f"{where}: unknown area key(s) {bad}")
        cy = it.get("cy") or {}
        if "aff" in cy and len(cy["aff"]) != len(it.get("aff") or []):
            errors.append(f"{where}: cy.aff has {len(cy['aff'])} entries, aff has {len(it.get('aff') or [])}")
    for i, g in enumerate(st["GROUPS"]):
        where = f"group {i} '{str(g.get('n', ''))[:40]}'"
        if not str(g.get("n", "")).strip():
            errors.append(f"{where}: no name")
        if g.get("url"):
            check_url(g["url"], f"{where} url", errors, warnings)
        if g.get("area") not in COMMUNITY_AREAS:
            errors.append(f"{where}: unknown area {g.get('area')!r}")
        if not isinstance(g.get("cy"), dict):
            warnings.append(f"{where}: no Welsh (cy)")
    for a, b in (("SOON", "SOON_CY"), ("WATCH", "WATCH_CY")):
        if len(st[a]) != len(st[b]):
            errors.append(f"{b} has {len(st[b])} entries, {a} has {len(st[a])} (must match, same order)")
    check_watch_list(st["WATCH"], errors, warnings)
    if parse_date(st["LAST_CHECKED"]) is None:
        errors.append(f"LAST_CHECKED is not a date: {st['LAST_CHECKED']!r}")
    return errors, warnings, ids


def validate_community_en(st):
    """East Kent, Tayside, West Herts: no Welsh; place keys checked against AREAS + AREAL."""
    errors, warnings = [], []
    ids = check_items(st["ITEMS"], {"open", "decision", "ongoing", "closed"}, errors, warnings, welsh=False)
    keys = set(st.get(AREA_KEYS) or [])
    if not keys:
        errors.append(f"{AREA_KEYS} missing: run extract on the page first")
    for i, it in enumerate(st["ITEMS"]):
        bad = [a for a in it.get("at") or [] if a not in keys]
        if keys and bad:
            errors.append(f"item {i} ({it.get('id')}): unknown place key(s) {bad}")
    for i, g in enumerate(st["GROUPS"]):
        where = f"group {i} '{str(g.get('n', ''))[:40]}'"
        if not str(g.get("n", "")).strip():
            errors.append(f"{where}: no name")
        if g.get("url"):
            check_url(g["url"], f"{where} url", errors, warnings)
        areas = g.get("area") if isinstance(g.get("area"), list) else [g.get("area")]
        if keys and any(a not in keys for a in areas):
            errors.append(f"{where}: unknown area {g.get('area')!r}")
    check_watch_list(st["WATCH"], errors, warnings)
    return errors, warnings, ids


def validate_consultation(st):
    errors, warnings = [], []
    ids = check_items(st["ITEMS"], KINDS["consultation"]["statuses"], errors, warnings)
    for i, it in enumerate(st["ITEMS"]):
        where = f"item {i} ({it.get('id')})"
        en, cy = it.get("a") or {}, (it.get("cy") or {}).get("a") or {}
        for k, lst in en.items():
            if k in cy and len(cy[k]) != len(lst):
                errors.append(f"{where}: cy.a.{k} has {len(cy[k])} entries, a.{k} has {len(lst)}")
    for i, p in enumerate(st["PETITIONS"]):
        where = f"petition {i} '{str(p.get('title', ''))[:40]}'"
        if not p.get("url"):
            errors.append(f"{where}: no url")
        else:
            check_url(p["url"], f"{where} url", errors, warnings)
        if parse_date(p.get("date")) is None:
            errors.append(f"{where}: bad date {p.get('date')!r}")
        if not isinstance(p.get("cy"), dict):
            warnings.append(f"{where}: no Welsh (cy)")
    check_watch_list(st["WATCH"], errors, warnings)
    for w in st["WATCH"]:
        if isinstance(w, list) and len(w) >= 2 and w[1] not in st["WATCH_CY"]:
            warnings.append(f"WATCH '{str(w[0])[:40]}': no Welsh label in WATCH_CY")
    for iid, places in st["PLACE"].items():
        if iid not in ids:
            warnings.append(f"PLACE: no item with id {iid}")
        bad = [p for p in (places if isinstance(places, list) else [places]) if p not in CONSULT_PLACES]
        if bad:
            errors.append(f"PLACE {iid}: unknown place key(s) {bad}")
    for iid in st["STATUS"]:
        if iid not in ids:
            warnings.append(f"STATUS: no item with id {iid}")
    return errors, warnings, ids


def validate(kind, st):
    """Return (errors, warnings) for a state dict. Errors block publishing."""
    cfg = kind_cfg(kind)
    gone = [c for c in cfg["consts"] if c not in st]
    if gone:
        return [f"state is missing {', '.join(gone)}"], []
    fn = {"community": validate_community, "consultation": validate_consultation}.get(kind, validate_community_en)
    errors, warnings, _ = fn(st)
    return errors, warnings


WRAP_HEAD, WRAP_TAIL = "<!doctype html><html><head>", "</body></html>"


def unwrap(s):
    """Strip the host wrapper the Artifact tool adds to a saved page: everything up to and including the
    wrapper's first <body> line, and the final </body></html>. Pages without the wrapper are returned as-is."""
    if not s.startswith(WRAP_HEAD) or "</head><body>" not in s:
        return s
    s = s.split("</head><body>", 1)[1]
    s = s[1:] if s.startswith("\n") else s
    s = s.rstrip()
    return s[:-len(WRAP_TAIL)] if s.endswith(WRAP_TAIL) else s


def cmd_unwrap(saved, out):
    write(out, unwrap(read(saved)))
    print(f"unwrapped -> {out}")


def cmd_extract(kind, page, out):
    st, origin, _, _ = load_sources(kind, page)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    print(f"{kind}: items {len(st['ITEMS'])} -> {out} ({where(origin)})")


def cmd_check(kind, p):
    errors, warnings = validate(kind, load_json(p))
    report(errors, warnings)
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


def cmd_apply(kind, p, page, outdir):
    st = load_json(p)
    errors, warnings = validate(kind, st)
    report(errors, warnings)
    if errors:
        raise SystemExit(f"refusing to write page: {len(errors)} errors (see above)")
    _, origin, s, d = load_sources(kind, page)
    inline = [c for c in kind_cfg(kind)["consts"] if origin[c] == "page"]
    for c in inline:
        if kind_cfg(kind).get("js_literals"):
            _, a, b = find_decl(s, c)
            s = s[:a] + to_script_json(st[c]) + s[b:]
        else:
            s = put_obj(s, c, st[c])
    os.makedirs(outdir, exist_ok=True)
    # The page is always written, even when every constant has moved and it is therefore
    # unchanged, so that callers can treat OUTDIR as the complete publishable set.
    out_page = os.path.join(outdir, os.path.basename(page))
    write(out_page, s)
    wrote = [out_page]
    if d is not None:
        for c in kind_cfg(kind)["consts"]:
            if origin[c] == "data":
                d[data_key(c)] = st[c]
        d["generated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out_data = os.path.join(outdir, DATA_SIBLING)
        with open(out_data, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
            f.write("\n")
        wrote.append(out_data)
    print(f"wrote {', '.join(wrote)}: {len(st['ITEMS'])} items, {len(warnings)} warnings ({where(origin)})")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(0)
    {"unwrap": cmd_unwrap, "extract": cmd_extract, "check": cmd_check, "apply": cmd_apply}[a[0]](*a[1:])
