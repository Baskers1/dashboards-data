#!/usr/bin/env python3
"""Helper for the three Ammanford What's On pages (What's On, Season Ahead, Big Buttons).

The pages hold their listings inline as JSON in the page script:
  const DATA = {...};     What's On + Season Ahead: {"events":[...],"news":[...],"meta":{...}} (identical in both)
                          Big Buttons: {"updated":"YYYY-MM-DD","events":[...]}  (non-politics events, fewer fields)
  const CY_SUM = {...};   identical in all three: English summary -> Welsh summary (event + news summaries and meta.gaps)

Commands:
  extract  WHATSON.html OUT.json        -> writes {"DATA":..., "CY_SUM":...} from the What's On page
  missing  STATE.json                   -> lists English summaries that have no Welsh in CY_SUM
  check    STATE.json                   -> validates the data; exit 1 if anything would block publishing
  sport    STATE.json SPORT.json [TODAY]      -> merges All Wales Sport fixtures (ammanford/whats-on/data/sport.json, put on
                                         GitHub weekly by the Mac) into STATE.json in place, with Welsh summaries
  apply    STATE.json WHATSON.html SEASON.html BIG.html OUTDIR
                                         -> validates, then writes the three updated pages to OUTDIR (same file names)

apply refuses to write if check finds errors (bad link schemes, blocked domains, missing title/url/date,
bad dates). Warnings (http links, duplicates, missing Welsh) are printed but do not block.
"""
import datetime as dt
import hashlib, json, os, re, sys
from urllib.parse import urlparse

BIG_FIELDS = ["title", "group", "town", "venue", "date", "end_date", "price", "url", "summary", "time", "highlight"]
URL_FIELDS = ["url", "flagUrl", "meetings_url"]
# Known spam / unsafe sources. Add a domain here and apply will refuse any listing that links to it.
BLOCKED_DOMAINS = {"parchoward.org.uk"}


def dead_links(path=None):
    """URLs the weekly link check found dead (LINKS.md 3.6 and 4). The ledger lives in the public
    dashboards repo; on a machine without it (a cloud session) this returns an empty set and the
    check is skipped, never failed."""
    path = path or os.environ.get("LINK_LEDGER") or os.path.expanduser("~/dashboards/data/link-ledger.json")
    try:
        with open(path, encoding="utf-8") as f:
            urls = json.load(f).get("urls", {})
    except (OSError, ValueError):
        return set()
    return {u for u, e in urls.items() if e.get("state") == "dead"}


DEAD_LINKS = dead_links()


def find_obj(s, name):
    m = re.search(r'const\s+' + name + r'\s*=\s*', s)
    if not m:
        raise SystemExit(f"const {name} not found")
    start = m.end()
    obj, end = json.JSONDecoder().raw_decode(s, start)
    return obj, start, end


def to_script_json(obj):
    """JSON that is safe inside a <script> block: no '<' at all, so no </script>, <!-- or <script can appear."""
    txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return txt.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def put_obj(s, name, obj):
    _, a, b = find_obj(s, name)
    return s[:a] + to_script_json(obj) + s[b:]


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def cmd_extract(page, out):
    s = read(page)
    data, _, _ = find_obj(s, "DATA")
    cy, _, _ = find_obj(s, "CY_SUM")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"DATA": data, "CY_SUM": cy}, f, ensure_ascii=False, indent=1)
    print(f"events {len(data['events'])}, news {len(data.get('news', []))}, CY_SUM {len(cy)} -> {out}")


def used_keys(d):
    """Every English string the Welsh switch looks up in CY_SUM: event and news summaries, and meta.gaps."""
    u = {e.get("summary") for e in d["events"]} | {n.get("summary") for n in d.get("news", [])}
    u |= set((d.get("meta") or {}).get("gaps") or [])
    return {t for t in u if t}


def missing(state):
    cy = state["CY_SUM"]
    return sorted(t for t in used_keys(state["DATA"]) if t not in cy)


def cmd_missing(p):
    m = missing(load_json(p))
    print(json.dumps(m, ensure_ascii=False, indent=1)); print(len(m), "missing", file=sys.stderr)


def check_url(u, where, errors, warnings):
    if not isinstance(u, str) or not u.strip():
        errors.append(f"{where}: empty link")
        return
    p = urlparse(u.strip())
    if p.scheme not in ("http", "https") or not p.netloc:
        errors.append(f"{where}: link is not http(s): {u[:80]}")
        return
    host = p.netloc.lower().split(":")[0]
    if any(host == b or host.endswith("." + b) for b in BLOCKED_DOMAINS):
        errors.append(f"{where}: blocked domain {host}")
    if p.scheme == "http":
        warnings.append(f"{where}: plain http link {u[:80]}")
    if u.strip() in DEAD_LINKS:
        # a warning, not an error: the refresh re-finds or drops it (LINKS.md 4), and sync.py in the
        # dashboards repo already publishes it without a link once it has been dead on two runs
        warnings.append(f"{where}: dead link (weekly link check), re-find or drop it: {u[:80]}")


def parse_date(v):
    try:
        return dt.date.fromisoformat(v)
    except (TypeError, ValueError):
        return None


def validate(d):
    """Return (errors, warnings) for a DATA object. Errors block publishing."""
    errors, warnings = [], []
    seen = set()
    for i, e in enumerate(d.get("events", [])):
        where = f"event {i} '{str(e.get('title', ''))[:40]}'"
        if not str(e.get("title", "")).strip():
            errors.append(f"{where}: no title")
        if not e.get("url"):
            errors.append(f"{where}: no url")
        for k in URL_FIELDS:
            if k in e and e[k] not in (None, ""):
                check_url(e[k], f"{where} {k}", errors, warnings)
        start = parse_date(e.get("date"))
        if start is None:
            errors.append(f"{where}: bad date {e.get('date')!r}")
        if e.get("end_date") not in (None, ""):
            end = parse_date(e["end_date"])
            if end is None:
                errors.append(f"{where}: bad end_date {e['end_date']!r}")
            elif start and end < start:
                errors.append(f"{where}: end_date {end} is before date {start}")
        key = (str(e.get("title", "")).strip().lower(), e.get("date"), str(e.get("venue", "")).strip().lower())
        if key in seen:
            warnings.append(f"{where}: duplicate of an earlier listing")
        seen.add(key)
    for i, n in enumerate(d.get("news", [])):
        where = f"news {i} '{str(n.get('headline', ''))[:40]}'"
        if n.get("url"):
            check_url(n["url"], f"{where} url", errors, warnings)
    return errors, warnings


def report(errors, warnings, extra_warnings=()):
    for w in list(warnings) + list(extra_warnings):
        print("WARNING:", w, file=sys.stderr)
    for e in errors:
        print("ERROR:", e, file=sys.stderr)


def cmd_check(p):
    st = load_json(p)
    errors, warnings = validate(st["DATA"])
    miss = missing(st)
    report(errors, warnings, [f"{len(miss)} summaries have no Welsh (run 'missing')"] if miss else [])
    print(f"{len(errors)} errors, {len(warnings) + (1 if miss else 0)} warnings")
    sys.exit(1 if errors else 0)


def big_events(events):
    out = []
    for e in events:
        if e.get("group") == "politics":
            continue
        out.append({k: e[k] for k in BIG_FIELDS if k in e and e[k] not in (None, "", False)})
    return out


def cmd_apply(p, w, se, b, outdir):
    st = load_json(p)
    d, cy = st["DATA"], st["CY_SUM"]
    errors, warnings = validate(d)
    used = used_keys(d)
    cy = {k: v for k, v in cy.items() if k in used}  # prune Welsh entries nobody uses any more
    miss = [t for t in used if t not in cy]
    report(errors, warnings, [f"{len(miss)} summaries have no Welsh (run 'missing')"] if miss else [])
    if errors:
        raise SystemExit(f"refusing to write pages: {len(errors)} errors (see above)")
    updated = (d.get("meta") or {}).get("updated")
    os.makedirs(outdir, exist_ok=True)
    for src in (w, se):
        s = put_obj(read(src), "DATA", d)
        s = put_obj(s, "CY_SUM", cy)
        write(os.path.join(outdir, os.path.basename(src)), s)
    s = read(b)
    s = put_obj(s, "DATA", {"updated": updated, "events": big_events(d["events"])})
    s = put_obj(s, "CY_SUM", cy)
    write(os.path.join(outdir, os.path.basename(b)), s)
    print(f"wrote 3 pages to {outdir}: {len(d['events'])} events, {len(d.get('news', []))} news, CY_SUM {len(cy)}, updated {updated}")


# ---------- sport fixtures (All Wales Sport, fetched by the Mac) ----------

SPORT_SOURCE = "All Wales Sport"
SPORT_MAX_AGE_DAYS = 8
SPORT_EN = {"rugby union": "Rugby union", "football": "Football", "youth rugby": "Youth rugby", "youth football": "Youth football"}
SPORT_CY = {"rugby union": "rygbi'r undeb", "football": "pêl-droed", "youth rugby": "rygbi ieuenctid", "youth football": "pêl-droed ieuenctid"}
NO_TIME_EN, NO_TIME_CY = " Kick-off time not listed.", " Amser y gic gyntaf heb ei restru."


def _norm(t):
    return re.sub(r"[^a-z0-9]+", " ", str(t).lower()).strip()


def sport_summary(f):
    """(English, Welsh) one-line summary for a fixture, built from fixed wording so no translation is needed.
    Competition names stay as they are, like show and band names."""
    en = f"{SPORT_EN[f['sport']]} fixture ({f['competition']})."
    cy = f"Gêm {SPORT_CY[f['sport']]} ({f['competition']})."
    if not f.get("time"):
        en, cy = en + NO_TIME_EN, cy + NO_TIME_CY
    return en, cy


def merge_sport(state, sport, today):
    """Replace last week's All Wales Sport listings with this file's fixtures (today .. +120 days). A fixture the weekly
    research already lists (same date, a title naming the home side and the away side's first word) is skipped.
    A file older than SPORT_MAX_AGE_DAYS changes nothing. Returns the number of fixtures added."""
    fetched = parse_date(str((sport.get("meta") or {}).get("fetched_at", ""))[:10])
    t0 = parse_date(today)
    if fetched is None or (t0 - fetched).days > SPORT_MAX_AGE_DAYS:
        print(f"sport file is stale or undated ({(sport.get('meta') or {}).get('fetched_at')!r}); not merged", file=sys.stderr)
        return 0
    d, cy = state["DATA"], state["CY_SUM"]
    others = [e for e in d["events"] if e.get("source") != SPORT_SOURCE]
    by_day = {}
    for e in others:
        by_day.setdefault(e.get("date"), []).append(_norm(e.get("title", "")))
    added = []
    for f in sport.get("fixtures") or []:
        day = parse_date(f.get("date"))
        if day is None or not (t0 <= day <= t0 + dt.timedelta(days=120)):
            continue
        home, away = (_norm(x) for x in re.sub(r" \((U18|youth|women)\)$", "", f["title"]).split(" v ", 1))
        if any(home in t and away.split(" ")[0] in t for t in by_day.get(f["date"], [])):
            continue
        en, cyw = sport_summary(f)
        e = {"title": f["title"], "category": "sport", "group": "sport", "town": f["town"], "venue": f["venue"],
             "date": f["date"]}
        if f.get("time"):
            e["time"] = f["time"]
        e.update({"url": f["url"], "summary": en, "source": SPORT_SOURCE, "highlight": False,
                  "id": hashlib.md5((f["date"] + f["title"] + f["town"]).encode("utf-8")).hexdigest()[:10]})
        cy[en] = cyw
        added.append(e)
    d["events"] = sorted(others + added, key=lambda e: (e.get("date") or "", e.get("time") or "99", e.get("title") or ""))
    return len(added)


def cmd_sport(p, sp, today=None):
    st = load_json(p)
    today = today or dt.date.today().isoformat()
    n = merge_sport(st, load_json(sp), today)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    print(f"{n} sport fixtures merged -> {p}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(0)
    {"extract": cmd_extract, "missing": cmd_missing, "check": cmd_check, "sport": cmd_sport, "apply": cmd_apply}[a[0]](*a[1:])
