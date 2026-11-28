"""Tests for npt_whatson.py: ingest, survival gate, town/group mapping, validation, apply. Run: python3 -m pytest test_npt_whatson.py"""
import copy, json, os, subprocess, sys
import pytest
import npt_whatson as m

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-11-03"
FIXTURE = os.path.join(HERE, "fixtures", "scrape.json")


def raw(i="x", title="Test Show", dates=("2026-11-10",), url="https://example.org/e", **k):
    base = {"id": i, "title": title, "dates": list(dates), "time": "19:30", "venue": "Hall", "town": "Neath", "url": url,
            "booking_url": None, "price": None, "category": None, "source": "gwynhall", "source_kind": "venue"}
    base.update(k)
    return base


def scrape(*events, fetched="2026-11-03T06:58:00Z", failed=()):
    return {"meta": {"area": "neath-port-talbot", "fetched_at": fetched, "sources_ok": [], "sources_failed": list(failed)}, "events": list(events)}


def run(*events, prev=None, today=TODAY, **kw):
    return m.ingest(scrape(*events, **kw), prev, today)[0]["DATA"]["events"]


def state(*events):
    return {"DATA": {"events": list(events)}}


def prev_ev(title, date="2026-11-10", source="gwynhall", **k):
    return dict({"title": title, "date": date, "source": source, "url": "https://example.org/p", "town": "Neath"}, **k)


# ---------- ingest ----------

def test_fixture_ingests_and_validates():
    st, note = m.ingest(json.load(open(FIXTURE)), None, TODAY)
    assert m.validate(st["DATA"])[0] == []
    assert len(st["DATA"]["events"]) == 26 and "skipped" in note


def test_links_stay_the_events_own_and_no_invented_fields():
    (e,) = run(raw(url="https://example.org/own", booking_url="https://tickets.example.org/b"))
    assert e["url"] == "https://example.org/own"
    assert "booking_url" not in e and "summary" not in e and "highlight" not in e and "price" not in e


def test_highlight_rule_main_venue_live_shows_one_pick_per_show_capped_at_five_percent():
    fill = [raw(f"f{i}", f"Council item {i}", dates=("2026-11-%02d" % (4 + i % 20),), source="npt-council", source_kind="council") for i in range(94)]
    shows = [raw("a", "Tribute Night", dates=("2026-11-10", "2026-11-17"), category="Music", source="pontardawe-arts"),
             raw("b", "Comedy Gig", dates=("2026-11-12",), category="Comedy"),
             raw("c", "A Film", dates=("2026-11-11",), category="cinema"),             # film: not a big night
             raw("d", "Tea Social", dates=("2026-11-13",), category="Community"),    # community: no
             raw("e", "Council Panto", dates=("2026-11-14",), category="Panto", source="npt-council", source_kind="council"),  # not a main venue
             raw("f", "Later Musical", dates=("2026-12-20",), category="Musical", source="porttalbot")]
    evs = run(*fill, *shows)
    hl = [(e["title"], e["date"]) for e in evs if e.get("highlight")]
    assert hl == [("Tribute Night", "2026-11-10"), ("Comedy Gig", "2026-11-12"), ("Later Musical", "2026-12-20")]  # 100 events -> cap 5, 3 qualify
    capped = run(*fill, *[raw(f"s{i}", f"Show {i}", dates=("2026-11-%02d" % (5 + i),), category="Music") for i in range(8)])
    assert [e["title"] for e in capped if e.get("highlight")] == [f"Show {i}" for i in range(5)]  # 102 events -> cap 5, earliest first


def test_highlight_is_recomputed_not_carried_from_previous_state():
    old = prev_ev("Old Show", source="topup: The Gnoll", highlight=True, group="community", date="2026-11-20")
    evs = run(*[raw(f"n{i}", f"Council {i}", source="npt-council", source_kind="council") for i in range(40)], raw("x", "New", category="Music"),
              prev=state(old))
    assert [e["title"] for e in evs if e.get("highlight")] == ["New"]  # Old Show is carried forward as community: its stale flag is dropped


@pytest.mark.parametrize("url", [None, "", "javascript:alert(1)", "/relative", "ftp://x.org/a", "data:text/html,hi", "https://"])
def test_event_without_valid_http_url_is_skipped(url):
    assert run(raw(), raw("y", "Other", url=url)) and len(run(raw(), raw("y", "Other", url=url))) == 1


def test_event_without_valid_date_is_skipped_and_bad_dates_ignored():
    evs = run(raw(dates=["15/11/2026"]), raw("b", "Two", dates=["junk", "2026-11-12"]), raw("c", "Three", dates=[]))
    assert [e["title"] for e in evs] == ["Two"] and evs[0]["date"] == "2026-11-12"


def test_past_events_dropped_and_running_ones_kept():
    evs = run(raw(dates=["2026-10-01"]), raw("b", "Run", dates=["2026-10-30", "2026-10-31", "2026-11-01", "2026-11-04"]),
              raw("c", "Today", dates=[TODAY]))
    assert sorted(e["title"] for e in evs) == ["Run", "Today"]
    assert [e["date"] for e in evs if e["title"] == "Run"] == ["2026-11-04"]  # the non-consecutive tail is a single day


def test_three_consecutive_days_make_a_run_fewer_do_not():
    run3 = run(raw(dates=["2026-12-01", "2026-12-02", "2026-12-03"]))
    assert len(run3) == 1 and run3[0]["date"] == "2026-12-01" and run3[0]["end_date"] == "2026-12-03"
    two = run(raw(dates=["2026-12-01", "2026-12-02"]))
    assert [e["date"] for e in two] == ["2026-12-01", "2026-12-02"] and all("end_date" not in e for e in two)
    gap = run(raw(dates=["2026-12-01", "2026-12-08", "2026-12-15"]))
    assert len(gap) == 3


def test_id_is_md5_of_date_title_town():
    (e,) = run(raw(title="Test Show", town="Neath"))
    assert e["id"] == m.hashlib.md5("2026-11-10Test ShowNeath".encode()).hexdigest()[:10]


def test_bad_time_dropped_event_kept():
    (e,) = run(raw(time="7pm"))
    assert "time" not in e


def test_duplicate_prefers_venue_over_aggregator_and_borrows_time():
    agg = raw("a", "The Test Show", url="https://agg.example.org/1", time="20:00", price="£5", source="wherecanwego", source_kind="aggregator")
    ven = raw("v", "Test Show", url="https://venue.example.org/1", time=None, price=None)
    (e,) = run(agg, ven)
    assert e["url"] == "https://venue.example.org/1" and e["time"] == "20:00" and e["price"] == "£5"


def test_stale_scraper_file_stops():
    with pytest.raises(SystemExit, match="publish nothing"):
        run(raw(), fetched="2026-10-30T06:58:00Z")
    with pytest.raises(SystemExit, match="stale"):
        run(raw(), fetched="")


def test_empty_result_stops():
    with pytest.raises(SystemExit, match="publish nothing"):
        run(raw(url=None))


def test_failed_sources_reported_as_gaps():
    st, _ = m.ingest(scrape(raw(), failed=[{"id": "margam", "error": "HTTP 503"}]), None, TODAY)
    assert any("margam could not be read" in g and "503" in g for g in st["DATA"]["meta"]["gaps"])


# ---------- towns and groups ----------

@pytest.mark.parametrize("raw_town,want", [
    ("neath", "Neath"), ("Neath Abbey", "Neath"), ("Cimla", "Neath"), ("Port Talbot, Neath Port Talbot", "Port Talbot"),
    ("Taibach", "Port Talbot"), ("Cwmafan", "Port Talbot"), ("Aberavon Beach", "Aberavon"), ("Margam Park", "Margam"),
    ("  Briton   Ferry ", "Briton Ferry"), ("Ystalyfera", "Ystalyfera"), ("Pontneddfechan", "Glynneath"),
    ("Resolven", "Glynneath"), ("Swansea", "Swansea"), ("", "Neath Port Talbot"), (None, "Neath Port Talbot")])
def test_map_town(raw_town, want):
    assert m.map_town(raw_town) == want


def test_every_mapped_town_is_a_button_or_passes_through():
    assert {v for v in m.TOWN_MAP.values()} <= set(m.TOWNS)


@pytest.mark.parametrize("cat,title,want", [
    ("Cinema", "X", "film"), ("Music", "X", "music"), (None, "Test Panto", "stage"), ("Children", "X", "family"),
    ("Exhibition", "X", "arts"), (None, "Just a coffee morning", "community"), ("Council meeting", "X", "politics")])
def test_group_of(cat, title, want):
    assert m.group_of(cat, title) == want


# ---------- survival gate ----------

def full_prev(n=4):
    return state(*[prev_ev(f"Show {i}") for i in range(n)])


def test_gate_stops_when_fewer_than_half_survive():
    with pytest.raises(SystemExit, match="only 1 of the previous 4.*publish nothing"):
        run(raw(title="Show 0"), raw("z", "Brand new"), prev=full_prev())


def test_gate_passes_at_exactly_half_and_above():
    assert run(raw(title="Show 0"), raw("b", "Show 1"), prev=full_prev())
    assert run(*[raw(str(i), f"Show {i}") for i in range(4)], prev=full_prev())


def test_gate_counts_runs_by_overlap_and_ignores_past_and_topups():
    prev = state(prev_ev("Long Run", date="2026-10-01", end_date="2026-12-01"),   # started before today, still on
                 prev_ev("Old", date="2026-10-01"),                                 # past: not counted
                 prev_ev("Gnoll Talk", source="tinyfish-topup"))                    # not a scraper source: not counted
    assert run(raw(title="Long Run", dates=["2026-11-05", "2026-11-06", "2026-11-07"]), prev=prev)


def test_gate_skipped_without_previous_state():
    assert run(raw(), prev=None) and run(raw(), prev=state())


def test_topups_are_carried_forward_when_still_upcoming():
    prev = state(prev_ev("Gnoll Talk", source="tinyfish-topup", venue="The Gnoll"), prev_ev("Gone Talk", date="2026-10-02", source="tinyfish-topup"))
    titles = [e["title"] for e in run(raw(), prev=prev)]
    assert "Gnoll Talk" in titles and "Gone Talk" not in titles


def test_cli_exit_codes_and_no_output_on_stop(tmp_path):
    sc, pv, out = tmp_path / "s.json", tmp_path / "p.json", tmp_path / "o.json"
    sc.write_text(json.dumps(scrape(raw(title="Show 0"))))
    pv.write_text(json.dumps(full_prev()))
    r = subprocess.run([sys.executable, os.path.join(HERE, "npt_whatson.py"), "ingest", str(sc), str(out), str(pv), "--today", TODAY], capture_output=True, text=True)
    assert r.returncode != 0 and "publish nothing" in r.stderr and not out.exists()
    pv.write_text(json.dumps(state()))
    r = subprocess.run([sys.executable, os.path.join(HERE, "npt_whatson.py"), "ingest", str(sc), str(out), str(pv), "--today", TODAY], capture_output=True, text=True)
    assert r.returncode == 0 and out.exists()


# ---------- validation, big events, apply ----------

def test_validate_blocks_bad_links_and_warns_on_unknown_town():
    e = {"title": "T", "date": "2026-11-10", "url": "javascript:x", "town": "Resolven"}
    errs, warns = m.validate({"events": [e]})
    assert any("not http(s)" in x for x in errs) and any("Resolven" in w for w in warns)
    assert m.validate({"events": [dict(e, url="https://example.org", town="Neath")]}) == ([], [])


def test_big_events_drops_politics_and_empty_fields():
    big = m.big_events([{"title": "A", "group": "politics", "date": "d"}, {"title": "B", "group": "music", "date": "d", "price": "", "source": "x"}])
    assert big == [{"title": "B", "group": "music", "date": "d"}]


def test_script_json_has_no_angle_brackets_and_round_trips():
    nasty = {"s": "</script><script>alert(1)</script><!--"}
    txt = m.to_script_json(nasty)
    assert "<" not in txt and json.loads(txt) == nasty
    page = 'x<script>const DATA={"a":1};</script>'
    assert m.find_obj(m.put_obj(page, "DATA", nasty), "DATA")[0] == nasty


SHELLS = os.path.join(HERE, "shells")


@pytest.mark.skipif(not os.path.exists(os.path.join(SHELLS, "big.html")), reason="shells not built")
def test_apply_writes_three_pages_and_cross_links(tmp_path):
    st = tmp_path / "state.json"
    s, _ = m.ingest(json.load(open(FIXTURE)), None, TODAY)
    st.write_text(json.dumps(s))
    urls = tmp_path / "urls.json"
    urls.write_text(json.dumps({"whatson": "https://claude.ai/artifact/AAA", "season": "https://claude.ai/artifact/BBB"}))
    out = tmp_path / "out"
    m.cmd_apply(str(st), *(os.path.join(SHELLS, f) for f in ("whatson.html", "season.html", "big.html")), str(out), str(urls))
    wo, se, bg = (open(out / f, encoding="utf-8").read() for f in ("whatson.html", "season.html", "big.html"))
    assert m.find_obj(wo, "DATA")[0] == m.find_obj(se, "DATA")[0] == s["DATA"]
    assert 'const OTHER_URL="https://claude.ai/artifact/BBB";' in wo and 'const OTHER_URL="https://claude.ai/artifact/AAA";' in se
    big = m.find_obj(bg, "DATA")[0]
    assert big["updated"] == TODAY and len(big["events"]) == sum(1 for e in s["DATA"]["events"] if e["group"] != "politics")
    assert "</script><script" not in bg


@pytest.mark.skipif(not os.path.exists(os.path.join(SHELLS, "big.html")), reason="shells not built")
def test_apply_refuses_errors_and_bad_crosslink(tmp_path):
    bad = copy.deepcopy(m.ingest(json.load(open(FIXTURE)), None, TODAY)[0])
    bad["DATA"]["events"][0]["url"] = "javascript:alert(1)"
    st = tmp_path / "state.json"; st.write_text(json.dumps(bad))
    sh = [os.path.join(SHELLS, f) for f in ("whatson.html", "season.html", "big.html")]
    with pytest.raises(SystemExit, match="refusing"):
        m.cmd_apply(str(st), *sh, str(tmp_path / "o"))
    bad["DATA"]["events"][0]["url"] = "https://example.org/ok"; st.write_text(json.dumps(bad))
    u = tmp_path / "u.json"; u.write_text(json.dumps({"season": "javascript:x"}))
    with pytest.raises(SystemExit, match="bad cross-link"):
        m.cmd_apply(str(st), *sh, str(tmp_path / "o"), str(u))


def test_sources_cover_every_scraper_source_id():
    # A scraper id missing here is carried forward forever as a top-up and skips the survival gate.
    import re, pathlib
    src = (pathlib.Path(__file__).resolve().parents[2] / "scrapekit/scrapers/npt_events.py").read_text()
    block = src[src.index("SOURCES = ["):]
    ids = set(re.findall(r'^\s*\("([a-z-]+)",', block[:block.index("\n]")], re.M))
    assert len(ids) >= 8, ids
    import npt_whatson
    missing = {i for i in ids if i not in npt_whatson.SOURCES}
    assert not missing, missing


def test_villages_fold_onto_the_nearest_town_button():
    got = {v: m.map_town(v) for v in ("Seven Sisters", "Crynant", "Trebanos", "Godre'r-graig", "Godre’r-graig", "Llandarcy", "Tonmawr")}
    assert got == {"Seven Sisters": "Glynneath", "Crynant": "Neath", "Trebanos": "Pontardawe", "Godre'r-graig": "Ystalyfera",
                   "Godre’r-graig": "Ystalyfera", "Llandarcy": "Skewen", "Tonmawr": "Port Talbot"}
    assert all(t in m.TOWNS for t in m.TOWN_MAP.values())
