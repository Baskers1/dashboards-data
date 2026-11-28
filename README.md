# dashboards-data

Latest snapshot of the scrapekit weather JSON files from Sarah's iMac, for the
cloud scheduled tasks that refresh the hourly weather dashboards.

- `data/*.json` - copies of `dashboards-source/scrapekit/out/<area>.json`
- `data/manifest.json` - `pushed_at`, and per file: `bytes`, `sha256`, `fetched_at`, `mac_mtime`

Why: scheduled tasks used to stage these files from the Mac with
`device_stage_files`, which the Claude app refused with `session_stale_relogin`
whenever nobody had used the app for a while. Reading them from GitHub removes
the Mac from the task's critical path.

How it updates: launchd agent `uk.baskers.dashboards-data.push` runs
`push_data.sh` whenever `scrapekit/out` changes (and every 15 minutes as a
fallback). Only valid JSON is copied. The repo keeps ONE commit (the latest
snapshot), force-updated each time, so it does not grow. Do not commit other
work here. Log: `~/Library/Logs/dashboards-data-push.log`.
