#!/usr/bin/env python3
"""Add a link-scheme guard to the Ammanford dashboard pages.

Every link the page builds from data goes through safeUrl(), which lets only
http(s) URLs through and turns anything else (javascript:, data:, vbscript:...)
into "#". Links built by string concatenation without esc() are also escaped,
so a quote in a scraped URL can no longer break out of the href attribute.

Usage: harden_links.py IN.html OUT.html     (idempotent: a second run changes nothing)
"""
import re, sys

GUARD = 'const safeUrl=u=>{u=String(u??"").trim();return /^https?:\\/\\//i.test(u)?u:"#"};'

def harden(s):
    if "const safeUrl=" in s:
        return s, 0
    # 1. define safeUrl straight after the page's esc() helper
    m = re.search(r'const esc\s*=\s*s\s*=>[^\n]*?\}\[c\]\)\);', s)
    if not m:
        raise SystemExit("esc() helper not found - page layout changed, patch by hand")
    s = s[:m.end()] + GUARD + s[m.end():]
    n = 0
    # 2. template-literal pages: href="${esc(X)}"  ->  href="${esc(safeUrl(X))}"
    s, k = re.subn(r'href="\$\{esc\((?!safeUrl)([^}]*?)\)\}"', r'href="${esc(safeUrl(\1))}"', s); n += k
    # 3. concatenation pages, escaped:   href="' + esc(X) + '"
    s, k = re.subn(r"href=\"' \+ esc\((?!safeUrl)([\w.\[\]]+)\) \+ '\"", r"href=\"' + esc(safeUrl(\1)) + '\"", s); n += k
    # 4. concatenation pages, unescaped: href="' + X + '"
    s, k = re.subn(r"href=\"' \+ ([\w.\[\]]+) \+ '\"", r"href=\"' + esc(safeUrl(\1)) + '\"", s); n += k
    return s, n

if __name__ == "__main__":
    src, dst = sys.argv[1:3]
    s, n = harden(open(src, encoding="utf-8").read())
    with open(dst, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"{src}: {n} links guarded")
