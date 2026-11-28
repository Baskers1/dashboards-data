"""Turn one hour's scraped data into the data blocks a weather page is built from.

    python3 refresh_data.py <area> <current page.html> <source.json> <out data.json>

  <current page.html>  the page as published now; each block that cannot be refreshed this
                       hour is copied from it unchanged
  <source.json>        the area's file from dashboards-data (data/<area>.json)
  <out data.json>      the blocks, ready for build.py

Weather (LOCS) and air (AIR) come from the area's existing refresh_weather.py, so their
rules stay in one place. An area whose refresh.json says "mode": "page_script" has a
script that builds every block itself; it is run on the current page and the blocks lifted
out (Neath Port Talbot). Rivers, floods and sewage overflows follow the rules in
areas/<area>/refresh.json; before the template these were steps 4 and 5 of the hourly task
prompt, carried out by hand each run.

Prints one line per block (refreshed, or kept and why) and exits:
  0  every block written (some may be kept from the page; see the lines printed)
  2  nothing written: the source is too old, or the weather could not be built
"""
import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
from blocks import _literal_end  # noqa: E402

J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731


def ms(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def ok_data(results, key):
    r = results.get(key) or {}
    return r.get("data") if r.get("ok") else None


def page_blocks(page, names, var_names=None):
    """The current value of each block: the literal after a line that starts `var NAME=`
    (no indent), wherever it is on the page. var_names maps a block to a different variable
    name (Ammanford's Welsh dictionary, block CYW, is `var W=`)."""
    out = {}
    for n in names:
        var = (var_names or {}).get(n, n)
        hits = list(re.finditer(r"(?m)^var " + re.escape(var) + r"=", page))
        if len(hits) != 1:
            raise ValueError(f"expected one line starting 'var {var}=', found {len(hits)}")
        start = hits[0].end()
        out[n] = page[start:_literal_end(page, start)]
    return out


def rivers(old, results, stations, now_ms):
    """New RIVERS: each station's last 96 readings, oldest first. A station whose source
    failed keeps its old readings. Returns (block, notes)."""
    notes, st = [], []
    for s in old["st"]:
        s = dict(s)
        data = ok_data(results, stations.get(s["id"], ""))
        items = (data or {}).get("items") or []
        if not items:
            notes.append(f"river {s['id']} ({s['r']}, {s['n']}): source failed or empty, kept old readings")
        else:
            items = sorted(items, key=lambda i: i["dateTime"])[-96:]
            s["v"] = [i["value"] for i in items]
            s["t"] = ms(items[-1]["dateTime"])
        st.append(s)
    return {**old, "asofMs": now_ms, "st": st}, notes


def first_sentence(text):
    text = " ".join((text or "").split())
    return re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0] if text else ""


def floods(old, results, key, now_ms):
    data = ok_data(results, key)
    if data is None or not isinstance(data.get("items"), list):
        return old, [f"FLOODS kept: source {key} failed"]
    items = []
    for it in data["items"]:
        area = it.get("description") or (it.get("floodArea") or {}).get("label") or it.get("eaAreaName") or "Unnamed area"
        msg = first_sentence(it.get("message"))
        items.append([str(it.get("severity") or "Flood alert"), f"{area} - {msg}" if msg else str(area)])
    return {"asofMs": now_ms, "items": items}, []


def spills(old, results, cfg, areas):
    data = ok_data(results, cfg["source"])
    if data is None or not isinstance(data.get("features"), list):
        return old, [f"SPILLS kept: source {cfg['source']} failed or has no features"]
    keep = re.compile(cfg["keep"], re.I)
    rows, newest, notes = [], 0, []
    for feat in data["features"]:
        a = feat.get("attributes") or {}
        if not keep.search(a.get("ReceivingWaterCourse") or ""):
            continue
        status = a.get("Status")
        if status == 1:
            start, end = a.get("StatusStart"), None
        elif status == 0:
            start, end = a.get("LatestEventStart"), a.get("LatestEventEnd")
        else:
            start, end = None, None
        rows.append([a["Id"], status, start, end, a.get("Latitude"), a.get("Longitude"), a.get("ReceivingWaterCourse")])
        newest = max(newest, a.get("LastUpdated") or 0)
        if a["Id"] not in areas:
            notes.append(f"new overflow {a['Id']} at {a.get('Latitude')}, {a.get('Longitude')}: not named in AREAS")
    if not rows:
        return old, [f"SPILLS kept: no overflows on {cfg['keep']} after filtering, which is unusual"]
    return {"asofMs": newest, "f": rows}, notes


def load_weather_module(path):
    spec = importlib.util.spec_from_file_location("area_refresh_weather", REPO / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def refresh(area, page, src, now):
    """(blocks or None, lines). None means nothing should be written."""
    cfg = json.loads((HERE / "areas" / area / "refresh.json").read_text(encoding="utf-8"))
    settings = json.loads((HERE / "areas" / area / "settings.json").read_text(encoding="utf-8"))
    names = settings["data_blocks"]
    var_names = cfg.get("var_names", {})
    seeded = []
    try:
        old_text = page_blocks(page, names, var_names)
    except ValueError as exc:
        # The live page is still the area's pre-template page (East Kent's first run on the
        # template): start from a template page built from the area's seed data instead. Every
        # block is then rebuilt from this hour's sources; the seed only stands in for a block
        # whose source fails on that first run.
        if not cfg.get("seed"):
            raise
        import build
        page, _ = build.build(area, HERE / cfg["seed"])
        old_text = page_blocks(page, names, var_names)
        seeded = [f"current page is not a template page ({exc}); started from the seed {cfg['seed']}"]
    old = {n: json.loads(t) for n, t in old_text.items()}
    results, lines = src["results"], []
    fetched = datetime.fromisoformat(src["fetched_at"])
    if now - fetched > timedelta(hours=cfg["max_age_hours"]):
        return None, [f"source fetched {src['fetched_at']} is more than {cfg['max_age_hours']} h old: nothing written"]
    now_ms = int(fetched.timestamp() * 1000)  # when the data was fetched, not when this ran
    out = dict(old_text)

    wx = load_weather_module(cfg["weather_module"])
    if cfg.get("mode") == "page_script":
        # The area's own refresh_weather.py already builds every block (NPT: LOCS, RIVERS,
        # FLOODS, OUTLOOK, AIR) and leaves a block whose source failed as it was. Run it
        # on the current page and lift the finished blocks out.
        html, done, notes = wx.refresh(page, src, now)
        if "LOCS" not in done:
            return None, notes + ["weather could not be built: nothing written"]
        new = page_blocks(html, names, var_names)
        import build
        extra = build.welsh_extra(settings, area)
        if extra and "CYW" in new:
            # build.py adds the shared Welsh lines and lang_extra (template-only lines such as
            # the title) to the dictionary; take them out again so the data holds only what the
            # area makes. Only lines still exactly as build.py put them: Welsh the area's own
            # script wrote for the same English stays.
            cyw = json.loads(new["CYW"])
            for k, v in extra.items():
                if cyw.get(k) == v:
                    del cyw[k]
            new["CYW"] = J(cyw)
        for n in names:
            changed = n in done or json.loads(new[n]) != old[n]
            lines.append(f"{n} refreshed" if changed else f"{n} kept")
        return new, lines + notes + seeded
    today = now.astimezone(wx.LON).date().isoformat()
    try:
        out["LOCS"] = J(wx.build_locs(old["LOCS"], results, today, wx.stamp(wx.fetched_of(src)), now))
        lines.append("LOCS refreshed")
    except ValueError as exc:
        return None, [f"weather could not be built ({exc}): nothing written"]
    air = wx.build_air(old["AIR"], results)
    if air is None:
        lines.append("AIR kept: a Defra series failed or every reading was missing")
    else:
        out["AIR"] = J(air)
        lines.append("AIR refreshed")

    for name, fn in (("RIVERS", lambda: rivers(old["RIVERS"], results, cfg["rivers"], now_ms)),
                     ("FLOODS", lambda: floods(old["FLOODS"], results, cfg["floods"], now_ms)),
                     ("SPILLS", lambda: spills(old["SPILLS"], results, cfg["spills"], json.loads(
                         (HERE / "areas" / area / "static" / "AREAS.js").read_text(encoding="utf-8"))))):
        block, notes = fn()
        if block is not old[name]:
            out[name] = J(block)
            lines.append(f"{name} refreshed")
        lines.extend(notes)
    return out, lines


def main(argv):
    if len(argv) != 5:
        raise SystemExit(__doc__)
    area, page_p, src_p, out_p = argv[1:5]
    src = json.loads(Path(src_p).read_text(encoding="utf-8"))
    print(f"source fetched_at {src['fetched_at']}; failed: {src.get('sources_failed')}")
    out, lines = refresh(area, Path(page_p).read_text(encoding="utf-8"), src, datetime.now(timezone.utc))
    for line in lines:
        print(line)
    if out is None:
        return 2
    Path(out_p).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
