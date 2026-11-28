# Weather template

One template for the six area weather boards. Each board is a folder of settings plus its
own photos and fixed lists; the hourly task supplies only the data.

Status (22 Nov 2026): live for West Herts (since 14:37). Neath Port Talbot is merged in and
tested; its hourly task is switched separately.

- 13:22 West Herts extracted. With `"photos": "inline"` and the original layout, the build
  plus `tools/harden.py` matched the live page (12:50) byte for byte.
- 13:40 First changes, measured in headless Chrome at 390 x 844 against the 12:50 live page:

  | | Live | Template |
  |---|---|---|
  | Page size | 894 KB | 190 KB, plus one photo (42-80 KB) for the town on show |
  | "Right now" starts | 0.86 screens down | 0.29 screens down |
  | Larger text | works (16 to 22 px) | works (16 to 22 px) |
  | Console errors | none | none |

## Layout

| Path | What it is |
|---|---|
| `shell.html` | Page skeleton with markers: `{{TITLE}}`, `{{H1}}`, `{{JUMP}}`, `{{SECTIONS}}`, `{{PART:name}}` |
| `parts/` | Styles and scripts. `app.js` holds `{{BLOCK:NAME}}` markers where data goes |
| `sections/<name>.html` | One card per section. `{{ABOUT}}` is filled from the area's settings |
| `sections/catalogue.json` | Each section's anchor and jump-link label |
| `areas/<area>/settings.json` | Title, heading, which sections in which order, area-specific "About" text |
| `areas/<area>/static/*.js` | Lists that change only by hand: towns, walks, overflow names |
| `areas/<area>/heroes.json`, `heroes/` | Town photos and their credits (several towns may share one file) |
| `areas/<area>/static/SITE.js` | Area wording the shared code uses: town-button label, air-station note, "typical"/"usual" range, scene, walk land label |
| `areas/<area>/code/` | The area's own river, flood and sewage code (`rivers.js`, `sewage.js`, `viz.js`), filled into the `{{CODE:...}}` slots of `parts/app.js` and `parts/07-viz-js.js`. England (Environment Agency, Thames Water) and Wales (NRW) differ here |
| `areas/<area>/refresh.json` | How `refresh_data.py` builds this area's data blocks |
| `fixtures/` | Saved hours of data used by the tests |

## Commands

    python3 refresh_data.py west-herts <current page.html> <data/west-herts.json> data.json
    python3 build.py west-herts data.json <out_dir>      # writes index.html and heroes/
    python3 test_build.py && python3 test_refresh_data.py

`refresh_data.py` turns one hour's file from dashboards-data into the page's data blocks.
Weather and air use the area's own `refresh_weather.py`; rivers, floods and sewage follow
`areas/<area>/refresh.json` (these used to be steps 4 and 5 of the hourly task prompt, done
by hand each run). A block that cannot be refreshed is kept from the current page, with a
line saying why. On the 13:31 data of 22 Nov it produced exactly the blocks the hourly task
published at 13:54.

## Turning a section on or off

Edit `sections` in `areas/<area>/settings.json`. The section card, its jump link and (once
the app code is updated) its "Right now" tile follow the list. An inland board leaves out
`tides` and `bathing`.

## Merging a board in (as done for Neath Port Talbot, 22 Nov)

1. Compare its main script with `parts/app.js` function by function, and its chart script with
   `parts/07-viz-js.js` line by line.
2. Area facts written into the code (county names, air station, scene, wording) go to `SITE.js`,
   `COUNTY.js`, `AIRLL.js`. River, flood and sewage code that names the area or its regulator goes
   to `areas/<area>/code/`.
3. Where one board improved shared code (NPT: grouped town buttons, stations with no published
   range), the template takes the improvement for every board.
4. Check: visible text of every town, old page against template page, in Chrome. For NPT the only
   differences were the title, the photo credit wording and one Open-Meteo attribution line; for West
   Herts, a town-group label and a dropped, wrong "refreshed 08:22 to 18:22" sentence.

## Coastal boards and the "extra" slot (Tayside, 22 Nov)

- `sections/tides.html` and `sections/bathing.html` (anchors `t` and `bw`) are switched on in an
  area's `sections` list like any other. Inland boards leave them out.
- `{{CODE:extra}}` sits just before `init();` in `parts/app.js` and is optional. Code there runs
  last, so it can declare an area's own blocks (Tayside: `TIDES`, `BATHING`, `TIDEST`, `AQL`) and
  replace a shared function by declaring one of the same name. Tayside replaces four: `renderAir`
  (Scottish Air Quality pages give one reading, not 24 hours), `drawWalks`/`wtile` (walks filtered
  by starting area), `renderGlance` (a "Next tide" tile) and `setTab` (tides, bathing, SEPA floods).
  Keep such replacements few: each one is a copy that will not pick up later fixes to the shared one.
- Tayside's data comes from `tayside/weather/refresh_page.py` (mode `page_script`), which wraps the
  existing `refresh_weather.py` (LOCS, AIR) and parses rivers, floods, tides, bathing and overflows,
  the five blocks the hourly task used to copy out of page text by hand. On the 20:43 data of
  22 Nov it reproduced the hand-written tides, bathing and overflows exactly
  (`tayside/weather/test_refresh_page.py`).

## Live forecast in the reader's browser (22 Nov)

`parts/live.js` goes into every board through the `{{CODE:live}}` slot (default in `build.py`;
an area opts out by naming `code/empty.js`). When the page opens or a town is chosen, the
browser asks Open-Meteo for that town and replaces its now, hourly and 8-day figures; the
conditions line then reads "Live Open-Meteo conditions for ... at <time>". `omBlock()` is a copy
of `om_rows.place_block()`, checks included; `test_live.py` runs both on the same saved answers
and edge cases (run from `test_build.py`; needs node). If the request fails or a check fails,
the hourly snapshot stays. It works on the GitHub Pages copies (the CSP from `tools/harden.py`
allows `connect-src https://api.open-meteo.com`), never on claude.ai artifact links, which block
requests to other sites. It costs no Claude tokens. Air, rivers, floods, tides, bathing and
sewage stay hourly.

## East Kent (22 Nov)

- Six towns (`static/TOWNS.js`), each with its own flood areas, gauges, beaches, release filter and tide
  table; its code is in `areas/east-kent/code/` (rivers.js: floods; sewage.js: overflows and releases;
  coast.js: tides, bathing, air, walks, Right now, setTab, init). The chosen town is remembered.
- `areas/<area>/sections/<name>.html`, if present, replaces the shared section (East Kent: air, tides,
  bathing, walks).
- Data: `east-kent/weather/refresh_page.py` builds all six towns with `om_rows.place_block` (the
  scraper's `other_towns` now asks for `OM_PARAMS`), air with the old `build_air`, overflows and floods
  (the hourly task's steps 4d and 4g, by hand until now), and the release history from Southern
  Water's Rivers and Seas Watch (`bathing_releases`, `bathing_release_history`; by hand, last 2 Oct).
- Tides: full tables in `areas/east-kent/tides/` (2026-2027); each refresh embeds yesterday to +13 days.
- Text message: `east-kent/weather/sms_text.py` applies the old prompt's STEP 7 rules in code.

## Not done yet

- Plymouth & Ivybridge (26 Nov): made from East Kent's area by `plymouth/weather/make_template_area.py`; the old Plymouth page had East Kent's 49 functions, so only the ones Plymouth changed (overflows, air, bathing, tides, floods, the chart script) are its own. Data: `plymouth/weather/refresh_page.py` (tests: `test_refresh_page.py`).
- Live on the template (22 Nov): West Herts and Neath Port Talbot. Ammanford switches at its
  first run on 23 Nov; Tayside waits for its new hourly prompt to be approved.
- Flood text is now escaped in the Flood Warnings section too (the top banner already
  escaped it); checked in Chrome with a hostile item.
