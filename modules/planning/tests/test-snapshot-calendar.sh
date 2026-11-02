#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE="$(cd "$HERE/../../.." && pwd -P)"
source "$SOURCE/tests/helpers/shell-scenarios.sh"
TMP="$(mktemp -d "${TMPDIR:-/private/tmp}/snapshot-scenarios.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
STAGE="$TMP/stage"
bash "$HERE/stage-scripts.sh" "$STAGE"
SCRIPT="$STAGE/snapshot-calendar.sh"

make_hub() { local dir; dir="$(mktemp -d "$TMP/hub.XXXXXX")"; mkdir -p "$dir/ai/tmp"; (cd "$dir" && pwd -P); }

creates_exact_snapshot() {
  local hub rc output
  scenario_begin
  hub="$(make_hub)"
  scenario_exec rc bash "$SCRIPT" --hub "$hub" --at 2026-09-08-0930 >"$TMP/path" <<'EVENT'
09:00|10:00|Редактура|Личный
EVENT
  scenario_assert_exit 0 "$rc"
  output="$(< "$TMP/path")"
  scenario_accept_exit 1 ''
  scenario_exec rc bash -c '[[ "$1" =~ ^"$2/ai/tmp/calendar-snapshots/2026-09-08-0930--captured-"[0-9]+--[0-9]+-[0-9]+\.txt$ ]]' _ "$output" "$hub"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc /bin/test -f "$output"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc grep -Fxq '09:00|10:00|Редактура|Личный' "$output"
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 0 ''
  scenario_exec rc wc -l <"$output" >"$TMP/count"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc tr -d ' ' <"$TMP/count" >"$TMP/normalized-count"
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 1 ''
  scenario_exec rc /bin/test "$(< "$TMP/normalized-count")" = 1
  scenario_assert_exit 0 "$rc"
  scenario_pass
}

rejects_bad_line() {
  local hub rc
  scenario_begin
  hub="$(make_hub)"
  scenario_accept_exit 1 $'ERROR: bad event line: мусор\n'
  scenario_exec rc bash "$SCRIPT" --hub "$hub" --at 2026-09-08-0930 <<'EVENT'
мусор
EVENT
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

prunes_old_only() {
  local hub rc now old fresh
  scenario_begin
  hub="$(make_hub)"; now="$(date +%s)"
  mkdir -p "$hub/ai/tmp/calendar-snapshots"
  old="$hub/ai/tmp/calendar-snapshots/2026-08-01-0900--captured-$((now - 15 * 86400))--1-1.txt"
  fresh="$hub/ai/tmp/calendar-snapshots/2026-09-05-0900--captured-$((now - 86400))--2-2.txt"
  : >"$old"; : >"$fresh"
  scenario_exec rc bash "$SCRIPT" --hub "$hub" --prune-only
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 1 ''
  scenario_exec rc /bin/test ! -e "$old"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc /bin/test -f "$fresh"
  scenario_assert_exit 0 "$rc"
  scenario_pass
}

lists_captured_snapshot() {
  local hub rc snapshot
  scenario_begin
  hub="$(make_hub)"
  mkdir -p "$hub/ai/tmp/calendar-snapshots"
  snapshot="$hub/ai/tmp/calendar-snapshots/2026-09-08-0930--captured-1788859800--1-2.txt"
  printf '%s\n' '09:00|10:00|Редактура|Личный' >"$snapshot"
  scenario_exec rc bash "$SCRIPT" --hub "$hub" --list --day 2026-09-08 >"$TMP/list"
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 1 ''
  scenario_exec rc /bin/test "$(< "$TMP/list")" = "$snapshot"
  scenario_assert_exit 0 "$rc"
  scenario_pass
}

rejects_impossible_date() {
  local hub rc
  scenario_begin
  hub="$(make_hub)"
  scenario_accept_exit 1 $'ERROR: --at has an impossible date: 2026-13-45-0930\n'
  scenario_exec rc bash "$SCRIPT" --hub "$hub" --at 2026-13-45-0930 <<'EVENT'
09:00|10:00|Редактура|Личный
EVENT
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

rejects_unknown_option() {
  local hub rc
  scenario_begin
  hub="$(make_hub)"
  scenario_accept_exit 1 $'ERROR: unknown option: --nope\n'
  scenario_exec rc bash "$SCRIPT" --hub "$hub" --nope < /dev/null
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

rejects_extra_field() {
  local hub rc
  scenario_begin
  hub="$(make_hub)"
  scenario_accept_exit 1 $'ERROR: bad event line: 09:00|10:00|Редактура|Личный|лишнее\n'
  scenario_exec rc bash "$SCRIPT" --hub "$hub" --at 2026-09-08-0930 <<'EVENT'
09:00|10:00|Редактура|Личный|лишнее
EVENT
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

rejects_impossible_month() {
  local hub rc
  scenario_begin
  hub="$(make_hub)"
  scenario_accept_exit 1 $'ERROR: --at has an impossible date: 2026-99-99-0900\n'
  scenario_exec rc bash "$SCRIPT" --hub "$hub" --at 2026-99-99-0900 < /dev/null
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

same_time_keeps_both_snapshots() {
  local hub rc first second
  scenario_begin
  hub="$(make_hub)"
  scenario_exec rc bash "$SCRIPT" --hub "$hub" --at 2026-09-09-0900 >"$TMP/first" <<'EVENT'
09:00|10:00|First|Calendar
EVENT
  scenario_assert_exit 0 "$rc"
  scenario_exec rc bash "$SCRIPT" --hub "$hub" --at 2026-09-09-0900 >"$TMP/second" <<'EVENT'
10:00|11:00|Second|Calendar
EVENT
  scenario_assert_exit 0 "$rc"
  first="$(< "$TMP/first")"; second="$(< "$TMP/second")"
  scenario_accept_exit 1 ''
  scenario_exec rc /bin/test "$first" != "$second"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc grep -Fxq '09:00|10:00|First|Calendar' "$first"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc grep -Fxq '10:00|11:00|Second|Calendar' "$second"
  scenario_assert_exit 0 "$rc"
  scenario_pass
}
scenario_declare creates-path-and-exact-content creates_exact_snapshot
scenario_declare rejects-malformed-event-line rejects_bad_line
scenario_declare prunes-only-older-than-fourteen-days prunes_old_only
scenario_declare lists-new-captured-name lists_captured_snapshot
scenario_declare rejects-impossible-date rejects_impossible_date
scenario_declare rejects-unknown-option rejects_unknown_option
scenario_declare rejects-extra-event-field rejects_extra_field
scenario_declare rejects-impossible-month rejects_impossible_month
scenario_declare keeps-both-at-same-time same_time_keeps_both_snapshots
scenario_main "$@"
