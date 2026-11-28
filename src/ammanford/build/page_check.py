#!/usr/bin/env python3
"""Browser checks for Community Watch pages, before and after a data.json split.

  probe  PAGE.html ITEMS GROUPS   -> loads the page (and the data.json beside it, if any) over local
                                     http, and exits 1 unless ITEMS.length and GROUPS.length match,
                                     cards render, and the page throws no errors. This is the check
                                     that catches a split which silently dropped data.
  digest PAGE.html OUT.json        -> clicks every mode x town x view (x language) and records a hash of
                                     the visible text of each combination. Two pages with the same
                                     digest look the same to a reader. The clock is fixed at
                                     2026-11-02 09:00 London so "days left" text does not drift.

Needs playwright with chromium installed. Runs with python3 -I.
"""
import contextlib, functools, hashlib, http.server, json, os, sys, threading

from playwright.sync_api import sync_playwright

FIXED_NOW = "2026-11-02T09:00:00Z"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser closed early (missing hero photos); not a page problem


@contextlib.contextmanager
def served(page):
    """Serve the page's folder on a free localhost port; yield the page URL. Pages fetch data.json,
    which file:// URLs cannot do."""
    folder, name = os.path.split(os.path.abspath(page))
    handler = functools.partial(Quiet, directory=folder)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_port}/{name}"
    finally:
        srv.shutdown()


@contextlib.contextmanager
def opened(page):
    with served(page) as url, sync_playwright() as pw:
        browser = pw.chromium.launch()
        p = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        p.on("pageerror", lambda e: errors.append(str(e)))
        # Script errors only: hero photos and web fonts are not served locally, and their failed
        # loads say nothing about whether the page's data and code are intact.
        p.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text
             and errors.append(m.text))
        p.clock.install(time=FIXED_NOW)
        p.goto(url, wait_until="networkidle")
        try:
            yield p, errors
        finally:
            browser.close()


def cmd_probe(page, want_items, want_groups):
    with opened(page) as (p, errors):
        got = p.evaluate("() => [typeof ITEMS === 'undefined' ? -1 : ITEMS.length,"
                         " typeof GROUPS === 'undefined' ? -1 : GROUPS.length,"
                         " document.querySelectorAll('main .card').length]")
    items, groups, cards = got
    problems = []
    if items != int(want_items):
        problems.append(f"ITEMS {items}, expected {want_items}")
    if groups != int(want_groups):
        problems.append(f"GROUPS {groups}, expected {want_groups}")
    if cards < 1:
        problems.append("no cards rendered")
    problems += [f"page error: {e[:160]}" for e in errors]
    print(f"probe {page}: ITEMS {items}, GROUPS {groups}, cards {cards}")
    for x in problems:
        print("FAIL:", x)
    sys.exit(1 if problems else 0)


def visible_text(p):
    return p.evaluate("() => (document.querySelector('main') || document.body).innerText")


def cmd_digest(page, out):
    result = {}
    with opened(page) as (p, errors):
        # Clicked through the DOM rather than as a user would: on three pages the town buttons sit
        # inside a collapsed "More filters" panel, and the digest is about content, not layout.
        # Both display modes are walked explicitly, because pages remember or default to either.
        click = lambda sel: p.evaluate("sel => document.querySelector(sel).click()", sel)
        datas = lambda sel, key: p.eval_on_selector_all(sel, f"els => els.map(e => e.dataset.{key})")
        modes = {"std": ("#areas [data-area]", ".viewtabs [data-view]", "view"),
                 "big": ("#bigarea [data-area]", "#bigbar [data-big]", "big")}
        for lang in datas("[data-lang]", "lang") or [""]:
            if lang:
                click(f"[data-lang='{lang}']")
            for mode, (town_sel, view_sel, key) in modes.items():
                click(f"#m-{mode}")
                for town in datas(town_sel, "area"):
                    click(f"{town_sel.split(' ')[0]} [data-area='{town}']")
                    for v in datas(view_sel, key):
                        click(f"{view_sel.split(' ')[0]} [data-{key}='{v}']")
                        result[f"{lang or 'en'} | {mode} | {town} | {v}"] = hashlib.sha256(
                            visible_text(p).encode()).hexdigest()[:16]
    if errors:
        result["_errors"] = errors
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"digest {page}: {len(result) - ('_errors' in result)} combinations, {len(errors)} errors -> {out}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("probe", "digest"):
        print(__doc__)
        sys.exit(0)
    {"probe": cmd_probe, "digest": cmd_digest}[a[0]](*a[1:])
