#!/usr/bin/env bash
set -euo pipefail

# Install, refresh, or remove the guarded Apple Calendar policy MCP inside a hub.
# It copies code only. Calendar access is never requested here.
#
# HUB_CALENDAR_SKIP_BRIDGE=1 skips the macOS bridge build (used by fixture-Hub
# tests that only need the tool directory and .mcp.json entry, not a signed app).
SOURCE_ROOT=""; HUB_DIR=""; MODE="apply"; ACTION="install"
die() { echo "ERROR: $*" >&2; exit 1; }
usage() { echo "Usage: sync-calendar-policy.sh --source REPO_DIR --hub HUB_DIR [--remove] [--dry-run]" >&2; }
while [ "$#" -gt 0 ]; do
  case "$1" in
    --source) shift; [ "$#" -gt 0 ] || die "--source requires a directory"; SOURCE_ROOT="$1" ;;
    --hub) shift; [ "$#" -gt 0 ] || die "--hub requires a directory"; HUB_DIR="$1" ;;
    --remove) ACTION="remove" ;;
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
TOOL_DIR="$HUB_DIR/tools/apple-calendar-policy"; ALLOWLIST_DIR="$HUB_DIR/.local/apple-calendar"; ALLOWLIST="$ALLOWLIST_DIR/allowlist.json"
MCP_JSON="$HUB_DIR/.mcp.json"

remove_mcp_server() {
  # Rewrites .mcp.json in place, deleting only the hub_calendar key. Every
  # other server (and the rest of the file) is preserved byte-for-byte in
  # content, formatting aside.
  local mcp_json="$1"
  [ -f "$mcp_json" ] || return 0
  MCP_JSON_PATH="$mcp_json" python3 - <<'PY'
import json
import os

path = os.environ["MCP_JSON_PATH"]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
servers = data.get("mcpServers")
if isinstance(servers, dict) and "hub_calendar" in servers:
    del servers["hub_calendar"]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
PY
}

add_mcp_server_if_missing() {
  # Adds the hub_calendar entry only when absent; an existing entry (possibly
  # user-edited) is never overwritten. Other servers are preserved.
  local mcp_json="$1" hub_dir="$2"
  MCP_JSON_PATH="$mcp_json" HUB_DIR_PATH="$hub_dir" python3 - <<'PY'
import json
import os

path = os.environ["MCP_JSON_PATH"]
hub_dir = os.environ["HUB_DIR_PATH"]
if os.path.isfile(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
else:
    data = {}
servers = data.setdefault("mcpServers", {})
if "hub_calendar" not in servers:
    servers["hub_calendar"] = {
        "command": f"{hub_dir}/tools/apple-calendar-policy/.venv/bin/python",
        "args": ["-m", "hub_calendar_policy"],
        "env": {
            "PYTHONPATH": f"{hub_dir}/tools/apple-calendar-policy/src",
            "HUB_CALENDAR_ALLOWLIST": f"{hub_dir}/.local/apple-calendar/allowlist.json",
            "HUB_CALENDAR_BRIDGE": f"{hub_dir}/tools/apple-calendar-policy/bridge/HubCalendarBridge.app/Contents/MacOS/HubCalendarBridge",
        },
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
PY
}

if [ "$ACTION" = "remove" ]; then
  if [ "$MODE" = "dry-run" ]; then
    echo "Would remove $TOOL_DIR"
    echo "Would remove the hub_calendar entry from $MCP_JSON (other servers kept)"
    echo ".local/apple-calendar/ and calendar snapshots are kept"
    exit 0
  fi
  rm -rf "$TOOL_DIR"
  remove_mcp_server "$MCP_JSON"
  echo "Removed guarded Calendar policy MCP from $TOOL_DIR"
  echo "The calendar allowlist and any snapshots were left untouched."
  exit 0
fi

POLICY_SRC="$SOURCE_ROOT/modules/calendar/policy"
for required in src/hub_calendar_policy/__main__.py src/hub_calendar_policy/server.py bridge/hub_eventkit_bridge.swift bridge/SHA256SUMS pyproject.toml; do
  [ -f "$POLICY_SRC/$required" ] || die "source is missing modules/calendar/policy/$required"
done
(cd "$POLICY_SRC/bridge" && shasum -a 256 -c SHA256SUMS >/dev/null 2>&1) || die "calendar policy bridge checksum mismatch; refusing to install"
if [ "$MODE" = "dry-run" ]; then
  echo "Would install guarded Calendar policy MCP into $TOOL_DIR"
  [ -e "$ALLOWLIST" ] && echo "Existing allowlist is preserved: $ALLOWLIST" || echo "Would create empty allowlist: $ALLOWLIST"
  if [ -f "$MCP_JSON" ] && python3 -c "import json,sys; sys.exit(0 if 'hub_calendar' in json.load(open('$MCP_JSON')).get('mcpServers', {}) else 1)" 2>/dev/null; then
    echo "Existing .mcp.json hub_calendar entry is preserved: $MCP_JSON"
  else
    echo "Would add .mcp.json hub_calendar entry: $MCP_JSON"
  fi
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
if [ "$(uname -s)" = "Darwin" ] && [ "${HUB_CALENDAR_SKIP_BRIDGE:-0}" != "1" ]; then
  BRIDGE_EXECUTABLE="$(bash "$(dirname "$0")/build-calendar-bridge.sh" --bridge-dir "$TOOL_DIR/bridge" | tail -1)"
  [ -x "$BRIDGE_EXECUTABLE" ] || die "the bridge bundle was not built"
  echo "Bridge executable: $BRIDGE_EXECUTABLE"
elif [ "${HUB_CALENDAR_SKIP_BRIDGE:-0}" = "1" ]; then
  echo "Bridge build skipped: HUB_CALENDAR_SKIP_BRIDGE=1."
else
  echo "Bridge build skipped: Apple EventKit is available only on macOS."
fi

mkdir -p "$ALLOWLIST_DIR"
if [ ! -e "$ALLOWLIST" ]; then
  printf '%s\n' '{"calendar_ids": []}' > "$ALLOWLIST"
  echo "Created empty calendar allowlist: $ALLOWLIST"
fi
if ! grep -Fqx '/.local/' "$HUB_DIR/.gitignore" 2>/dev/null; then printf '%s\n' '/.local/' >> "$HUB_DIR/.gitignore"; fi
add_mcp_server_if_missing "$MCP_JSON" "$HUB_DIR"
echo "Installed guarded Calendar policy MCP into $TOOL_DIR"
echo "No calendar is selected and no Calendar access was requested."
