#!/usr/bin/env python3
"""Neath Port Talbot events: eleven sources merged into one JSON file.

    python3 npt_events.py -o out/neath-port-talbot-events.json [--days 120]

Sources (checked 2-3 Nov 2026; robots.txt allows every path used):
  gwynhall      Gwyn Hall WordPress JSON (venue)
  porttalbot    Ticketsolve shows.xml: Yr Aelwyd and The Orangery (venue)
  npt-council   NPT Council What's On, paged HTML (council)
  margam        Margam Country Park What's On (venue)
  wherecanwego  WhereCanWeGo Neath (aggregator)
  pontardawe-arts  Pontardawe Arts Centre What's On, data-dates on each show card (venue)
  eventbrite    Eventbrite Port Talbot + Neath search pages, JSON-LD (aggregator)
  useyourlocal  Pig Iron Tavern, Port Talbot, via its useyourlocal.com page (venue)
  npt-democracy NPT Council committee meetings, modern.gov month calendar (council; robots allows all but *.asmx)
  neathrfc      Neath RFC home games at The Gnoll, SportsPress fixtures table (venue; robots allows all but /wp-admin/)
  allwalessport All Wales Sport league pages: home games of NPT clubs, rugby, football, youth (aggregator; no robots.txt)
  (eventbrite also reads its Neath sports-and-fitness browse page, /b/ is allowed, and tags those events Sport.)
Checked 6 Nov 2026 and not used: allevents.in/neath/sports (3 NPT events, 1 sport, and that one duplicates Eventbrite);
nonleaguehq.com (fixtures load from a Supabase API with a key in the page script, not a published feed; All Wales Sport
already has the Neath & District League).
Not usable (3 Nov 2026): Bandsintown (Cloudflare 403); Skiddle (AWS WAF challenge, HTTP 202 with
x-amzn-waf-action: challenge, on plain GET with curl and with the Fetcher; its radius/hidecancelled URLs are also robots-disallowed).

Output: {"meta": {"area","fetched_at","days","sources_ok","sources_failed":[{"id","error"}],
"counts"}, "events": [{"id","title","dates","time","venue","town","url","booking_url",
"price","category","source","source_kind"}]}. Dates are Europe/London, today or later,
within --days. Same title+venue on many dates is one event with a `dates` list.
A source that fails or parses to nothing is listed in sources_failed, never skipped.
Exits 1 (writing nothing) if every source failed.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import os
import re
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup                       # noqa: E402

from aws_fixtures import AWS, club_town, fetch_leagues, parse_league  # noqa: E402
from civic_pages import curl                        # noqa: E402
from scrapekit import Fetcher                      # noqa: E402

log = logging.getLogger("npt_events")
LONDON = ZoneInfo("Europe/London")
GWYN = "https://gwynhall.com/wp-json/bigwave-events/v1/events"
TICKETSOLVE = "https://porttalbottheatre.ticketsolve.com/shows.xml"
NPT = "https://www.npt.gov.uk/culture-and-tourism/whats-on-in-npt/"
MARGAM = "https://www.margamcountrypark.co.uk/whats-on/"
WCWG = "https://www.wherecanwego.com/whats-on/neath"
PONTARDAWE = "https://pontardaweartscentre.com/whats-on/"
DEMOCRACY = "https://democracy.npt.gov.uk/mgCalendarMonthView.aspx?M={m}&Y={y}"
EVENTBRITE = ["https://www.eventbrite.co.uk/d/united-kingdom--port-talbot/all-events/",
              "https://www.eventbrite.co.uk/d/united-kingdom--neath/all-events/"]
EVENTBRITE_SPORT = "https://www.eventbrite.co.uk/b/united-kingdom--neath/sports-and-fitness/"  # fetched first: its events are tagged Sport
UYL_PUBS = [("https://www.useyourlocal.com/pubs/pig-iron-tavern-port-talbot-46758/", "Pig Iron Tavern", "Port Talbot")]
MAX_PAGES = 40
CINEMA = {"Cinema", "Event Cinema", "Animation", "Action", "Action/Adventure", "Baby Pictures"}  # film genres Gwyn Hall tags films with
TOWNS = {"The Orangery": "Margam", "Yr Aelwyd": "Port Talbot"}
PLACES = ["Neath", "Port Talbot", "Aberavon", "Margam", "Pontardawe", "Briton Ferry", "Skewen", "Baglan", "Glynneath",
          "Resolven", "Ystalyfera", "Cwmafan", "Cymmer", "Seven Sisters", "Tonna", "Cadoxton", "Cimla", "Bryncoch", "Crynant",
          "Taibach", "Sandfields", "Gwaun-Cae-Gurwen", "Cwmllynfell", "Godre'r-graig"]
PLACE_RE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(p).replace("\\ ", r"\s+") for p in PLACES) + r")(?![\w-])", re.I)
POSTCODE_RE = re.compile(r"\bSA(8|9|10|11|12|13)\b", re.I)
FULL_POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]? \d[A-Z]{2}\b")
POSTCODE_TOWN = {"8": "Pontardawe", "10": "Neath", "11": "Neath", "12": "Port Talbot", "13": "Port Talbot"}  # SA9 is ambiguous
MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def clean(s) -> str:
    return " ".join(html.unescape(s or "").split())


def expand(a: date, b: date) -> list[date]:
    if not 0 <= (b - a).days <= 400:
        raise ValueError(f"implausible date range {a}..{b}")
    return [a + timedelta(n) for n in range((b - a).days + 1)]


def find_place(text: str) -> str | None:
    """Earliest NPT place named in text, in its canonical spelling."""
    m = PLACE_RE.search(text or "")
    return next(p for p in PLACES if p.lower() == " ".join(m.group().lower().split())) if m else None


def common_time(times) -> str | None:
    """One time for a whole event only when every performance has it; mixed times (a panto's matinees and
    evenings) give None rather than the first performance's time on every date."""
    ts = {t for t in times}
    return ts.pop() if len(ts) == 1 else None


def rec(title, dates, time, venue, town, url, booking_url=None, price=None, category=None) -> dict:
    return {"title": clean(title), "dates": sorted(set(dates)), "time": time, "venue": clean(venue) or None,
            "town": town, "url": url, "booking_url": booking_url, "price": price, "category": category}


# ---- parsers: text -> list of rec() -------------------------------------------------

def parse_gwyn(text: str) -> list[dict]:
    out = []
    for e in json.loads(text)["events"]:
        slots = [(e["date"]["event_date"], e["date"].get("start_time"), e.get("cancelled"))]
        slots += [(i["date"], i.get("start_time"), i.get("cancelled")) for i in e.get("recurring_instances") or []]
        live = sorted((d, t) for d, t, c in slots if d and not c)
        if not live:
            continue
        types = [t["name"] for t in e["taxonomies"]["bigwave_event_type"]]
        cat = "cinema" if types and set(types) <= CINEMA else (types[0] if types else None)
        pricing = e.get("pricing")
        price = ", ".join(pricing) if pricing and all(isinstance(p, str) for p in pricing) else None
        out.append(rec(e["title"], [date.fromisoformat(d) for d, _ in live], common_time((t or "")[:5] or None for _, t in live),
                       "Gwyn Hall", "Neath", e["permalink"], e.get("booking_url") or None, price, cat))
    return out


def parse_ticketsolve(text: str) -> list[dict]:
    out = []
    for venue in ET.fromstring(text).iter("venue"):
        vname = clean(venue.findtext("name"))
        for show in venue.iter("show"):
            slots = []
            for ev in show.iter("event"):
                if "cancel" in (ev.findtext("status") or "").lower():
                    continue
                slots.append((datetime.fromisoformat(ev.findtext("date_time_iso").strip()).astimezone(LONDON), ev.findtext("url")))
            if slots:
                slots.sort()
                out.append(rec(show.findtext("name"), [s.date() for s, _ in slots], common_time(s.strftime("%H:%M") for s, _ in slots), vname,
                               TOWNS.get(vname), show.findtext("url").strip(), slots[0][1], None,
                               clean(show.findtext("event_category")) or None))
    return out


def parse_cards(text: str, base: str, town: str | None) -> list[dict]:
    """NPT Council and Margam share one CMS: cards with a footer of dates, time and venue."""
    out = []
    for card in BeautifulSoup(text, "lxml").select(".events .card"):
        a = card.select_one("h3 a[href]")
        foot = card.select_one(".card-footer")
        if not a or not foot:
            continue
        ds = [datetime.strptime(d.replace("Sept", "Sep"), "%d %b %Y").date() for d in re.findall(r"\d{2} \w{3,4} \d{4}", foot.get_text(" "))]  # council writes "Sept"
        if not ds:
            raise ValueError(f"card without a date: {clean(a.get_text())}")
        def span(label):
            s = foot.select_one(f'svg[aria-label="{label}"]')
            return clean(s.parent.get_text(" ")) if s else ""
        t = re.search(r"\d{1,2}:\d{2}", span("Time"))
        venue = span("Venue")
        out.append(rec(a.get_text(), expand(ds[0], ds[1]) if len(ds) > 1 else ds, t.group().zfill(5) if t else None,
                       venue, find_place(venue) or town, urljoin(base, a["href"])))
    return out


def parse_wcwg_dates(s: str, today: date) -> list[date]:
    """'Thu 5 Nov, Thu 14 Jan 27', 'Fri 6 Nov to Thu 3 Dec', 'Today', '..., and more dates until Wed 2 Dec'."""
    toks = list(re.finditer(r"\bToday\b|\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\d{1,2}) ([A-Z][a-z]{2})(?: (\d{2})\b)?", s))
    if not toks:
        raise ValueError(f"unrecognised date text: {s!r}")
    def one(m):
        if m.group().startswith("Today"):
            return today
        y = 2000 + int(m.group(3)) if m.group(3) else today.year
        d = date(y, MONTHS[m.group(2)], int(m.group(1)))
        return d.replace(year=y + 1) if not m.group(3) and d < today - timedelta(days=183) else d
    days = [one(m) for m in toks]
    out = []
    for i, d in enumerate(days):
        if i and s[toks[i - 1].end():toks[i].start()].strip() == "to":
            out += expand(days[i - 1], d)
        else:
            out.append(d)
    return sorted(set(out))


def wcwg_area(recs: list[dict]) -> tuple[list[dict], int]:
    """Keep aggregator events in SA8-SA13 or naming an NPT place, with town set; return (kept, dropped count)."""
    kept = []
    for r in recs:
        v = r["venue"] or ""
        place, pc = find_place(v), POSTCODE_RE.search(v)
        if FULL_POSTCODE_RE.search(v):  # a full postcode is authoritative: "Neath Road, Swansea SA1 1AA" is not NPT
            place = place if pc else None
        if place or pc:
            kept.append({**r, "town": place or POSTCODE_TOWN.get(pc.group(1))})
    return kept, len(recs) - len(kept)


def parse_wcwg(text: str, today: date) -> list[dict]:
    out = []
    for r in BeautifulSoup(text, "lxml").select("div.EventResults"):
        m = re.search(r"/item/e\d+", r.get("onclick", ""))
        title, when, venue = r.select_one(".eventtitle"), r.select_one(".DateTimeString"), r.select_one(".VenueLine")
        if not (m and title and when):
            raise ValueError("result without link, title or date")
        out.append(rec(title.get_text(), parse_wcwg_dates(clean(when.get_text()), today), None,
                       venue.get_text() if venue else "", None, "https://www.wherecanwego.com" + m.group()))
    return out


PONTARDAWE_VENUE = "Pontardawe Arts Centre"
MOVED_RE = re.compile(r"taking place at\s+([^.;\n]+)", re.I)


def moved_venue(card) -> str | None:
    """Where a Pontardawe Arts Centre listing says the show really is: the card's own venue line when it
    differs, else a 'taking place at <venue>' note. The note runs on without a space ('NEATHAll tickets'), so
    cut at a capital followed by a capitalised word."""
    line = clean(card.select("a.card-date-info")[-1].get_text()) if card.select("a.card-date-info") else ""
    if line and line.lower() != PONTARDAWE_VENUE.lower():
        return line
    note = card.select_one(".sg-post-excerpt")
    m = MOVED_RE.search(clean(note.get_text()) if note else "")
    if not m:
        return None
    v = clean(re.split(r"(?<=[A-Z])(?=[A-Z][a-z])", m.group(1))[0])
    v = re.sub(r"^the\s+", "", v, flags=re.I)  # 'THE CASTLE HOTEL' -> 'Castle Hotel'
    return v.title() if v.isupper() else v


def parse_pontardawe(text: str) -> list[dict]:
    """Show cards carry every performance date in data-dates; times are not in the listing.
    Some cards are for shows the centre promotes at another venue (e.g. the Castle Hotel, Neath); those keep
    the real venue, and the town comes from the place matcher (None when the venue is outside the borough)."""
    out = []
    for c in BeautifulSoup(text, "lxml").select(".whatson_show"):
        a, h = c.select_one("a[href]"), c.select_one("h3")
        if not (a and h):
            raise ValueError("show card without link or title")
        ds = [date.fromisoformat(d) for d in json.loads(c["data-dates"])]
        cat = c.select_one(".sg-btn-alt")
        venue = moved_venue(c)
        out.append(rec(h.get_text(), ds, None, venue or PONTARDAWE_VENUE, find_place(venue) if venue else "Pontardawe",
                       a["href"], None, None,
                       clean(cat.get_text()).lower() if cat else None))
    return out


MEETING_RE = re.compile(r"^Meeting of (.+?) on (\d{1,2})/(\d{1,2}) at (\d{1,2})\.(\d\d) ([ap]m)$")


def parse_democracy(text: str, year: int, month: int) -> list[dict]:
    """One month view of the council's modern.gov calendar. Its links read "Meeting of <committee> on dd/mm at h.mm am";
    the grid also shows the edges of the months either side, so a day's year follows from its month."""
    out = []
    for a in BeautifulSoup(text, "html.parser").select("a[href*='ieListDocuments.aspx']"):
        m = MEETING_RE.match(clean(a.get_text(" ")))
        # Not a meeting that will happen there and then: cancelled, postponed, provisional, moved away, workshops, tests.
        if not m or re.search(r"cancel|postpone|provisional|^moved -|workshop only|^zzz", m.group(1), re.I):
            continue
        name, d, mo, h, mi, ap = m.groups()
        name = re.sub(r"^moved from [^,]+, ", "", name, flags=re.I)  # moved here: keep it, under its own name
        y = year - 1 if int(mo) - month > 6 else year + 1 if month - int(mo) > 6 else year
        hh = int(h) % 12 + (12 if ap == "pm" else 0)
        out.append(rec(name, [date(y, int(mo), int(d))], f"{hh:02d}:{mi}", None, None,
                       urljoin(DEMOCRACY, a["href"]), category="Council meeting"))
    return out


def fetch_democracy(fetcher, today: date, days: int) -> list[dict]:
    end, y, m, out = today + timedelta(days=days), today.year, today.month, []
    while (y, m) <= (end.year, end.month):
        out += parse_democracy(get_curl(DEMOCRACY.format(m=m, y=y)), y, m)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def ld_events(text: str) -> list[dict]:
    """schema.org Event objects from every ld+json block (bare, in a list, or in an ItemList)."""
    found = []
    for m in BeautifulSoup(text, "lxml").select('script[type="application/ld+json"]'):
        d = json.loads(m.string)
        for x in d if isinstance(d, list) else d.get("itemListElement") or [d]:
            x = x.get("item", x) if isinstance(x, dict) else x
            if isinstance(x, dict) and x.get("@type") == "Event":
                found.append(x)
    return found


def parse_jsonld(text: str) -> list[dict]:
    """Eventbrite (and Skiddle-shaped) JSON-LD: one rec per Event, on its start date only (shortcut: multi-day runs show their first day).
    Venue is 'name, street, locality, postcode' so the area filter can see the postcode."""
    out = []
    for e in ld_events(text):
        if "cancel" in str(e.get("eventStatus", "")).lower():
            continue
        loc = e.get("location") or {}
        adr = loc.get("address") or {}
        venue = ", ".join(x for x in (loc.get("name"), adr.get("streetAddress"), adr.get("addressLocality"), adr.get("postalCode")) if x)
        start = datetime.fromisoformat(e["startDate"])
        start = start.astimezone(LONDON) if start.tzinfo else start
        t = start.strftime("%H:%M") if "T" in e["startDate"] else None
        prices = [float(o["price"]) for o in e.get("offers") or [] if o.get("price") not in (None, "")]
        out.append(rec(e["name"], [start.date()], t, venue, None, e["url"],
                       None, f"from £{min(prices):.2f}" if prices else None))
    return out


def parse_uyl(text: str, today: date, venue: str, town: str) -> list[dict]:
    """useyourlocal pub page: cards with 'Fri 6th Nov' (no year: next occurrence)."""
    out = []
    for c in BeautifulSoup(text, "lxml").select("a.cal-card"):
        h, w = c.select_one("h4"), re.search(r"(\d{1,2})(?:st|nd|rd|th) ([A-Z][a-z]{2})", c.select_one(".cc-time").get_text() if c.select_one(".cc-time") else "")
        if not (h and w):
            raise ValueError("pub event card without title or date")
        d = date(today.year, MONTHS[w.group(2)], int(w.group(1)))
        out.append(rec(h.get_text(), [d.replace(year=d.year + 1) if d < today - timedelta(days=183) else d], None, venue, town, c["href"]))
    return out


NEATHRFC = "https://neathrfc.com/fixtures-and-results/"
NEATHRFC_DROP = re.compile(r"postpon|cancel|abandon|void|tbc", re.I)


def parse_neathrfc(text: str) -> list[dict]:
    """Neath RFC's SportsPress fixtures table: home games only ('Neath v ...'), so every listing is at a ground in the
    borough; BYE/BLANK weeks, away games and postponed or cancelled games are left out. Kick-off comes from the row's
    <date> text ('2026-11-21 14:30:05'), which is the local clock: the cell's content attribute says +00:00 all year."""
    out = []
    for tr in BeautifulSoup(text, "lxml").select("table.sp-event-list tbody tr"):
        when, ev = tr.select_one("td.data-date date"), tr.select_one("td.data-event a[href]")
        if not (when and ev):
            raise ValueError("fixture row without date or match link")
        title = re.sub(r"\s+RFC\b", "", clean(ev.get_text()))  # "Llangennech RFC": All Wales Sport says "Llangennech"
        status = clean(tr.select_one("td.data-time").get_text(" ")) if tr.select_one("td.data-time") else ""
        if not re.match(r"Neath v ", title) or NEATHRFC_DROP.search(status):
            continue
        dt = datetime.strptime(clean(when.get_text())[:16], "%Y-%m-%d %H:%M")
        venue = clean(tr.select_one("td.data-venue").get_text()) if tr.select_one("td.data-venue") else ""
        league = clean(tr.select_one("td.data-league").get_text()) if tr.select_one("td.data-league") else ""
        out.append(rec(title, [dt.date()], dt.strftime("%H:%M"), venue or "The Gnoll",
                       "Neath" if (venue or "The Gnoll") == "The Gnoll" else find_place(venue), ev["href"],
                       category=f"Sport: rugby union, {league}" if league else "Sport: rugby union"))
    return out


# All Wales Sport (Red Dragon Press Agency): one page per league or cup; the parser is shared with Ammanford in
# aws_fixtures.py. No robots.txt (404).
# Leagues and cups with an NPT club in them (scan of 552 league pages, 6 Nov 2026). Cricket and junior football are left
# out: no NPT cricket fixtures are published out of season, and the only local-looking junior club ("Sandfields") is ambiguous.
AWS_LEAGUES = [  # (page, cid, label)
    ("rugby-union", 19909, "Super Rygbi Cymru: SRC Trophy"),
    ("rugby-union", 19919, "Super Rygbi Cymru: SRC Cup - Pool B"),
    ("rugby-union", 19813, "WRU Premiership: Premiership"),
    ("rugby-union", 20045, "WRU Premiership Cup: Premiership Cup"),
    ("rugby-union", 19901, "WRU Championship: Championship - West"),
    ("rugby-union", 20022, "WRU Championship Cup: Championship Cup"),
    ("rugby-union", 19854, "Womens Rugby: Premiership"),
    ("rugby-union", 20042, "Womens Rugby: WRU Cup"),
    ("rugby-union", 19792, "WRU West Central: 1 West Central"),
    ("rugby-union", 19793, "WRU West Central: 2 West Central"),
    ("rugby-union", 19794, "WRU West Central: 3 West Central"),
    ("rugby-union", 19811, "WRU West Central: 4 West Central"),
    ("rugby-union", 19812, "WRU West Central: 5 West Central"),
    ("rugby-union", 20023, "WRU Division 1 Cup: Division 1 Cup"),
    ("rugby-union", 20024, "WRU Division 2 Cup: Division 2 Cup"),
    ("rugby-union", 20025, "WRU Division 3 Cup: Division 3 Cup"),
    ("rugby-union", 20026, "WRU Division 4 Cup: Division 4 Cup"),
    ("rugby-union", 20027, "WRU Division 5 Cup: Division 5 Cup"),
    ("rugby-union", 21133, "Swansea District: League"),
    ("football", 20052, "Novira Cymru Premier: League"),
    ("football", 20146, "Novira Cymru Leagues: Cymru South"),
    ("football", 20421, "FAW Cymru Welsh Cup: Welsh Cup Main"),
    ("football", 20340, "FAW Cymru Welsh Cup: Welsh Cup South"),
    ("football", 20354, "FAW Trophy: South"),
    ("football", 20150, "Ardal Leagues: South West"),
    ("football", 20480, "Ardal League Cups: South Cup"),
    ("football", 20157, "FAW Cymru Reserves: South West"),
    ("football", 20158, "Womens Football: Premier League"),
    ("football", 21104, "Womens Football: Welsh Cup - South"),
    ("football", 20347, "Womens Football: Genero Adran Trophy"),
    ("football", 20054, "Neath & District: Premier Division"),
    ("football", 20055, "Neath & District: Division 1"),
    ("football", 20056, "Neath & District: Division 2"),
    ("football", 20220, "Neath & District: Division 3"),
    ("football", 20297, "Neath & District: Division 4"),
    ("football", 20408, "Neath & District: Open Cup"),
    ("football", 20409, "Neath & District: Open Trophy"),
    ("football", 20335, "Neath & District: Rose Bowl"),
    ("football", 20405, "Neath & District: Division 2 Cup"),
    ("football", 20062, "Port Talbot & District: League"),
    ("football", 20373, "Port Talbot & District: Open Cup"),
    ("football", 20059, "South Wales Premier: Premier Division"),
    ("football", 20262, "South Wales Premier: Championship"),
    ("football", 20384, "South Wales Premier: W John Owen Cup"),
    ("football", 20438, "West Wales FA: West Wales FA Cup"),
    ("football", 20144, "West Wales Premier: W Wales League"),
    ("youth-rugby", 20623, "U18 Schools & Colleges: Conference B"),
    ("youth-rugby", 20824, "U18 WRU Trophies: Cup"),
    ("youth-rugby", 20826, "U18 WRU Trophies: Plate"),
    ("youth-rugby", 20825, "U18 WRU Trophies: Bowl"),
    ("youth-rugby", 20783, "U18 WRU Trophies: Shield"),
    ("youth-rugby", 20598, "U18 Ospreys Region: Cup - Group 1"),
    ("youth-rugby", 21144, "U18 Ospreys Region: Bowl - Group 2"),
    ("youth-rugby", 21145, "U18 Ospreys Region: Shield - Group 2"),
    ("youth-rugby", 20605, "U18 Ospreys Region: Trophy - Group 1"),
    ("youth-rugby", 21141, "U18 Ospreys Region: Trophy - Group 2"),
    ("youth-rugby", 20688, "Youth Rugby Friendlies: Friendlies"),
    ("youth-football", 20908, "FAW Youth Cup: FAW Youth Cup"),
    ("youth-football", 20893, "FAW National Academi: South"),
]
# Home team (as All Wales Sport spells it, without a Reserves/B/3rds suffix) -> town: a page button where the ground is in
# one of the nine towns, else its own village (TOWN_MAP in npt_whatson.py folds Cimla, Tonna, Baglan etc. onto a button).
# Only home games of these clubs are kept, so every listing is at a ground in the borough. Left out as not in the borough or
# ambiguous: Ystradgynlais, Cwmtwrch, Abercrave (Powys), Brynamman (Carmarthenshire), Glais, Clydach, Vardre, Ynystawe
# (Swansea), Maesteg (Bridgend), Sandfields (a Swansea name too), Cwm Wanderers and Brynawel (home not confirmed).
AWS_CLUBS = {
    "Aberavon": "Aberavon", "Aberavon Green Stars": "Aberavon", "Aberavon Quins": "Aberavon", "Afan Lido": "Aberavon",
    "Afan United": "Port Talbot", "Port Talbot Town": "Port Talbot", "Trefelin": "Port Talbot", "Trefelin BGC": "Port Talbot",
    "Goytre United": "Port Talbot", "Goytre Utd": "Port Talbot", "Tata Steel": "Port Talbot", "Tata Steel United": "Port Talbot",
    "Tata Steel Utd": "Port Talbot", "Pontrhydyfen/Taibach": "Port Talbot", "Taibach": "Taibach", "Pontrhydyfen": "Pontrhydyfen",
    "Cwmafan": "Cwmafan", "Baglan": "Baglan", "Baglan Dragons": "Baglan", "Margam YC": "Margam", "Croeserw Athletic": "Croeserw",
    "Gwynfi United": "Abergwynfi", "Glyncorrwg": "Glyncorrwg", "Tonmawr": "Tonmawr",
    "Neath": "Neath", "Neath Athletic": "Neath", "Neath Town": "Neath", "Neath Port Talbot Coll": "Neath",
    "Cwrt Herbert Colts": "Neath", "Cimla": "Cimla", "Bryncoch": "Bryncoch", "Tonna": "Tonna", "Cilfrew Rovers": "Cilfrew",
    "Ynysygerwn": "Ynysygerwn", "Longford": "Longford", "Skewen": "Skewen", "Coed Darcy": "Coed Darcy", "Llandarcy": "Llandarcy",
    "Briton Ferry": "Briton Ferry", "Briton Ferry Llansawel": "Briton Ferry", "Giants Grave": "Briton Ferry",
    "Glynneath": "Glynneath", "Glynneath Town": "Glynneath", "Resolven": "Resolven", "Cwmgwrach": "Cwmgwrach",
    "Seven Sisters": "Seven Sisters", "Seven Sisters Onllwyn": "Seven Sisters", "Banwen": "Banwen", "Crynant": "Crynant",
    "Pontardawe": "Pontardawe", "Pontardawe Town": "Pontardawe", "AFC Pontardawe": "Pontardawe", "Trebanos": "Trebanos",
    "Ynysmeudwy": "Ynysmeudwy", "Rhos": "Rhos", "Ystalyfera": "Ystalyfera", "Ysgol Ystalyfera": "Ystalyfera",
    "Godre'r Graig": "Godre'r-graig", "Godre'r Graig Ath": "Godre'r-graig", "Godrergraig Ath": "Godre'r-graig",
    "Cwmllynfell": "Cwmllynfell", "Cwmgors": "Cwmgors",
}


def aws_town(team: str) -> str | None:
    """Town of an NPT club's home ground, or None if the team is not one of ours."""
    return club_town(team, AWS_CLUBS)


def _recs(fixtures) -> list[dict]:
    return [rec(r["title"], [r["date"]], r["time"], r["venue"], r["town"], r["url"], category=r["category"]) for r in fixtures]


def parse_aws(text: str, page: str, cid: int, label: str) -> list[dict]:
    """One All Wales Sport league page: home games of NPT clubs (rules in aws_fixtures.parse_league)."""
    return _recs(parse_league(text, page, cid, label, AWS_CLUBS))


def fetch_aws(fetcher, today: date, days: int) -> list[dict]:
    """Every league page in AWS_LEAGUES; one dead page keeps the rest (the run log names it), all dead fails the source."""
    fixtures, _ = fetch_leagues(lambda u: get(fetcher, u), AWS_LEAGUES, AWS_CLUBS)
    return _recs(fixtures)


# ---- fetching -----------------------------------------------------------------------

def get(fetcher, url: str) -> str:
    r = fetcher.get(url, fallback_to_cache=False)
    if r.status != 200:
        raise RuntimeError(f"HTTP {r.status} from {url}")
    return r.text


def get_curl(url: str) -> str:
    status, body = curl(url)
    if status != 200:
        raise RuntimeError(f"HTTP {status} from {url}")
    return body


def fetch_npt(fetcher, today: date, days: int) -> list[dict]:
    out, cutoff = [], today + timedelta(days=days)
    for page in range(1, MAX_PAGES + 1):
        cards = parse_cards(get(fetcher, f"{NPT}?page={page}&size=100"), NPT, "Neath Port Talbot")
        if not cards:
            if page == 1:
                raise RuntimeError("no events on page 1")
            break
        out += cards
        if min(c["dates"][0] for c in cards) > cutoff:  # pages run in date order
            break
    return out


def eventbrite_page(fetcher, url: str) -> list[dict]:
    """One Eventbrite page; the sports page's events get category Sport. It is fetched first, so when the same event is on an
    all-events page too, finish() keeps this tagged copy and only adds dates."""
    recs = parse_jsonld(get(fetcher, url))
    return [{**r, "category": "Sport"} for r in recs] if url == EVENTBRITE_SPORT else recs


def fetch_all(urls, getter, parse):
    """Fetch several pages for one source; fail only if every page failed (one dead page keeps the rest)."""
    out, errs = [], []
    for u in urls:
        try:
            out += parse(getter(u))
        except Exception as exc:
            errs.append(f"{u}: {exc}")
    if errs and not out:
        raise RuntimeError("; ".join(errs)[:300])
    return out


SOURCES = [  # (id, source_kind, fetch(fetcher, today, days) -> records)
    # shortcut: curl_cffi gets an HTTP/2 PROTOCOL_ERROR from gwynhall.com (checked 3 Nov 2026) and
    # pontardaweartscentre.com (every run 3-6 Nov) while macOS curl is fine, so these use curl as civic_pages
    # does; switch back to get() once the Fetcher copes.
    ("gwynhall", "venue", lambda f, t, d: parse_gwyn(get_curl(GWYN))),
    ("porttalbot", "venue", lambda f, t, d: parse_ticketsolve(get(f, TICKETSOLVE))),
    ("npt-council", "council", fetch_npt),
    ("margam", "venue", lambda f, t, d: parse_cards(get(f, MARGAM), MARGAM, "Margam")),
    ("wherecanwego", "aggregator", lambda f, t, d: wcwg_area(parse_wcwg(get(f, WCWG), t))),
    ("pontardawe-arts", "venue", lambda f, t, d: parse_pontardawe(get_curl(PONTARDAWE))),
    ("eventbrite", "aggregator", lambda f, t, d: wcwg_area(fetch_all([EVENTBRITE_SPORT] + EVENTBRITE, lambda u: eventbrite_page(f, u), lambda x: x))),
    ("useyourlocal", "venue", lambda f, t, d: [r for u, v, tn in UYL_PUBS for r in parse_uyl(get(f, u), t, v, tn)]),
    ("npt-democracy", "council", fetch_democracy),
    ("neathrfc", "venue", lambda f, t, d: parse_neathrfc(get(f, NEATHRFC))),
    ("allwalessport", "aggregator", fetch_aws),
]


FIXTURE_SOURCES = {"neathrfc", "allwalessport"}


def finish(source: str, kind: str, recs: list[dict], today: date, days: int) -> list[dict]:
    """Window-filter, collapse same title+venue into one event, add id and source."""
    cutoff, merged = today + timedelta(days=days), {}
    for r in recs:
        ds = [d for d in r["dates"] if today <= d <= cutoff]
        if not ds:
            continue
        k = (r["title"].lower(), (r["venue"] or "").lower())
        if source == "npt-democracy":  # each meeting has its own agenda page and time: never fold dates together
            k += (r["url"],)
        if source in FIXTURE_SOURCES:  # one listing per match: a league and a cup game v the same side keep their own kick-offs
            k += (r["url"], ds[0])
        if k in merged:
            merged[k]["dates"] = sorted(set(merged[k]["dates"]) | set(ds))
            merged[k]["time"] = common_time([merged[k]["time"], r["time"]])
        else:
            merged[k] = {**r, "dates": ds}
    out = []
    for r in merged.values():
        key = f"{source}|{r['url']}|{r['dates'][0]}"
        out.append({"id": hashlib.sha1(key.encode()).hexdigest()[:12], **r, "dates": [d.isoformat() for d in r["dates"]],
                    "source": source, "source_kind": kind})
    return out


def run(fetcher=None, today: date | None = None, days: int = 120, sources=SOURCES) -> dict:
    fetcher = fetcher or Fetcher(use_cache=False, timeout=30)
    today = today or datetime.now(LONDON).date()
    events, ok, failed, counts = [], [], [], {}
    for sid, kind, fetch in sources:
        t0 = time.monotonic()
        try:
            recs = fetch(fetcher, today, days)
            extra = {}
            if isinstance(recs, tuple):  # (records, dropped) from the aggregator's area filter
                recs, dropped = recs
                extra = {f"{sid}_dropped_out_of_area": dropped}
            if not recs:
                raise RuntimeError("parsed zero events (page layout changed?)")
            got = finish(sid, kind, recs, today, days)
        except Exception as exc:  # one dead source must not take the others down
            failed.append({"id": sid, "error": f"{type(exc).__name__}: {str(exc)[:300]}"})
            log.error("FAILED %s after %.1fs: %s", sid, time.monotonic() - t0, exc)
            continue
        events += got
        ok.append(sid)
        counts[sid] = len(got)
        counts.update(extra)
        log.info("%s: %d events in %.1fs", sid, len(got), time.monotonic() - t0)
    events.sort(key=lambda e: (e["dates"][0], e["time"] or "", e["title"]))
    return {"meta": {"area": "neath-port-talbot", "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "days": days, "sources_ok": ok, "sources_failed": failed, "counts": counts}, "events": events}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(message)s", stream=sys.stderr)
    data = run(days=a.days)
    if not data["meta"]["sources_ok"]:
        print("every source failed; nothing written", file=sys.stderr)
        return 1
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, out)
    print(f"wrote {out}: {len(data['events'])} events, {len(data['meta']['sources_failed'])} sources failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
