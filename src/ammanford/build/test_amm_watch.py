"""Tests for amm_watch.py (Community Watch / Consultation Watch). Run: python3 -m unittest test_amm_watch"""
import json, os, shutil, tempfile, unittest
import amm_watch as m


def citem(**k):
    base = {"id": "a1", "at": ["ammanford"], "title": "Hall fair", "status": "open", "deadline": "2026-11-01",
            "url": "https://example.org/a", "aff": ["Older people"], "cy": {"title": "Ffair", "aff": ["Pobl hŷn"]}}
    base.update(k)
    return base


def community(**k):
    st = {"ITEMS": [citem()], "GROUPS": [{"n": "Club", "area": "betws", "url": "https://example.org/g", "cy": {}}],
          "SOON": ["Later"], "SOON_CY": ["Wedyn"], "WATCH": [["Council", "https://example.org/w"]],
          "WATCH_CY": ["Cyngor"], "LAST_CHECKED": "2026-10-14"}
    st.update(k)
    return st


def oitem(**k):
    base = {"id": "o1", "title": "Bus changes", "status": "open", "deadline": "2026-11-01",
            "url": "https://example.org/o", "a": {"people": [["Riders", 1]]},
            "cy": {"title": "Bysiau", "a": {"people": ["Teithwyr"]}}}
    base.update(k)
    return base


def consultation(**k):
    st = {"ITEMS": [oitem()], "PETITIONS": [{"date": "2026-03-16", "url": "https://example.org/p", "cy": {}}],
          "WATCH": [["Council", "https://example.org/w"]], "WATCH_CY": {"https://example.org/w": "Cyngor"},
          "COLLECTED": "14 October 2026", "COLLECTED_CY": "14 Hydref 2026", "WATCH_NOTE": "", "WATCH_NOTE_CY": "",
          "EMPTY_CHARITY": "", "EMPTY_CHARITY_CY": "", "STATUS": {"o1": "Decides soon"}, "PLACE": {"o1": "ammanford"}}
    st.update(k)
    return st


class Community(unittest.TestCase):
    def v(self, st):
        return m.validate("community", st)

    def test_clean_passes(self):
        self.assertEqual(self.v(community()), ([], []))

    def test_bad_links_block(self):
        for u in ("javascript:alert(1)", "data:text/html,x", "/rel", "https://www.parchoward.org.uk/x"):
            self.assertTrue(self.v(community(ITEMS=[citem(url=u)]))[0], u)
        self.assertTrue(self.v(community(WATCH=[["x", "javascript:x"]]))[0])
        g = community(); g["GROUPS"][0]["url"] = "javascript:x"
        self.assertTrue(self.v(g)[0])

    def test_ids_status_dates_areas(self):
        self.assertTrue(self.v(community(ITEMS=[citem(), citem()]))[0])          # duplicate id
        self.assertTrue(self.v(community(ITEMS=[citem(id="")]))[0])
        self.assertTrue(self.v(community(ITEMS=[citem(status="maybe")]))[0])
        self.assertTrue(self.v(community(ITEMS=[citem(deadline="20 Oct")]))[0])
        self.assertTrue(self.v(community(ITEMS=[citem(at=["narnia"])]))[0])
        self.assertTrue(self.v(community(LAST_CHECKED="today"))[0])

    def test_welsh_in_step(self):
        self.assertTrue(self.v(community(SOON_CY=[]))[0])
        self.assertTrue(self.v(community(ITEMS=[citem(cy={"title": "x", "aff": []})]))[0])
        e, w = self.v(community(ITEMS=[citem(cy={})]))   # missing Welsh is only a warning
        self.assertEqual(e, []); self.assertTrue(w)

    def test_missing_constant(self):
        st = community(); del st["GROUPS"]
        self.assertTrue(self.v(st)[0])


class Consultation(unittest.TestCase):
    def v(self, st):
        return m.validate("consultation", st)

    def test_clean_passes(self):
        self.assertEqual(self.v(consultation()), ([], []))

    def test_bad_links_and_fields_block(self):
        self.assertTrue(self.v(consultation(ITEMS=[oitem(url="javascript:x")]))[0])
        self.assertTrue(self.v(consultation(PETITIONS=[{"date": "2026-01-01", "url": "vbscript:x"}]))[0])
        self.assertTrue(self.v(consultation(PETITIONS=[{"date": "soon", "url": "https://e.org"}]))[0])
        self.assertTrue(self.v(consultation(ITEMS=[oitem(status="ongoing")]))[0])  # not a Consultation status
        self.assertTrue(self.v(consultation(PLACE={"o1": ["ammanford", "mars"]}))[0])

    def test_cy_a_lists_must_match(self):
        self.assertTrue(self.v(consultation(ITEMS=[oitem(cy={"title": "x", "a": {"people": []}})]))[0])

    def test_dangling_place_and_status_warn(self):
        e, w = self.v(consultation(PLACE={"zz": "npt"}, STATUS={"zz": "x"}))
        self.assertEqual(e, []); self.assertEqual(len(w), 2)


class Unwrap(unittest.TestCase):
    def test_strips_host_wrapper_only(self):
        page = '<meta charset="utf-8">\n<title>T</title><script>const X = 1;</script>'
        saved = '<!doctype html><html><head><meta charset=utf8><style>body{}</style></head><body>\n' + page + "</body></html>"
        self.assertEqual(m.unwrap(saved), page)       # keeps the page's own leading <meta>
        self.assertEqual(m.unwrap(page), page)        # no wrapper: unchanged


class RoundTrip(unittest.TestCase):
    def test_apply_writes_safe_json_and_keeps_page(self):
        st = community(ITEMS=[citem(title="</script><script>alert(1)</script>")])
        page = "<title>t</title><script>const PHOTOS = {\"a\":\"b\"};\n" + "".join(
            f"const {c} = {json.dumps(v)};\n" for c, v in community().items()) + "function go(){}</script>"
        with tempfile.TemporaryDirectory() as d:
            p, s, out = os.path.join(d, "page.html"), os.path.join(d, "st.json"), os.path.join(d, "out")
            open(p, "w", encoding="utf-8").write(page)
            json.dump(st, open(s, "w", encoding="utf-8"))
            m.cmd_apply("community", s, p, out)
            html = open(os.path.join(out, "page.html"), encoding="utf-8").read()
            self.assertEqual(html.count("</script>"), 1)
            self.assertIn('const PHOTOS = {"a":"b"};', html)   # photos untouched
            self.assertIn("function go(){}", html)
            m.cmd_extract("community", os.path.join(out, "page.html"), os.path.join(d, "rt.json"))
            self.assertEqual(json.load(open(os.path.join(d, "rt.json"), encoding="utf-8")), st)

    def test_apply_refuses_bad_data(self):
        with tempfile.TemporaryDirectory() as d:
            s = os.path.join(d, "st.json")
            json.dump(community(ITEMS=[citem(url="javascript:x")]), open(s, "w", encoding="utf-8"))
            with self.assertRaises(SystemExit):
                m.cmd_apply("community", s, os.path.join(d, "none.html"), d)


class DataJsonSplit(unittest.TestCase):
    """R2 moved each page's data into a sibling data.json. extract must read it from there,
    apply must write it back there, and a half-split page must work either way."""

    def build(self, d, inline, extra_keys=None):
        """A temp dir holding page.html with INLINE constants and a data.json holding the rest."""
        page = "<title>t</title><script>const PHOTOS = {\"a\":\"b\"};\n" + "".join(
            f"const {c} = {json.dumps(v)};\n" for c, v in d.items() if c in inline) + "function go(){}</script>"
        data = {"generated_at": "2020-01-01T00:00:00Z"}
        data.update(extra_keys or {})
        for c, v in d.items():
            if c not in inline:
                data[c.lower()] = v
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        open(os.path.join(tmp, "page.html"), "w", encoding="utf-8").write(page)
        with open(os.path.join(tmp, "data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return tmp

    def test_extract_reads_fully_split_page(self):
        st = community()
        tmp = self.build(st, inline=[])
        out = os.path.join(tmp, "st.json")
        m.cmd_extract("community", os.path.join(tmp, "page.html"), out)
        with open(out, encoding="utf-8") as f:
            self.assertEqual(json.load(f), st)

    def test_extract_reads_half_split_page(self):
        st = consultation()
        tmp = self.build(st, inline=["PLACE", "STATUS"])      # Ammanford keeps these inline
        _, origin, _, _ = m.load_sources("consultation", os.path.join(tmp, "page.html"))
        self.assertEqual(origin["PLACE"], "page")
        self.assertEqual(origin["STATUS"], "page")
        self.assertEqual(origin["ITEMS"], "data")
        out = os.path.join(tmp, "st.json")
        m.cmd_extract("consultation", os.path.join(tmp, "page.html"), out)
        with open(out, encoding="utf-8") as f:
            self.assertEqual(json.load(f), st)

    def test_apply_writes_data_json_and_round_trips(self):
        tmp = self.build(consultation(), inline=["PLACE", "STATUS"])
        changed = consultation(ITEMS=[oitem(id="o1", title="Bus changes, revised")],
                               PLACE={"o1": "llandeilo"}, COLLECTED="26 October 2026")
        sp, out = os.path.join(tmp, "new.json"), os.path.join(tmp, "out")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(changed, f)
        m.cmd_apply("consultation", sp, os.path.join(tmp, "page.html"), out)
        with open(os.path.join(out, "data.json"), encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d["items"][0]["title"], "Bus changes, revised")
        self.assertEqual(d["collected"], "26 October 2026")
        self.assertNotIn("place", d)                       # stayed inline, must not be duplicated
        self.assertNotEqual(d["generated_at"], "2020-01-01T00:00:00Z")   # refreshed
        html = open(os.path.join(out, "page.html"), encoding="utf-8").read()
        self.assertIn("llandeilo", html)                   # the inline constant was updated
        self.assertIn('const PHOTOS = {"a":"b"};', html)   # photos untouched
        self.assertEqual(html.count("</script>"), 1)
        # extract from what apply wrote must give back exactly the state that went in
        rt = os.path.join(tmp, "rt.json")
        m.cmd_extract("consultation", os.path.join(out, "page.html"), rt)
        with open(rt, encoding="utf-8") as f:
            self.assertEqual(json.load(f), changed)

    def test_apply_keeps_unrelated_data_json_keys(self):
        tmp = self.build(community(), inline=[], extra_keys={"schema": 2})
        sp, out = os.path.join(tmp, "new.json"), os.path.join(tmp, "out")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(community(LAST_CHECKED="2026-10-26"), f)
        m.cmd_apply("community", sp, os.path.join(tmp, "page.html"), out)
        with open(os.path.join(out, "data.json"), encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d["schema"], 2)
        self.assertEqual(d["last_checked"], "2026-10-26")

    def test_missing_everywhere_still_fails_loudly(self):
        st = community()
        tmp = self.build(st, inline=[])
        with open(os.path.join(tmp, "data.json"), encoding="utf-8") as f:
            d = json.load(f)
        del d["groups"]                                    # in neither the page nor data.json
        with open(os.path.join(tmp, "data.json"), "w", encoding="utf-8") as f:
            json.dump(d, f)
        with self.assertRaises(SystemExit):
            m.load_sources("community", os.path.join(tmp, "page.html"))


# East Kent / Tayside / West Herts pages hold their data as JavaScript literals, not JSON.
JS_PAGE = """<!doctype html><title>t</title><script>
const AREAS = {ramsgate:"Ramsgate", margate:"Margate"};
const AREAL = Object.assign({thanet:"Across Thanet"}, AREAS);
const IOTN = "https://example.org/news";
const LENSES = [{id:"money", re:/grant|fund's/i}];
function render() {
  const ITEMS = [];
}
const ITEMS = [
  {id:'a1', title:"It's a fair", status:"open", deadline:"2026-11-01", url:IOTN, at:["ramsgate"]}, // trailing
];
const GROUPS = [{n:"Club", area:"thanet", url:"https://example.org/g"}, {n:"Two", area:["ramsgate","margate"]}];
const SOON = ["Later"];
const WATCH = [["Council", "https://example.org/w"]];
const BIG = [{k:"all"}];
render();
</script>"""


class NptKind(unittest.TestCase):
    def test_npt_community_kind_registered_english_only(self):
        self.assertEqual(m.KINDS["community:neath-port-talbot"], m.KINDS["community:east-kent"])


class PlymouthKind(unittest.TestCase):
    def test_plymouth_kind_takes_totnes_from_page_areas(self):
        self.assertEqual(m.KINDS["community:plymouth"], m.KINDS["community:east-kent"])
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        p = os.path.join(tmp, "page.html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(JS_PAGE.replace('margate:"Margate"}', 'margate:"Margate", totnes:"Totnes"}').replace('at:["ramsgate"]', 'at:["totnes"]'))
        st, _, _, _ = m.load_sources("community:plymouth", p)
        self.assertIn("totnes", st[m.AREA_KEYS])
        self.assertEqual(m.validate("community:plymouth", st)[0], [])


class JsLiteralPages(unittest.TestCase):
    KIND = "community:east-kent"

    def page(self, text=JS_PAGE):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        p = os.path.join(tmp, "page.html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return tmp, p

    def test_extract_reads_js_literals_and_resolves_constants(self):
        _, p = self.page()
        st, origin, _, _ = m.load_sources(self.KIND, p)
        self.assertEqual(st["ITEMS"][0]["url"], "https://example.org/news")   # IOTN resolved
        self.assertEqual(st["ITEMS"][0]["title"], "It's a fair")
        self.assertEqual(len(st["ITEMS"]), 1)            # the function-local ITEMS is ignored
        self.assertEqual(st[m.AREA_KEYS], ["margate", "ramsgate", "thanet"])
        self.assertEqual(set(origin.values()), {"page"})

    def test_validation_uses_page_area_keys(self):
        _, p = self.page()
        st, _, _, _ = m.load_sources(self.KIND, p)
        self.assertEqual(m.validate(self.KIND, st)[0], [])
        st["ITEMS"][0]["at"] = ["narnia"]
        self.assertTrue(m.validate(self.KIND, st)[0])
        st["ITEMS"][0]["at"] = ["ramsgate"]; st["GROUPS"][1]["area"] = ["ramsgate", "narnia"]
        self.assertTrue(m.validate(self.KIND, st)[0])

    def test_apply_round_trip_inline(self):
        tmp, p = self.page()
        st, _, _, _ = m.load_sources(self.KIND, p)
        st["SOON"] = ["Sooner"]
        sp, out = os.path.join(tmp, "st.json"), os.path.join(tmp, "out")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(st, f)
        m.cmd_apply(self.KIND, sp, p, out)
        again, _, s, _ = m.load_sources(self.KIND, os.path.join(out, "page.html"))
        self.assertEqual(again["SOON"], ["Sooner"])
        self.assertEqual(again["ITEMS"], st["ITEMS"])
        self.assertIn("render();", s)                    # code after the data is untouched
        self.assertNotIn(m.AREA_KEYS, s)                 # bookkeeping never reaches the page

    def test_refuses_what_cannot_move_to_data_json(self):
        from page_consts import eval_consts
        for decl in ('const X = {a: undefined};', 'const X = [/abc/i];', 'const X = {f: () => 1};',
                     'const X = [NaN];', 'const X = new Set([1]);', 'const X = {m: new Map()};',
                     'const X = [new Date(0)];'):
            with self.assertRaises(SystemExit, msg=decl):
                eval_consts(f"<script>\n{decl}\n</script>", ["X"])
        with self.assertRaises(SystemExit):
            eval_consts("<script>\nconst Y = 1;\n</script>", ["X"])

    def test_trailing_comment_without_semicolon(self):
        from page_consts import eval_consts
        page = "<script>\nconst X = [1, 2] // no semicolon\nconst Y = {a: 'b'}  // nor here\n</script>"
        self.assertEqual(eval_consts(page, ["X", "Y"]), {"X": [1, 2], "Y": {"a": "b"}})


if __name__ == "__main__":
    unittest.main()
