"""Tests for amm_whatson.py validation and safe JSON embedding. Run: python3 -m unittest test_amm_whatson"""
import json, unittest
import amm_whatson as m


def ev(**k):
    base = {"title": "Concert", "date": "2026-10-20", "url": "https://example.org/x", "venue": "Hall"}
    base.update(k)
    return base


class Validate(unittest.TestCase):
    def errs(self, *events, news=()):
        return m.validate({"events": list(events), "news": list(news)})

    def test_clean_event_passes(self):
        self.assertEqual(self.errs(ev()), ([], []))

    def test_javascript_url_blocked(self):
        e, _ = self.errs(ev(url="javascript:alert(1)"))
        self.assertTrue(any("not http(s)" in x for x in e))

    def test_data_and_relative_urls_blocked(self):
        self.assertTrue(self.errs(ev(url="data:text/html,hi"))[0])
        self.assertTrue(self.errs(ev(url="/relative"))[0])

    def test_flagurl_checked_too(self):
        self.assertTrue(self.errs(ev(flagUrl="javascript:x"))[0])

    def test_blocked_domain_and_subdomain(self):
        self.assertTrue(self.errs(ev(url="https://parchoward.org.uk/a"))[0])
        self.assertTrue(self.errs(ev(url="https://www.parchoward.org.uk/a"))[0])
        self.assertFalse(self.errs(ev(url="https://notparchoward.org.uk/a"))[0])

    def test_http_is_warning_not_error(self):
        e, w = self.errs(ev(url="http://example.org/"))
        self.assertEqual(e, []); self.assertTrue(w)

    def test_missing_fields_and_bad_dates(self):
        self.assertTrue(self.errs(ev(title=""))[0])
        self.assertTrue(self.errs(ev(url=""))[0])
        self.assertTrue(self.errs(ev(date="13/10/2026"))[0])
        self.assertTrue(self.errs(ev(end_date="2026-10-01"))[0])  # before start
        self.assertFalse(self.errs(ev(end_date="2026-10-25"))[0])

    def test_duplicate_is_warning(self):
        e, w = self.errs(ev(), ev(title=" CONCERT "))
        self.assertEqual(e, []); self.assertTrue(any("duplicate" in x for x in w))

    def test_news_url_checked(self):
        self.assertTrue(self.errs(news=[{"headline": "h", "url": "javascript:1"}])[0])


class ScriptJson(unittest.TestCase):
    def test_no_angle_brackets_survive(self):
        nasty = {"s": "</script><script>alert(1)</script><!--"}
        txt = m.to_script_json(nasty)
        self.assertNotIn("<", txt)
        self.assertEqual(json.loads(txt), nasty)  # still round-trips

    def test_put_obj_roundtrip(self):
        page = 'x<script>const DATA={"a":1};</script>'
        out = m.put_obj(page, "DATA", {"a": "</script>"})
        self.assertEqual(m.find_obj(out, "DATA")[0], {"a": "</script>"})
        self.assertEqual(out.count("</script>"), 1)


class Sport(unittest.TestCase):
    def fixture(self, **k):
        f = {"title": "Tycroes v Pontarddulais", "date": "2026-11-14", "time": "14:30", "venue": "Tycroes (home ground)",
             "town": "Tycroes", "url": "https://allwalessport.co.uk/rugby-union.aspx?cid=19789", "sport": "rugby union",
             "competition": "WRU West: 2 West"}
        f.update(k)
        return f

    def state(self, *events):
        return {"DATA": {"events": list(events), "news": [], "meta": {}}, "CY_SUM": {}}

    def sport(self, *fx, fetched="2026-11-06T07:00:00Z"):
        return {"meta": {"fetched_at": fetched}, "fixtures": list(fx)}

    def test_adds_fixture_with_welsh_summary_and_valid_fields(self):
        st = self.state(ev(date="2026-11-14", summary="x"))
        st["CY_SUM"]["x"] = "y"
        self.assertEqual(m.merge_sport(st, self.sport(self.fixture()), "2026-11-07"), 1)
        e = [x for x in st["DATA"]["events"] if x.get("source") == "All Wales Sport"][0]
        self.assertEqual((e["group"], e["town"], e["time"]), ("sport", "Tycroes", "14:30"))
        self.assertEqual(e["summary"], "Rugby union fixture (WRU West: 2 West).")
        self.assertEqual(st["CY_SUM"][e["summary"]], "Gêm rygbi'r undeb (WRU West: 2 West).")
        self.assertEqual(m.missing(st), [])
        self.assertEqual(m.validate(st["DATA"])[0], [])

    def test_no_time_says_so_in_both_languages(self):
        st = self.state()
        m.merge_sport(st, self.sport(self.fixture(time=None, sport="football", competition="C.thenshire Leagues: Division 1")), "2026-11-07")
        e = st["DATA"]["events"][0]
        self.assertNotIn("time", e)
        self.assertTrue(e["summary"].endswith("Kick-off time not listed."))
        self.assertTrue(st["CY_SUM"][e["summary"]].startswith("Gêm pêl-droed"))

    def test_replaces_last_week_and_skips_games_research_already_lists(self):
        old = dict(ev(title="Tycroes v Old", date="2026-11-14"), source="All Wales Sport")
        found = ev(title="Welsh Premier League: Ammanford vs Briton Ferry", date="2026-11-21", summary="s")
        st = self.state(old, found)
        n = m.merge_sport(st, self.sport(self.fixture(), self.fixture(title="Ammanford v Briton Ferry Llansawel", date="2026-11-21",
                                                                     town="Ammanford", sport="football")), "2026-11-07")
        self.assertEqual(n, 1)
        self.assertEqual(sorted(e["title"] for e in st["DATA"]["events"]),
                         ["Tycroes v Pontarddulais", "Welsh Premier League: Ammanford vs Briton Ferry"])

    def test_stale_file_and_out_of_window_fixtures_change_nothing(self):
        st = self.state(dict(ev(), source="All Wales Sport"))
        self.assertEqual(m.merge_sport(st, self.sport(self.fixture(), fetched="2026-10-20T07:00:00Z"), "2026-11-07"), 0)
        self.assertEqual(len(st["DATA"]["events"]), 1)
        self.assertEqual(m.merge_sport(st, self.sport(self.fixture(date="2026-11-01"), self.fixture(date="2027-06-01")), "2026-11-07"), 0)



class DeadLinks(unittest.TestCase):
    """LINKS.md 3.6: a link the weekly check marked dead is a warning, never an error."""
    def test_dead_link_warns_but_does_not_block(self):
        saved = m.DEAD_LINKS
        m.DEAD_LINKS = {"https://example.org/gone"}
        try:
            errors, warnings = [], []
            m.check_url("https://example.org/gone", "events[0] url", errors, warnings)
            self.assertEqual(errors, [])
            self.assertTrue(any("dead link" in w for w in warnings), warnings)
            errors, warnings = [], []
            m.check_url("https://example.org/fine", "events[0] url", errors, warnings)
            self.assertEqual((errors, warnings), ([], []))
        finally:
            m.DEAD_LINKS = saved

    def test_missing_ledger_means_no_check(self):
        self.assertEqual(m.dead_links("/nonexistent/link-ledger.json"), set())

if __name__ == "__main__":
    unittest.main()
