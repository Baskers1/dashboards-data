"""Find and replace the data blocks inside a weather page's main script.

A data block is a top-level `var NAME=<value>` whose value is a JSON or JS object/array
literal. find_value() returns where the literal starts and ends, so a block can be lifted
out or put back without touching anything around it.
"""
import re


def _literal_end(s, i):
    """Index just past the object/array literal starting at s[i] ('{' or '[')."""
    depth, q, n = 0, None, len(s)
    while i < n:
        c = s[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "\"'`":
            q = c
        elif c in "[{(":
            depth += 1
        elif c in "]})":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unterminated literal")


def find_value(script, name):
    """(start, end) of the literal assigned by the one top-level `var NAME=`."""
    hits = list(re.finditer(r"(?m)(?:^|;)\s*var\s+" + re.escape(name) + r"\s*=\s*", script))
    if len(hits) != 1:
        raise ValueError(f"expected one `var {name}=`, found {len(hits)}")
    start = hits[0].end()
    if script[start] not in "[{":
        raise ValueError(f"`var {name}=` is not an object or array literal")
    return start, _literal_end(script, start)


def lift(script, names):
    """Replace each named block with a {{BLOCK:NAME}} marker. Returns (template, {name: text})."""
    out = {}
    for name in names:
        a, b = find_value(script, name)
        out[name] = script[a:b]
        script = script[:a] + "{{BLOCK:" + name + "}}" + script[b:]
    return script, out


def fill(template, blocks):
    """Put blocks back. Every marker must be filled and every block used."""
    for name, text in blocks.items():
        marker = "{{BLOCK:" + name + "}}"
        if template.count(marker) != 1:
            raise ValueError(f"marker for {name} appears {template.count(marker)} times")
        template = template.replace(marker, text)
    left = re.findall(r"\{\{BLOCK:([A-Z_]+)\}\}", template)
    if left:
        raise ValueError("no data for blocks: " + ", ".join(left))
    return template
