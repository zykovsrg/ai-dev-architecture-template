#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SOURCE="$(cd "$ROOT/../.." && pwd -P)"
source "$SOURCE/tests/helpers/shell-scenarios.sh"
TMP="$(mktemp -d "${TMPDIR:-/private/tmp}/calendar-context-scenarios.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/ai/tmp"
CONTEXT="$TMP/ai/tmp/calendar-context.json"

# Нейтральная фикстура предыдущего дня: подготовка не вызывает проверяемый код.
seed_previous_day() {
  python3 - "$CONTEXT" <<'PY'
from datetime import date, timedelta
import json, sys
start = date(2026, 8, 11)
days = {(start + timedelta(days=n)).isoformat(): {"events": [], "fetched_at": "2026-09-10T00:00:00+03:00"} for n in range(61)}
with open(sys.argv[1], "w") as output:
    json.dump({"schema_version": 1, "anchor_date": "2026-09-10", "timezone": "Europe/Kirov", "calendar_ids": ["cal-1"], "days": days}, output)
PY
}

initial_range() {
  local rc
  scenario_begin
  scenario_exec rc python3 "$ROOT/scripts/calendar-context.py" plan --hub "$TMP" --anchor 2026-09-10 --timezone Europe/Kirov --calendar-id cal-1 >"$TMP/plan"
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 1 ''
  scenario_exec rc /usr/bin/jq -e '.ranges == [{"start":"2026-08-11","end":"2026-10-11"}]' "$TMP/plan"
  scenario_assert_exit 0 "$rc"
  scenario_pass
}

ingests_events() {
  local rc
  scenario_begin
  scenario_exec rc python3 "$ROOT/scripts/calendar-context.py" ingest --hub "$TMP" --anchor 2026-09-10 --timezone Europe/Kirov --calendar-id cal-1 --start 2026-08-11 --end 2026-10-11 <<'JSON'
{"source":"Apple Calendar / EventKit","timezone":"Europe/Kirov","events":[{"id":"e1","calendar_id":"cal-1","title":"SEO publication","start":"2026-09-09T10:00:00+03:00","end":"2026-09-09T11:00:00+03:00","timezone":"Europe/Kirov","all_day":false},{"id":"e2","calendar_id":"cal-1","title":"Deadline","start":"2026-09-20T00:00:00+03:00","end":"2026-09-21T00:00:00+03:00","timezone":"Europe/Kirov","all_day":true}]}
JSON
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 1 ''
  scenario_exec rc /usr/bin/jq -e '(.days | length) == 61 and .days["2026-09-09"].events[0].title == "SEO publication" and .days["2026-09-20"].events[0].title == "Deadline"' "$CONTEXT"
  scenario_assert_exit 0 "$rc"
  scenario_pass
}

incremental_range() {
  local rc
  scenario_begin
  seed_previous_day
  scenario_exec rc python3 "$ROOT/scripts/calendar-context.py" plan --hub "$TMP" --anchor 2026-09-11 --timezone Europe/Kirov --calendar-id cal-1 >"$TMP/plan"
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 1 ''
  scenario_exec rc /usr/bin/jq -e '.ranges == [{"start":"2026-09-11","end":"2026-09-12"},{"start":"2026-10-11","end":"2026-10-12"}]' "$TMP/plan"
  scenario_assert_exit 0 "$rc"
  scenario_pass
}

prunes_expired_day() {
  local rc
  scenario_begin
  seed_previous_day
  scenario_exec rc python3 "$ROOT/scripts/calendar-context.py" ingest --hub "$TMP" --anchor 2026-09-11 --timezone Europe/Kirov --calendar-id cal-1 --start 2026-10-11 --end 2026-10-12 <<'JSON'
{"source":"Apple Calendar / EventKit","timezone":"Europe/Kirov","events":[]}
JSON
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 1 ''
  scenario_exec rc /usr/bin/jq -e '(.days | has("2026-08-11") | not) and (.days | has("2026-10-11"))' "$CONTEXT"
  scenario_assert_exit 0 "$rc"
  scenario_pass
}
scenario_declare initial-month-window initial_range
scenario_declare stores-events-and-day-count ingests_events
scenario_declare next-day-fetches-only-missing-ranges incremental_range
scenario_declare drops-expired-day-and-adds-new-day prunes_expired_day
scenario_main "$@"
