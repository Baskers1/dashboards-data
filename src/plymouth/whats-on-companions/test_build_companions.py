import json
import pytest
import build_companions as bc

WRAP = '<!doctype html><html lang="en"><head><meta charset=utf8><style>x</style></head><body>\n'
DATA = {"events": [
    {"title": "Gig </script><b>", "group": "music", "town": "Plymouth", "date": "2026-11-02", "id": "a", "source": "s", "category": "c"},
    {"title": "Full Council", "group": "politics", "town": "Plymouth", "date": "2026-11-03"}],
    "news": [], "meta": {"updated": "2026-11-01"}}
WHATSON = WRAP + "<title>Plymouth &amp; Ivybridge · What&#x27;s On</title>\n<script>\nconst MODE=\"near\";            // x\nconst OTHER_URL=\"\";  // none\nconst DATA=" + json.dumps(DATA) + ";\n</script>\n</body></html>"
BIG = WRAP + "<title>Big</title>\n<script>\nconst DATA={\"updated\":\"2026-10-01\",\"events\":[]};\nconst TOWNS=[];\n</script>\n</body></html>"


def test_season_switches_title_mode_link_and_unwraps():
    s = bc.season(WHATSON)
    assert s.startswith("<title>Plymouth &amp; Ivybridge · Season Ahead</title>")
    assert 'const MODE="season";' in s and 'MODE="near"' not in s
    assert f'const OTHER_URL="{bc.WHATSON_URL}";' in s
    assert "</body></html>" not in s and "<head>" not in s
    assert bc.SEASON_FIX in s
    assert bc.data_of(s) == DATA  # data untouched


def test_big_drops_politics_and_extra_keys_and_escapes():
    s = bc.big(WHATSON, BIG)
    d = bc.data_of(s)
    assert d["updated"] == "2026-11-01"
    assert [e["title"] for e in d["events"]] == ["Gig </script><b>"]
    assert set(d["events"][0]) == {"title", "group", "town", "date"}
    assert "</script><b>" not in s.split("const DATA=")[1].split("\n")[0]
    assert "const TOWNS=[];" in s


def test_link_sets_season_url():
    assert f'const OTHER_URL="{bc.SEASON_URL}";' in bc.link(WHATSON)


@pytest.mark.parametrize("page", [WHATSON.replace('const MODE="near"', 'const MODE="season"'),
                                  WHATSON.replace("const OTHER_URL", "let OTHER")])
def test_season_refuses_unexpected_shape(page):
    with pytest.raises(bc.Shape):
        bc.season(page)


def test_big_refuses_two_data_lines(tmp_path):
    with pytest.raises(bc.Shape):
        bc.big(WHATSON, BIG.replace("const TOWNS=[];", "const DATA={};"))
    out = tmp_path / "o.html"
    (tmp_path / "w.html").write_text(WHATSON.replace("const DATA=", "const XDATA="))
    (tmp_path / "b.html").write_text(BIG)
    assert bc.main(["big", str(tmp_path / "w.html"), str(tmp_path / "b.html"), str(out)]) == 2
    assert not out.exists()
