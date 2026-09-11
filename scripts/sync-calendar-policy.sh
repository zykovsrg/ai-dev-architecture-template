#!/usr/bin/env bash
set -euo pipefail

# Install or refresh the guarded Apple Calendar policy MCP inside a hub.
# It copies code only. Calendar access is never requested here.
SOURCE_ROOT=""; HUB_DIR=""; MODE="apply"
die() { echo "ERROR: $*" >&2; exit 1; }
usage() { echo "Usage: sync-calendar-policy.sh --source REPO_DIR --hub HUB_DIR [--dry-run]" >&2; }
while [ "$#" -gt 0 ]; do
  case "$1" in
    --source) shift; [ "$#" -gt 0 ] || die "--source requires a directory"; SOURCE_ROOT="$1" ;;
    --hub) shift; [ "$#" -gt 0 ] || die "--hub requires a directory"; HUB_DIR="$1" ;;
    --dry-run) MODE="dry-run" ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
  shift
done
[ -n "$SOURCE_ROOT" ] || die "--source is required"
[ -n "$HUB_DIR" ] || die "--hub is required"
[ -d "$SOURCE_ROOT" ] || die "--source directory not found: $SOURCE_ROOT"
[ -d "$HUB_DIR" ] || die "--hub directory not found: $HUB_DIR"
SOURCE_ROOT="$(cd "$SOURCE_ROOT" && pwd -P)"; HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
POLICY_SRC="$SOURCE_ROOT/calendar-policy"
for required in src/hub_calendar_policy/__main__.py src/hub_calendar_policy/server.py bridge/hub_eventkit_bridge.swift bridge/SHA256SUMS pyproject.toml; do
  [ -f "$POLICY_SRC/$required" ] || die "source is missing calendar-policy/$required"
done
(cd "$POLICY_SRC/bridge" && shasum -a 256 -c SHA256SUMS >/dev/null 2>&1) || die "calendar-policy bridge checksum mismatch; refusing to install"
TOOL_DIR="$HUB_DIR/tools/apple-calendar-policy"; ALLOWLIST_DIR="$HUB_DIR/.local/apple-calendar"; ALLOWLIST="$ALLOWLIST_DIR/allowlist.json"
if [ "$MODE" = "dry-run" ]; then
  echo "Would install guarded Calendar policy MCP into $TOOL_DIR"
  [ -e "$ALLOWLIST" ] && echo "Existing allowlist is preserved: $ALLOWLIST" || echo "Would create empty allowlist: $ALLOWLIST"
  exit 0
fi
mkdir -p "$TOOL_DIR"
RSYNC_EXCLUDES=(--exclude '__pycache__/' --exclude '*.pyc')
rsync -a --delete --delete-excluded "${RSYNC_EXCLUDES[@]}" "$POLICY_SRC/src/" "$TOOL_DIR/src/"
rsync -a --delete --delete-excluded "${RSYNC_EXCLUDES[@]}" "$POLICY_SRC/bridge/" "$TOOL_DIR/bridge/"
cp "$POLICY_SRC/pyproject.toml" "$TOOL_DIR/pyproject.toml"
printf '%s\n' '.venv/' 'bridge/HubCalendarBridge.app/' '__pycache__/' '*.pyc' > "$TOOL_DIR/.gitignore"

# The EventKit bridge is macOS-only. Non-macOS installs still receive the policy
# source so release/smoke checks remain portable; the bridge is built on macOS.
if [ "$(uname -s)" = "Darwin" ]; then
  BRIDGE_EXECUTABLE="$(bash "$(dirname "$0")/build-calendar-bridge.sh" --bridge-dir "$TOOL_DIR/bridge" | tail -1)"
  [ -x "$BRIDGE_EXECUTABLE" ] || die "the bridge bundle was not built"
  echo "Bridge executable: $BRIDGE_EXECUTABLE"
else
  echo "Bridge build skipped: Apple EventKit is available only on macOS."
fi

mkdir -p "$ALLOWLIST_DIR"
if [ ! -e "$ALLOWLIST" ]; then
  printf '%s\n' '{"calendar_ids": []}' > "$ALLOWLIST"
  echo "Created empty calendar allowlist: $ALLOWLIST"
fi
if ! grep -Fqx '/.local/' "$HUB_DIR/.gitignore" 2>/dev/null; then printf '%s\n' '/.local/' >> "$HUB_DIR/.gitignore"; fi
echo "Installed guarded Calendar policy MCP into $TOOL_DIR"
echo "No calendar is selected and no Calendar access was requested."
