#!/usr/bin/env bash
set -euo pipefail

# Ask macOS for Calendar access once, on behalf of the bridge bundle itself.
#
# The bundle must be started through LaunchServices for macOS to treat it as the
# responsible process and show the prompt; a bridge spawned by an MCP client is
# attributed to that client instead. Run this after any rebuild, because a new
# signature invalidates the stored decision.
#
# Granting access reads no calendar and changes no event.

BRIDGE_DIR=""
TIMEOUT_SECONDS=60

die() {
  echo "ERROR: $*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bridge-dir) shift; [ "$#" -gt 0 ] || die "--bridge-dir requires a directory"; BRIDGE_DIR="$1" ;;
    --timeout) shift; [ "$#" -gt 0 ] || die "--timeout requires seconds"; TIMEOUT_SECONDS="$1" ;;
    -h|--help) echo "Usage: grant-calendar-access.sh --bridge-dir DIR [--timeout SECONDS]"; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
  shift
done

[ -n "$BRIDGE_DIR" ] || die "--bridge-dir is required"
BRIDGE_DIR="$(cd "$BRIDGE_DIR" && pwd -P)"
APP="$BRIDGE_DIR/HubCalendarBridge.app"
EXECUTABLE="$APP/Contents/MacOS/HubCalendarBridge"

[ -d "$APP" ] || die "bridge bundle not found: $APP (build it first)"
[ -x "$EXECUTABLE" ] || die "bridge executable not found: $EXECUTABLE"

current_status() {
  "$EXECUTABLE" status | sed -n 's/.*"permission":"\([a-z_]*\)".*/\1/p'
}

before="$(current_status)"
if [ "$before" = "granted" ]; then
  echo "Calendar access is already granted to the bridge bundle."
  exit 0
fi

echo "Asking macOS for Calendar access. Approve the prompt that appears."
open -a "$APP" --args request

waited=0
while [ "$waited" -lt "$TIMEOUT_SECONDS" ]; do
  sleep 2
  waited=$((waited + 2))
  if [ "$(current_status)" = "granted" ]; then
    echo "Calendar access granted to the bridge bundle."
    echo "No calendar is selected yet; the allowlist decides what can be read."
    exit 0
  fi
done

echo "Calendar access was not granted within ${TIMEOUT_SECONDS}s (status: $(current_status))." >&2
echo "If no prompt appeared, check System Settings > Privacy & Security > Calendars." >&2
exit 1
