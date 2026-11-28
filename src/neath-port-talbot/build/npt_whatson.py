#!/usr/bin/env python3
"""Helper for the three Neath Port Talbot What's On pages (What's On, Season Ahead, Big Buttons). English only.

Adapted from ammanford/build/amm_whatson.py: the Welsh switch (CY_SUM, missing) is gone and `ingest` is new.
The pages hold their listings inline as JSON in the page script:
  const DATA = {...};   What's On + Season Ahead: {"events":[...],"news":[...],"meta":{...}} (identical in both)
                        Big Buttons: {"updated":"YYYY-MM-DD","events":[...]}  (non-politics events, fewer fields)
State file (state.json): {"DATA": {...}}

Commands:
  unwrap   SAVED.html OUT.html        -> strips the host wrapper the Artifact tool adds to a saved page
  ingest   SCRAPE.json OUT.json [PREV_STATE.json] [--today YYYY-MM-DD]
                                       -> scraper JSON -> state.json; exit 2 ("STOP ... publish nothing") if the
                                          scraper file is stale/empty or fewer than half of the previous state's
                                          still-upcoming scraped events survive
  extract  PAGE.html OUT.json         -> writes {"DATA":...} from a built page
  check    STATE.json                  -> validates; exit 1 if anything would block publishing
  apply    STATE.json WHATSON.html SEASON.html BIG.html OUTDIR [URLS.json]
                                       -> validates, then writes the three updated pages to OUTDIR (same file names).
                                          URLS.json {"whatson":..,"season":..} fills the cross-link between the two.
"""
import argparse, datetime as dt, hashlib, json, os, re, sys
from collections import Counter
from urllib.parse import urlparse

BIG_FIELDS = ["title", "group", "category", "town", "venue", "date", "end_date", "price", "url", "summary", "time", "highlight"]
URL_FIELDS = ["url", "flagUrl", "meetings_url"]
BLOCKED_DOMAINS = {"parchoward.org.uk"}  # spam domain; apply refuses any listing that links to it

# The town buttons on the pages, and the other spellings that fold onto them (like West Herts' TOWN_MAP).
TOWNS = ["Neath", "Port Talbot", "Pontardawe", "Margam", "Aberavon", "Briton Ferry", "Skewen", "Glynneath", "Ystalyfera"]
TOWN_MAP = {
    "neath": "Neath", "neath abbey": "Neath", "cimla": "Neath", "tonna": "Neath", "cadoxton": "Neath", "bryncoch": "Neath",
    "port talbot": "Port Talbot", "taibach": "Port Talbot", "sandfields": "Port Talbot", "baglan": "Port Talbot",
    "cwmafan": "Port Talbot", "cwmavon": "Port Talbot", "bryn": "Port Talbot", "pontrhydyfen": "Port Talbot",
    "pontardawe": "Pontardawe", "margam": "Margam", "margam park": "Margam", "margam country park": "Margam",
    "aberavon": "Aberavon", "aberavon beach": "Aberavon", "aberavon seafront": "Aberavon",
    "briton ferry": "Briton Ferry", "skewen": "Skewen",
    "glynneath": "Glynneath", "pontneddfechan": "Glynneath",
    "ystalyfera": "Ystalyfera",
    # Villages with no button go to the nearest one by road and valley (Sarah, 6 Nov 2026), so their events still show
    # under a town filter: mostly sports clubs' home grounds from All Wales Sport.
    "seven sisters": "Glynneath", "banwen": "Glynneath", "onllwyn": "Glynneath", "resolven": "Glynneath", "cwmgwrach": "Glynneath",
    "crynant": "Neath", "cilfrew": "Neath", "ynysygerwn": "Neath", "aberdulais": "Neath",
    "trebanos": "Pontardawe", "ynysmeudwy": "Pontardawe", "rhos": "Pontardawe", "alltwen": "Pontardawe",
    "godre'r-graig": "Ystalyfera", "godre'r graig": "Ystalyfera", "cwmllynfell": "Ystalyfera", "cwmgors": "Ystalyfera",
    "gwaun-cae-gurwen": "Ystalyfera",
    "llandarcy": "Skewen", "coed darcy": "Skewen", "longford": "Skewen", "coedffranc": "Skewen", "jersey marine": "Skewen",
    "tonmawr": "Port Talbot", "glyncorrwg": "Port Talbot", "croeserw": "Port Talbot", "abergwynfi": "Port Talbot", "cymmer": "Port Talbot",
}
FALLBACK_TOWN = "Neath Port Talbot"  # whole-county events: the What's On and Season pages give them an "Everywhere" button

# scraper source id -> (name, page type). Ids the scraper does not own (a top-up added by the daily task) are carried forward.
# Keys must match scrapekit/scrapers/npt_events.py source ids; anything else is treated as a carried-forward top-up.
SOURCES = {"gwynhall": ("Gwyn Hall, Neath", "listings"), "porttalbot": ("Yr Aelwyd and The Orangery (Ticketsolve)", "listings"),
           "npt-council": ("Neath Port Talbot Council", "council"), "margam": ("Margam Park", "listings"),
           "wherecanwego": ("WhereCanWeGo", "listings"), "pontardawe-arts": ("Pontardawe Arts Centre", "listings"),
           "eventbrite": ("Eventbrite", "listings"), "useyourlocal": ("Pig Iron Tavern (useyourlocal)", "listings"),
           "npt-democracy": ("Neath Port Talbot Council meetings calendar", "council"),
           "neathrfc": ("Neath RFC fixtures", "listings"), "allwalessport": ("All Wales Sport fixtures", "listings")}
RANK = {"venue": 0, "council": 1, "aggregator": 2}
MIN_RUN_DAYS = 3  # fewer consecutive dates are listed one event per day

# `highlight` feeds Season Ahead's "Big nights" and Big Buttons' "Big dates to book". Ammanford and Plymouth leave it to the
# daily task's judgement ("big nights worth booking ahead", "keep <=5% highlight"); here it is a mechanical rule so it is
# never empty or arbitrary: live shows (music, comedy, stage, family; not film, community or council) from the borough's
# three ticketed venues, one pick per show (its earliest upcoming date), at most 5% of all listings, earliest first.
HIGHLIGHT_SOURCES = {"gwynhall", "porttalbot", "pontardawe-arts"}
HIGHLIGHT_GROUPS = {"music", "comedy", "stage", "family"}
HIGHLIGHT_MAX_SHARE = 0.05

GROUP_RULES = [  # first match on category, then on title; default community
    ("politics", r"council meeting|committee|cabinet"), ("film", r"\bfilm|cinema|screening"), ("comedy", r"comed|stand.?up"),
    ("music", r"music|concert|gig\b|band|choir|orchestra|jazz|folk|tribute"),
    ("stage", r"panto|theatre|drama|dance|opera|musical|ballet|\bplay\b"), ("family", r"famil|child|kids|toddler"),
    ("arts", r"exhibit|\bart\b|craft|gallery|museum|workshop"), ("sport", r"sport|football|rugby|\brun\b|swim")]


def find_obj(s, name):
    m = re.search(r'const\s+' + name + r'\s*=\s*', s)
    if not m:
        raise SystemExit(f"const {name} not found")
    obj, end = json.JSONDecoder().raw_decode(s, m.end())
    return obj, m.end(), end


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


WRAP_HEAD, WRAP_TAIL = "<!doctype html><html><head>", "</body></html>"


def unwrap(s):
    """Strip the host wrapper the Artifact tool adds to a saved page. Pages without it are returned as-is."""
    if not s.startswith(WRAP_HEAD) or "</head><body>" not in s:
        return s
    s = s.split("</head><body>", 1)[1]
    s = s[1:] if s.startswith("\n") else s
    s = s.rstrip()
    return s[:-len(WRAP_TAIL)] if s.endswith(WRAP_TAIL) else s


def cmd_unwrap(saved, out):
    write(out, unwrap(read(saved)))
    print(f"unwrapped -> {out}")


def cmd_extract(page, out):
    data, _, _ = find_obj(read(page), "DATA")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"DATA": data}, f, ensure_ascii=False, indent=1)
    print(f"events {len(data['events'])}, news {len(data.get('news', []))} -> {out}")


# ---------- validation ----------

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
        if e.get("town") not in TOWNS and e.get("town") != FALLBACK_TOWN:
            warnings.append(f"{where}: town {e.get('town')!r} is not one of the page's town buttons (shown only when no town is picked)")
        key = (str(e.get("title", "")).strip().lower(), e.get("date"), str(e.get("venue", "")).strip().lower())
        if key in seen:
            warnings.append(f"{where}: duplicate of an earlier listing")
        seen.add(key)
    for i, n in enumerate(d.get("news", [])):
        where = f"news {i} '{str(n.get('headline', ''))[:40]}'"
        if n.get("url"):
            check_url(n["url"], f"{where} url", errors, warnings)
    return errors, warnings


def report(errors, warnings):
    for w in warnings:
        print("WARNING:", w, file=sys.stderr)
    for e in errors:
        print("ERROR:", e, file=sys.stderr)


def cmd_check(p):
    errors, warnings = validate(load_json(p)["DATA"])
    report(errors, warnings)
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


# ---------- ingest ----------

def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", str(t).lower()).removeprefix("the ").strip()


def map_town(t):
    """Fold a scraped town onto a page button; unknown spellings pass through unchanged, a missing one is the whole county."""
    first = re.sub(r"\s+", " ", str(t or "").replace("’", "'")).split(",")[0].strip()
    if not first:
        return FALLBACK_TOWN
    return TOWN_MAP.get(first.lower()) or first


def group_of(category, title):
    for text in (category, title):
        for g, rx in GROUP_RULES:
            if text and re.search(rx, str(text), re.I):
                return g
    return "community"


def spans(dates):
    """Sorted dates -> [(start, end)]: 3+ consecutive days become one run, anything shorter one entry per day."""
    runs = []
    for d in sorted(dates):
        day = dt.date.fromisoformat(d)
        if runs and (day - dt.date.fromisoformat(runs[-1][1])).days == 1:
            runs[-1][1] = d
        else:
            runs.append([d, d])
    out = []
    for a, b in runs:
        if (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days + 1 >= MIN_RUN_DAYS:
            out.append((a, b))
        else:
            out += [(a, a)] + ([(b, b)] if b != a else [])
    return out


def ev_id(date, title, town):
    return hashlib.md5((date + title + town).encode("utf-8")).hexdigest()[:10]


def convert(r, today, skipped):
    """One scraper event -> list of page events (none when it has no usable link, title or date)."""
    url = r.get("url")
    errs = []
    check_url(url, "", errs, [])
    if errs:
        skipped["no valid http(s) link"] += 1
        return []
    title = str(r.get("title") or "").strip()
    dates = {d for d in (r.get("dates") or []) if parse_date(d)}
    if not title or not dates:
        skipped["no title or no valid date"] += 1
        return []
    town = map_town(r.get("town"))
    base = {"title": title, "group": group_of(r.get("category"), title), "town": town, "venue": str(r.get("venue") or "").strip()}
    if r.get("category"):
        base["category"] = str(r["category"]).strip()
    if isinstance(r.get("time"), str) and re.fullmatch(r"\d{2}:\d{2}", r["time"]):
        base["time"] = r["time"]
    if r.get("price"):
        base["price"] = str(r["price"]).strip()
    base["url"] = url.strip()
    base["source"] = r.get("source") or "unknown"
    out = []
    for a, b in spans(dates):
        if b < today:
            continue
        e = dict(base, date=a)
        if b != a:
            e["end_date"] = b
        e["id"] = ev_id(a, title, town)
        out.append((RANK.get(r.get("source_kind"), 3), e))
    return out


def mark_highlights(events):
    """Set highlight=True per the rule above on date-sorted events; clears any highlight carried from a previous state."""
    for e in events:  # top-ups never set highlight, so clearing every event is safe
        e.pop("highlight", None)
    picks, seen = [], set()
    for e in events:
        if e.get("source") in HIGHLIGHT_SOURCES and e.get("group") in HIGHLIGHT_GROUPS and norm(e["title"]) not in seen:
            seen.add(norm(e["title"]))
            picks.append(e)
    for e in picks[:int(len(events) * HIGHLIGHT_MAX_SHARE)]:
        e["highlight"] = True


def upcoming(e, today):
    return (e.get("end_date") or e["date"]) >= today


def overlaps(a, b):
    return a["date"] <= (b.get("end_date") or b["date"]) and b["date"] <= (a.get("end_date") or a["date"])


def survival(prev, new, today):
    """(kept, total): of the previous state's still-upcoming scraped events, how many a new event with the same title overlaps."""
    mine = [e for e in prev if e.get("source") in SOURCES and upcoming(e, today)]
    by = {}
    for e in new:
        by.setdefault(norm(e["title"]), []).append(e)
    kept = sum(1 for e in mine if any(overlaps(e, n) for n in by.get(norm(e["title"]), [])))
    return kept, len(mine)


def ingest(scrape, prev_state, today):
    """Return (state, notes). Raises SystemExit(2) with a STOP message when nothing should be published."""
    meta = scrape.get("meta") or {}
    fetched = parse_date(str(meta.get("fetched_at", ""))[:10])
    if fetched is None or (parse_date(today) - fetched).days > 1:
        raise SystemExit(f"STOP: scraper file is stale or has no fetched_at ({meta.get('fetched_at')!r}); publish nothing.")
    skipped = Counter()
    ranked = [x for r in scrape.get("events") or [] for x in convert(r, today, skipped)]
    if not ranked:
        raise SystemExit("STOP: the scraper file gave no usable upcoming events; publish nothing.")
    new = [e for _, e in ranked]
    prev = ((prev_state or {}).get("DATA") or {}).get("events") or []
    kept, total = survival(prev, new, today)
    if kept * 2 < total:
        raise SystemExit(f"STOP: only {kept} of the previous {total} still-upcoming scraped events survive "
                         f"(fewer than half); publish nothing.")
    ranked += [(3, e) for e in prev if e.get("source") not in SOURCES and upcoming(e, today)]  # carry forward top-ups
    best = {}
    for rank, e in sorted(ranked, key=lambda x: x[0]):  # stable: lower rank wins a duplicate
        k = (e["date"], norm(e["title"]))
        if k in best:
            skipped["duplicate"] += 1
            for f in ("time", "price"):  # the winner keeps its link; it borrows a time or price it lacks
                if f in e and f not in best[k]:
                    best[k][f] = e[f]
            continue
        best[k] = e
    events = sorted(best.values(), key=lambda e: (e["date"], e.get("time") or "99", e["title"]))
    mark_highlights(events)
    origins = {}
    for e in events:
        u = urlparse(e["url"])
        origins.setdefault(e["source"], f"{u.scheme}://{u.netloc}/")
    failed = scrape.get("meta", {}).get("sources_failed") or []
    gaps = [f"{f.get('id', '?')} could not be read today ({str(f.get('error', ''))[:100]})." for f in failed]
    if skipped.get("no valid http(s) link") or skipped.get("no title or no valid date"):
        n = skipped["no valid http(s) link"] + skipped["no title or no valid date"]
        gaps.append(f"{n} scraped listings were left out because they had no usable link or date.")
    tomorrow = (parse_date(today) + dt.timedelta(days=1)).isoformat()
    state = {"DATA": {"events": events, "news": [], "meta": {
        "updated": today, "next_refresh": tomorrow, "gaps": gaps,
        "sources": [{"type": SOURCES[s][1], "name": SOURCES[s][0], "url": u} for s, u in origins.items() if s in SOURCES]}}}
    return state, f"{len(events)} events ({kept}/{total} previous scraped events survive); skipped {dict(skipped)}"


def cmd_ingest(argv):
    ap = argparse.ArgumentParser(prog="ingest")
    ap.add_argument("scrape"); ap.add_argument("out"); ap.add_argument("prev", nargs="?")
    ap.add_argument("--today", default=dt.datetime.now(dt.timezone.utc).astimezone().date().isoformat())
    a = ap.parse_args(argv)
    prev = load_json(a.prev) if a.prev and os.path.exists(a.prev) else None
    state, note = ingest(load_json(a.scrape), prev, a.today)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    print(f"{note} -> {a.out}")


# ---------- apply ----------

def big_events(events):
    return [{k: e[k] for k in BIG_FIELDS if k in e and e[k] not in (None, "", False)} for e in events if e.get("group") != "politics"]


def set_other(s, url):
    out, n = re.subn(r'const OTHER_URL="[^"]*";', lambda m: f'const OTHER_URL="{url}";', s)
    assert n == 1, "OTHER_URL not found"
    return out


def cmd_apply(p, w, se, b, outdir, urls=None):
    d = load_json(p)["DATA"]
    errors, warnings = validate(d)
    report(errors, warnings)
    if errors:
        raise SystemExit(f"refusing to write pages: {len(errors)} errors (see above)")
    u = load_json(urls) if urls and os.path.exists(urls) else {}
    for k, v in u.items():
        e2 = []
        check_url(v, k, e2, [])
        if e2:
            raise SystemExit(f"bad cross-link url in {urls}: {e2[0]}")
    updated = (d.get("meta") or {}).get("updated")
    os.makedirs(outdir, exist_ok=True)
    for src, other in ((w, "season"), (se, "whatson")):
        s = put_obj(read(src), "DATA", d)
        if u.get(other):
            s = set_other(s, u[other])
        write(os.path.join(outdir, os.path.basename(src)), s)
    write(os.path.join(outdir, os.path.basename(b)), put_obj(read(b), "DATA", {"updated": updated, "events": big_events(d["events"])}))
    print(f"wrote 3 pages to {outdir}: {len(d['events'])} events, updated {updated}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(0)
    if a[0] == "ingest":
        cmd_ingest(a[1:])
    else:
        {"unwrap": cmd_unwrap, "extract": cmd_extract, "check": cmd_check, "apply": cmd_apply}[a[0]](*a[1:])
