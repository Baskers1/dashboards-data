#!/bin/zsh
# push_data.sh - copy the latest scrapekit weather JSON (and the weather build
# scripts) from dashboards-source into this repo and push a single-commit snapshot.
# Run by launchd (uk.baskers.dashboards-data.push) whenever scrapekit/out changes.
# Cloud scheduled tasks read these files from GitHub instead of staging them
# from the Mac (staging was refused with session_stale_relogin when idle).
# Design: this repo keeps ONLY the latest snapshot. Each push is a fresh orphan
# commit sent with --force-with-lease, so the repo never grows.

set -u
DS=/Users/baskersimac/dashboards-source
SRC=$DS/scrapekit/out
REPO=/Users/baskersimac/dashboards-data
PY=/Users/baskersimac/.pyenv/versions/3.13.15/bin/python3
LOG=/Users/baskersimac/Library/Logs/dashboards-data-push.log
LOCK=/tmp/dashboards-data-push.lock
FILES=(east-kent.json tayside.json west-herts.json plymouth-ivybridge.json ammanford.json neath-port-talbot.json east-kent-civic.json west-herts-civic.json tayside-civic.json plymouth-civic.json neath-port-talbot-civic.json neath-port-talbot-events.json)
# build scripts, mirrored under src/ with the same layout as dashboards-source
SCRIPTS=(scrapekit/scrapers/om_rows.py east-kent/weather/refresh_weather.py east-kent/weather/refresh_page.py east-kent/weather/sms_text.py east-kent/weather/test_refresh_page.py east-kent/weather/fixtures/sources-2026-11-22T2123.json tayside/weather/refresh_weather.py tayside/weather/refresh_page.py tayside/weather/test_refresh_page.py tayside/weather/fixtures/sources-2026-11-22T2043.json tayside/weather/fixtures/page-blocks-2026-11-22T1837.json west-herts/weather/refresh_weather.py plymouth/weather/refresh_weather.py plymouth/weather/refresh_page.py plymouth/weather/test_refresh_page.py plymouth/weather/fixtures/sources-2026-11-26T0929.json ammanford/weather/refresh_weather.py neath-port-talbot/weather/refresh_weather.py neath-port-talbot/weather/npt_flood_areas.json ammanford/build/amm_watch.py ammanford/build/amm_whatson.py ammanford/build/check_links.js ammanford/build/harden_links.py ammanford/build/page_check.py ammanford/build/page_consts.js ammanford/build/page_consts.py ammanford/build/test_amm_watch.py ammanford/build/test_amm_whatson.py ammanford/build/test_pages.js neath-port-talbot/build/npt_whatson.py neath-port-talbot/build/test_npt_whatson.py neath-port-talbot/build/test_pages.js neath-port-talbot/build/fixtures/scrape.json neath-port-talbot/build/shells/whatson.html neath-port-talbot/build/shells/season.html neath-port-talbot/build/shells/big.html neath-port-talbot/build/urls.json scrapekit/scrapers/npt_events.py neath-port-talbot/whats-on/data/state.json plymouth/whats-on-companions/build_companions.py plymouth/whats-on-companions/test_build_companions.py)
# public page files of the Tech direction map (tech-briefs repo stays private;
# these two files hold only what the public page shows), mirrored under src/tech-briefs/
TB=/Users/baskersimac/GitHub/tech-briefs
TECH=(tools/direction-map/updates.json tools/direction-map/out/index.html)
export GIT_TERMINAL_PROMPT=0
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin

log() { print -r -- "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

# one run at a time
if ! mkdir "$LOCK" 2>/dev/null; then
  # stale lock older than 10 minutes is removed
  if [[ -n $(find "$LOCK" -maxdepth 0 -mmin +10 2>/dev/null) ]]; then rmdir "$LOCK"; mkdir "$LOCK" || exit 0; else exit 0; fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

sleep 5   # let a scraper finish writing its file

mkdir -p "$REPO/data"
changed=0
for f in $FILES; do
  s="$SRC/$f"; d="$REPO/data/$f"
  [[ -f "$s" ]] || { log "missing $f"; continue; }
  if ! "$PY" -c 'import json,sys; json.load(open(sys.argv[1]))' "$s" 2>/dev/null; then
    log "invalid JSON, kept previous copy: $f"; continue
  fi
  if ! cmp -s "$s" "$d"; then cp -p "$s" "$d.tmp" && mv "$d.tmp" "$d"; changed=1; fi
done

for p in $SCRIPTS; do
  s="$DS/$p"; d="$REPO/src/$p"
  [[ -f "$s" ]] || { log "missing script $p"; continue; }
  if [[ "$p" == *.py ]] && ! "$PY" -m py_compile "$s" 2>/dev/null; then log "script does not compile, kept previous copy: $p"; continue; fi
  if ! cmp -s "$s" "$d"; then mkdir -p "${d:h}"; cp -p "$s" "$d.tmp" && mv "$d.tmp" "$d"; changed=1; fi
done

# Shared weather page template (weather-template/), mirrored under src/weather-template/
# for the hourly weather tasks that build their page from it. Every file except Python
# caches; fixtures/ is included so a task can run the tests before it publishes.
for s in $DS/weather-template/**/*(.N); do
  p=${s#$DS/}
  [[ $p == */__pycache__/* || $p == *.pyc ]] && continue
  d="$REPO/src/$p"
  if [[ "$p" == *.py ]] && ! "$PY" -m py_compile "$s" 2>/dev/null; then log "script does not compile, kept previous copy: $p"; continue; fi
  if [[ "$p" == *.json ]] && ! "$PY" -c 'import json,sys; json.load(open(sys.argv[1]))' "$s" 2>/dev/null; then log "invalid JSON, kept previous copy: $p"; continue; fi
  if ! cmp -s "$s" "$d"; then mkdir -p "${d:h}"; cp -p "$s" "$d.tmp" && mv "$d.tmp" "$d"; changed=1; fi
done

for p in $TECH; do
  s="$TB/$p"; d="$REPO/src/tech-briefs/$p"
  [[ -f "$s" ]] || { log "missing tech file $p"; continue; }
  if [[ "$p" == *.json ]] && ! "$PY" -c 'import json,sys; json.load(open(sys.argv[1]))' "$s" 2>/dev/null; then log "invalid JSON, kept previous copy: $p"; continue; fi
  if ! cmp -s "$s" "$d"; then mkdir -p "${d:h}"; cp -p "$s" "$d.tmp" && mv "$d.tmp" "$d"; changed=1; fi
done

[[ $changed -eq 1 ]] || exit 0

# manifest: when each file was written on the Mac and its own fetched_at
"$PY" - "$REPO/data" "$SRC" <<'PYEOF'
import json, os, sys, hashlib, datetime as dt
data, src = sys.argv[1], sys.argv[2]
out = {"pushed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "files": {}}
for name in sorted(os.listdir(data)):
    if not name.endswith(".json") or name == "manifest.json":
        continue
    p = os.path.join(data, name)
    b = open(p, "rb").read()
    try:
        fa = json.loads(b).get("fetched_at")
    except Exception:
        fa = None
    sp = os.path.join(src, name)
    mt = os.path.getmtime(sp) if os.path.exists(sp) else os.path.getmtime(p)
    out["files"][name] = {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
        "fetched_at": fa,
        "mac_mtime": dt.datetime.fromtimestamp(mt, dt.timezone.utc).isoformat(timespec="seconds")}
json.dump(out, open(os.path.join(data, "manifest.json"), "w"), indent=1)
PYEOF

cd "$REPO" || exit 1
git checkout -q --orphan snap 2>>"$LOG" || { log "orphan checkout failed"; exit 1; }
git add -A data src README.md push_data.sh uk.baskers.dashboards-data.push.plist 2>/dev/null
git -c user.name="Baskers1" -c user.email="80006080+Baskers1@users.noreply.github.com" \
  commit -q -m "snapshot $(date -u '+%Y-%m-%dT%H:%M:%SZ')" 2>>"$LOG" || { log "commit failed"; git checkout -q main 2>/dev/null; exit 1; }
git branch -q -M snap main
if git push -q --force-with-lease origin main 2>>"$LOG"; then
  git fetch -q origin main 2>>"$LOG"
  log "pushed $(git rev-parse --short HEAD)"
else
  log "PUSH FAILED"
  exit 1
fi
