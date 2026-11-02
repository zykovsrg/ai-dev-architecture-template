#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SOURCE="$(cd "$ROOT/../.." && pwd -P)"
source "$SOURCE/tests/helpers/shell-scenarios.sh"
WORK="$(mktemp -d "${TMPDIR:-/private/tmp}/calendar-install-scenarios.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# Проверяем исходный установщик; его соседний сборщик заменён безопасной фикстурой.
mkdir -p "$WORK/subject" "$WORK/bin"
cp "$ROOT/scripts/sync-calendar-policy.sh" "$WORK/subject/sync-calendar-policy.sh"
SYNC="$WORK/subject/sync-calendar-policy.sh"
cat > "$WORK/subject/build-calendar-bridge.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
[ "$#" -eq 2 ] && [ "$1" = --bridge-dir ] || exit 91
app="$2/HubCalendarBridge.app"
mkdir -p "$app/Contents/MacOS"
cp "$2/Info.plist" "$app/Contents/Info.plist"
printf '#!/bin/sh\nexit 99\n' > "$app/Contents/MacOS/HubCalendarBridge"
chmod +x "$app/Contents/MacOS/HubCalendarBridge"
printf '%s\n' "$app" >> "${BUILD_LOG:?}"
printf '%s\n' "$app/Contents/MacOS/HubCalendarBridge"
STUB
cat > "$WORK/bin/uname" <<'STUB'
#!/bin/sh
if [ "$#" -eq 1 ] && [ "$1" = -s ]; then printf 'Darwin\n'; else exec /usr/bin/uname "$@"; fi
STUB
chmod +x "$WORK/bin/uname"

expect_ok() {
  local code
  scenario_accept_exit 1 ''
  scenario_exec code "$@"
  scenario_assert_exit 0 "$code"
}

assert_no_find_results() {
  local code found
  scenario_accept_exit 0 ''
  scenario_exec code find "$@" > "$WORK/found-paths"
  scenario_assert_exit 0 "$code"
  found="$(< "$WORK/found-paths")"
  expect_ok test -z "$found"
}

assert_local_ignore_once() {
  local code count
  scenario_accept_exit 1 ''
  scenario_exec code grep -Fxc '/.local/' "$hub/.gitignore" > "$WORK/local-ignore-count"
  scenario_assert_exit 0 "$code"
  count="$(< "$WORK/local-ignore-count")"
  expect_ok test "$count" = 1
}

make_fixture() {
  local name="$1"
  source_dir="$WORK/$name-source"; hub="$WORK/$name-hub"; tool="$hub/tools/apple-calendar-policy"
  mkdir -p "$source_dir/modules/calendar/policy" "$hub"
  cp -R "$ROOT/policy/src" "$ROOT/policy/bridge" "$source_dir/modules/calendar/policy/"
  cp "$ROOT/policy/pyproject.toml" "$source_dir/modules/calendar/policy/pyproject.toml"
  mkdir -p "$source_dir/modules/calendar/policy/src/hub_calendar_policy/__pycache__"
  : > "$source_dir/modules/calendar/policy/src/hub_calendar_policy/__pycache__/server.cpython-314.pyc"
  printf '%s\n' '/projects/' 'my-own-entry/' > "$hub/.gitignore"
}

install_subject() {
  local code
  scenario_accept_exit 0 ''
  scenario_exec code env PATH="$WORK/bin:$PATH" BUILD_LOG="$WORK/build.log" HUB_CALENDAR_SKIP_VENV=1 HUB_CALENDAR_SKIP_BRIDGE=0 \
    bash "$SYNC" --source "$source_dir" --hub "$hub" "$@" >"$WORK/install.out"
  scenario_assert_exit 0 "$code"
}

fresh_install() {
  scenario_begin
  make_fixture fresh
  install_subject
  expect_ok test -f "$tool/src/hub_calendar_policy/__main__.py"
  expect_ok test -f "$tool/bridge/hub_eventkit_bridge.swift"
  expect_ok test -f "$tool/bridge/SHA256SUMS"
  expect_ok test -f "$tool/pyproject.toml"
  expect_ok grep -Fxq '.venv/' "$tool/.gitignore"
  expect_ok grep -Fxq 'bridge/HubCalendarBridge.app/' "$tool/.gitignore"
  expect_ok grep -Fxq '__pycache__/' "$tool/.gitignore"
  expect_ok test -x "$tool/bridge/HubCalendarBridge.app/Contents/MacOS/HubCalendarBridge"
  expect_ok test -s "$WORK/build.log"
  expect_ok test -f "$tool/bridge/HubCalendarBridge.app/Contents/Info.plist"
  expect_ok grep -Fq NSCalendarsFullAccessUsageDescription "$tool/bridge/HubCalendarBridge.app/Contents/Info.plist"
  expect_ok grep -Fq '"calendar_ids": []' "$hub/.local/apple-calendar/allowlist.json"
  expect_ok grep -Fxq '/.local/' "$hub/.gitignore"
  expect_ok grep -Fxq 'my-own-entry/' "$hub/.gitignore"
  assert_no_find_results "$tool" -name '__pycache__' -o -name '*.pyc'
  scenario_pass
}

rerun_clears_cache() {
  scenario_begin
  make_fixture cache
  install_subject
  mkdir -p "$tool/src/hub_calendar_policy/__pycache__"
  : > "$tool/src/hub_calendar_policy/__pycache__/stale.cpython-314.pyc"
  install_subject
  assert_no_find_results "$tool" -name '*.pyc'
  scenario_pass
}

rerun_preserves_selection() {
  scenario_begin
  make_fixture preserve
  install_subject
  printf '%s\n' '{"calendar_ids": ["chosen-calendar"]}' > "$hub/.local/apple-calendar/allowlist.json"
  install_subject
  expect_ok grep -Fq chosen-calendar "$hub/.local/apple-calendar/allowlist.json"
  assert_local_ignore_once
  scenario_pass
}

tampered_source_is_rejected() {
  local code
  scenario_begin
  make_fixture tampered
  printf '\n// tampered\n' >> "$source_dir/modules/calendar/policy/bridge/hub_eventkit_bridge.swift"
  scenario_accept_exit 1 $'ERROR: calendar policy bridge checksum mismatch; refusing to install\n'
  scenario_exec code env PATH="$WORK/bin:$PATH" BUILD_LOG="$WORK/build.log" HUB_CALENDAR_SKIP_VENV=1 HUB_CALENDAR_SKIP_BRIDGE=0 \
    bash "$SYNC" --source "$source_dir" --hub "$hub" >"$WORK/rejected.out"
  scenario_assert_exit 1 "$code"
  expect_ok test ! -e "$hub/tools"
  expect_ok test ! -e "$hub/.local"
  scenario_pass
}

dry_run_writes_nothing() {
  scenario_begin
  make_fixture dry
  install_subject --dry-run
  expect_ok test ! -e "$hub/tools"
  expect_ok test ! -e "$hub/.local"
  expect_ok test ! -e "$hub/.mcp.json"
  scenario_pass
}

scenario_declare policy-fresh-install-and-empty-selection fresh_install
scenario_declare policy-rerun-removes-stale-cache rerun_clears_cache
scenario_declare policy-rerun-preserves-selection-and-ignore rerun_preserves_selection
scenario_declare policy-rejects-tampered-source-without-writes tampered_source_is_rejected
scenario_declare policy-dry-run-writes-nothing dry_run_writes_nothing
scenario_main "$@"
