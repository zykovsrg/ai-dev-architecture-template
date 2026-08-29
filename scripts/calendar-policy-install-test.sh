#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SYNC="$ROOT/scripts/sync-calendar-policy.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

make_source() {
  local dest="$WORK/$1"
  mkdir -p "$dest/scripts" "$dest/calendar-policy"
  cp -R "$ROOT/calendar-policy/src" "$dest/calendar-policy/src"
  cp -R "$ROOT/calendar-policy/bridge" "$dest/calendar-policy/bridge"
  cp "$ROOT/calendar-policy/pyproject.toml" "$dest/calendar-policy/pyproject.toml"
  printf '%s\n' "$dest"
}

make_hub() {
  local hub="$WORK/$1"
  mkdir -p "$hub"
  printf '%s\n' '/projects/' 'my-own-entry/' > "$hub/.gitignore"
  printf '%s\n' "$hub"
}

# A fresh hub receives the tool, an empty allowlist, and the ignore line.
source_dir="$(make_source source-1)"
hub="$(make_hub hub-1)"
bash "$SYNC" --source "$source_dir" --hub "$hub" >/dev/null

tool="$hub/tools/apple-calendar-policy"
[ -f "$tool/src/hub_calendar_policy/__main__.py" ] || fail "entrypoint was not installed"
[ -f "$tool/bridge/hub_eventkit_bridge.swift" ] || fail "bridge was not installed"
[ -f "$tool/bridge/SHA256SUMS" ] || fail "bridge manifest was not installed"
[ -f "$tool/pyproject.toml" ] || fail "manifest was not installed"
[ -f "$hub/.local/apple-calendar/allowlist.json" ] || fail "allowlist was not created"
grep -Fq '"calendar_ids": []' "$hub/.local/apple-calendar/allowlist.json" \
  || fail "installed allowlist is not empty"
grep -Fqx '/.local/' "$hub/.gitignore" || fail "ignore line was not added"
grep -Fqx 'my-own-entry/' "$hub/.gitignore" || fail "existing ignore entries were lost"

# A rerun must never overwrite a selection the user already made.
printf '%s\n' '{"calendar_ids": ["chosen-calendar"]}' > "$hub/.local/apple-calendar/allowlist.json"
bash "$SYNC" --source "$source_dir" --hub "$hub" >/dev/null
grep -Fq 'chosen-calendar' "$hub/.local/apple-calendar/allowlist.json" \
  || fail "rerun overwrote the user's allowlist"
[ "$(grep -Fxc '/.local/' "$hub/.gitignore")" -eq 1 ] || fail "ignore line was duplicated"

# A bridge that no longer matches its manifest must not be installed.
tampered="$(make_source source-tampered)"
printf '\n// tampered\n' >> "$tampered/calendar-policy/bridge/hub_eventkit_bridge.swift"
hub_tampered="$(make_hub hub-tampered)"
if bash "$SYNC" --source "$tampered" --hub "$hub_tampered" >/dev/null 2>&1; then
  fail "a tampered bridge was installed"
fi
[ ! -e "$hub_tampered/tools" ] || fail "a tampered source left files behind"

# A dry run reports the plan and writes nothing.
hub_dry="$(make_hub hub-dry)"
bash "$SYNC" --source "$source_dir" --hub "$hub_dry" --dry-run >/dev/null
[ ! -e "$hub_dry/tools" ] || fail "dry run installed files"
[ ! -e "$hub_dry/.local" ] || fail "dry run created runtime files"

printf 'PASS: guarded Calendar policy install is safe and repeatable.\n'
