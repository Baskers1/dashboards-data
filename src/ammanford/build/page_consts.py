"""Read top-level `const NAME = <literal>` declarations (at column 0; indented ones are function locals) from a dashboard page script.

Ammanford's pages hold their data as strict JSON, which amm_whatson.find_obj reads directly.
East Kent, Tayside and West Herts Community Watch hold it as JavaScript literals (unquoted keys,
single quotes, references to URL constants such as IOTN_SEP5), which JSON cannot parse.

find_decl() locates a declaration's literal text and its span in the page, in Python, so offsets
are Python string offsets (Node's are UTF-16 and would drift on emoji). eval_consts() evaluates the
page's declarations in order with Node, so a literal may refer to an earlier constant, and returns
only constants that survive a JSON round trip unchanged -- anything holding a RegExp, a function or
`undefined` is refused, because it cannot move to data.json.
"""
import json, os, re, subprocess

DECL = re.compile(r"^const\s+([A-Za-z_$][\w$]*)\s*=\s*", re.M)
OPEN, CLOSE = "([{", ")]}"
JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_consts.js")


def _end_of_expr(s, i):
    """Index just past the expression starting at s[i]: stops at ';' or a newline at depth 0."""
    depth, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "\"'`":
            q, i = c, i + 1
            while i < n and s[i] != q:
                if s[i] == "\\":
                    i += 1
                elif q == "`" and s.startswith("${", i):
                    j = _end_of_expr(s, i + 2)  # stops at the matching '}' (depth goes negative)
                    i = j
                i += 1
            if i >= n:
                raise ValueError("unterminated string")
        elif s.startswith("//", i):
            if depth == 0:
                return i  # the comment is not part of the value (a kept comment would eat the closing ")")
            i = s.find("\n", i)
            if i < 0:
                return n
            continue
        elif s.startswith("/*", i):
            i = s.index("*/", i) + 1
        elif c in OPEN:
            depth += 1
        elif c in CLOSE:
            depth -= 1
            if depth < 0:
                return i
        elif depth == 0 and c in ";\n":
            return i
        i += 1
    return n


def find_decl(s, name):
    """(literal_text, start, end) of `const name = ...` in s. SystemExit if absent."""
    m = re.search(r"^const\s+" + re.escape(name) + r"\s*=\s*", s, re.M)
    if not m:
        raise SystemExit(f"const {name} not found")
    end = _end_of_expr(s, m.end())
    return s[m.end():end].rstrip(), m.end(), end


def script_of(page_text):
    """The page's main inline script (the largest <script> block)."""
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", page_text, re.S)
    if not blocks:
        raise SystemExit("no inline <script> in page")
    return max(blocks, key=len)


def all_decls(js):
    """[(name, literal_text)] for every top-level const, in page order. Declarations the scanner
    cannot read (a regex literal holding a quote, say) are left out: they are code, not data, and
    eval_consts still fails loudly if a wanted constant is among them."""
    out = []
    for m in DECL.finditer(js):
        try:
            out.append((m.group(1), js[m.end():_end_of_expr(js, m.end())].rstrip()))
        except ValueError:
            continue
    return out


def eval_consts(page_text, names):
    """{name: value} for NAMES, evaluated by Node in page order. SystemExit naming any constant that
    is missing, fails to evaluate, or does not survive a JSON round trip."""
    decls = all_decls(script_of(page_text))
    r = subprocess.run(["node", JS], input=json.dumps({"decls": decls, "want": names}),
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"page_consts.js failed: {r.stderr.strip()[:400]}")
    res = json.loads(r.stdout)
    if res["bad"]:
        raise SystemExit("cannot move to data.json: " + "; ".join(f"{k}: {v}" for k, v in res["bad"].items()))
    return res["values"]
