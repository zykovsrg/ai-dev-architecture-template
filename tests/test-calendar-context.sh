#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMP="$(mktemp -d /private/tmp/calendar-context-test.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/ai/tmp"

PLAN="$($ROOT/scripts/calendar-context.py plan --hub "$TMP" --anchor 2026-09-10 --timezone Europe/Kirov --calendar-id cal-1)"
python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["ranges"] == [{"start":"2026-08-11","end":"2026-10-11"}]' <<<"$PLAN"

$ROOT/scripts/calendar-context.py ingest --hub "$TMP" --anchor 2026-09-10 --timezone Europe/Kirov --calendar-id cal-1 --start 2026-08-11 --end 2026-10-11 <<'JSON'
{"source":"Apple Calendar / EventKit","timezone":"Europe/Kirov","events":[{"id":"e1","calendar_id":"cal-1","title":"SEO publication","start":"2026-09-09T10:00:00+03:00","end":"2026-09-09T11:00:00+03:00","timezone":"Europe/Kirov","all_day":false},{"id":"e2","calendar_id":"cal-1","title":"Deadline","start":"2026-09-20T00:00:00+03:00","end":"2026-09-21T00:00:00+03:00","timezone":"Europe/Kirov","all_day":true}]}
JSON

CONTEXT="$TMP/ai/tmp/calendar-context.json"
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert len(p["days"]) == 61; assert p["days"]["2026-09-09"]["events"][0]["title"] == "SEO publication"; assert p["days"]["2026-09-20"]["events"][0]["title"] == "Deadline"' "$CONTEXT"

NEXT="$($ROOT/scripts/calendar-context.py plan --hub "$TMP" --anchor 2026-09-11 --timezone Europe/Kirov --calendar-id cal-1)"
python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["ranges"] == [{"start":"2026-09-11","end":"2026-09-12"},{"start":"2026-10-11","end":"2026-10-12"}]' <<<"$NEXT"

$ROOT/scripts/calendar-context.py ingest --hub "$TMP" --anchor 2026-09-11 --timezone Europe/Kirov --calendar-id cal-1 --start 2026-10-11 --end 2026-10-12 <<'JSON'
{"source":"Apple Calendar / EventKit","timezone":"Europe/Kirov","events":[]}
JSON
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert "2026-08-11" not in p["days"]; assert "2026-10-11" in p["days"]' "$CONTEXT"

echo "calendar context tests passed"
