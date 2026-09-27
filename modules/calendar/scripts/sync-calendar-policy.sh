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

# Validates .mcp.json's shape (missing file is fine) without writing anything.
# Prints a status line to stdout ("present"/"absent" for the hub_calendar key)
# and exits 2 with a clear stderr message for malformed JSON so callers can
# stop before making any other change.
mcp_json_check() {
  local mcp_json="$1"
  MCP_JSON_PATH="$mcp_json" python3 - <<'PY'
import json
import os
import sys

path = os.environ["MCP_JSON_PATH"]
if not os.path.isfile(path):
    print("absent-file")
    sys.exit(0)
try:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
except json.JSONDecodeError as error:
    print(f"ERROR: {path} is not valid JSON: {error}", file=sys.stderr)
    sys.exit(2)
except OSError as error:
    print(f"ERROR: could not read {path}: {error}", file=sys.stderr)
    sys.exit(2)
if not isinstance(data, dict):
    print(f"ERROR: {path} must contain a JSON object at the top level", file=sys.stderr)
    sys.exit(2)
servers = data.get("mcpServers", {})
if not isinstance(servers, dict):
    print(f"ERROR: {path}: \"mcpServers\" must be a JSON object", file=sys.stderr)
    sys.exit(2)
print("present" if "hub_calendar" in servers else "absent")
PY
}

# Atomically rewrites .mcp.json: "remove" deletes only the hub_calendar key,
# "install" adds it only if missing. Every other server and the rest of the
# file is preserved. Assumes the shape was already validated by
# mcp_json_check; still refuses the same malformed shapes defensively and
# changes nothing on the filesystem in that case (the temp file, if any, is
# removed).
mcp_json_write() {
  local action="$1" mcp_json="$2" hub_dir="$3"
  MCP_ACTION="$action" MCP_JSON_PATH="$mcp_json" HUB_DIR_PATH="$hub_dir" python3 - <<'PY'
import json
import os
import sys
import tempfile

action = os.environ["MCP_ACTION"]
path = os.environ["MCP_JSON_PATH"]
hub_dir = os.environ["HUB_DIR_PATH"]

if os.path.isfile(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as error:
        print(f"ERROR: {path} is not valid JSON: {error}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict):
        print(f"ERROR: {path} must contain a JSON object at the top level", file=sys.stderr)
        sys.exit(2)
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        print(f"ERROR: {path}: \"mcpServers\" must be a JSON object", file=sys.stderr)
        sys.exit(2)
else:
    data = {}
    servers = {}

data.setdefault("mcpServers", servers)
servers = data["mcpServers"]

changed = False
if action == "remove":
    if "hub_calendar" in servers:
        del servers["hub_calendar"]
        changed = True
elif action == "install":
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
        changed = True
else:
    print(f"ERROR: unknown mcp.json action: {action}", file=sys.stderr)
    sys.exit(2)

if not changed:
    sys.exit(0)

directory = os.path.dirname(path) or "."
os.makedirs(directory, exist_ok=True)
fd, tmp_path = tempfile.mkstemp(prefix=".mcp.json.", dir=directory)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    os.replace(tmp_path, path)
except Exception:
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
    raise
PY
}

# Refuses to remove tool_dir if the hub's tools/ path (or the tool dir itself)
# is a symlink, or if the tool dir resolves outside the Hub. HUB_DIR is
# already a symlink-free realpath (see the "pwd -P" above), so a plain prefix
# check on the resolved path is enough.
check_tool_dir_safe_to_remove() {
  local dir="$1"
  if [ -L "$HUB_DIR/tools" ]; then die "refusing to remove: $HUB_DIR/tools is a symlink"; fi
  if [ -L "$dir" ]; then die "refusing to remove: $dir is a symlink"; fi
  if [ -e "$dir" ]; then
    local resolved
    resolved="$(cd "$dir" && pwd -P)" || die "cannot resolve $dir"
    case "$resolved" in
      "$HUB_DIR"|"$HUB_DIR"/*) ;;
      *) die "refusing to remove: $dir resolves outside the Hub ($resolved)" ;;
    esac
  fi
}

if [ "$ACTION" = "remove" ]; then
  MCP_STATUS="$(mcp_json_check "$MCP_JSON")" || exit $?
  if [ "$MODE" = "dry-run" ]; then
    echo "Would remove $TOOL_DIR"
    if [ "$MCP_STATUS" = "present" ]; then
      echo "Would remove the hub_calendar entry from $MCP_JSON (other servers kept)"
    else
      echo "No hub_calendar entry in $MCP_JSON to remove"
    fi
    echo ".local/apple-calendar/ and calendar snapshots are kept"
    exit 0
  fi
  check_tool_dir_safe_to_remove "$TOOL_DIR"
  mcp_json_write remove "$MCP_JSON" "$HUB_DIR"
  rm -rf "$TOOL_DIR"
  echo "Removed guarded Calendar policy MCP from $TOOL_DIR"
  echo "The calendar allowlist and any snapshots were left untouched."
  exit 0
fi

POLICY_SRC="$SOURCE_ROOT/modules/calendar/policy"
for required in src/hub_calendar_policy/__main__.py src/hub_calendar_policy/server.py bridge/hub_eventkit_bridge.swift bridge/SHA256SUMS pyproject.toml; do
  [ -f "$POLICY_SRC/$required" ] || die "source is missing modules/calendar/policy/$required"
done
(cd "$POLICY_SRC/bridge" && shasum -a 256 -c SHA256SUMS >/dev/null 2>&1) || die "calendar policy bridge checksum mismatch; refusing to install"
MCP_STATUS="$(mcp_json_check "$MCP_JSON")" || exit $?
if [ "$MODE" = "dry-run" ]; then
  echo "Would install guarded Calendar policy MCP into $TOOL_DIR"
  [ -e "$ALLOWLIST" ] && echo "Existing allowlist is preserved: $ALLOWLIST" || echo "Would create empty allowlist: $ALLOWLIST"
  if [ "$MCP_STATUS" = "present" ]; then
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
mcp_json_write install "$MCP_JSON" "$HUB_DIR"
echo "Installed guarded Calendar policy MCP into $TOOL_DIR"
echo "No calendar is selected and no Calendar access was requested."
