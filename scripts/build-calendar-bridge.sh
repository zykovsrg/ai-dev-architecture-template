#!/usr/bin/env bash
set -euo pipefail

# Build the local EventKit bridge as a real application bundle.
#
# macOS attributes a Calendar prompt to the responsible application, not to the
# process that calls EventKit. A bare script run by an MCP client inherits that
# client's identity, and a client whose Info.plist has no
# NSCalendarsFullAccessUsageDescription is refused silently. A bundle of our own
# carries that description and can own the permission itself.
#
# Building never requests Calendar access and never reads a calendar.

BRIDGE_DIR=""
APP_NAME="HubCalendarBridge"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  build-calendar-bridge.sh --bridge-dir DIR

Builds DIR/HubCalendarBridge.app from DIR/hub_eventkit_bridge.swift and
DIR/Info.plist. Prints the path of the built executable.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bridge-dir) shift; [ "$#" -gt 0 ] || die "--bridge-dir requires a directory"; BRIDGE_DIR="$1" ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
  shift
done

[ -n "$BRIDGE_DIR" ] || die "--bridge-dir is required"
[ -d "$BRIDGE_DIR" ] || die "bridge directory not found: $BRIDGE_DIR"
BRIDGE_DIR="$(cd "$BRIDGE_DIR" && pwd -P)"

SOURCE="$BRIDGE_DIR/hub_eventkit_bridge.swift"
PLIST="$BRIDGE_DIR/Info.plist"
[ -f "$SOURCE" ] || die "missing bridge source: $SOURCE"
[ -f "$PLIST" ] || die "missing bridge Info.plist: $PLIST"

command -v swiftc >/dev/null 2>&1 || die "swiftc is required; install Xcode Command Line Tools"
command -v codesign >/dev/null 2>&1 || die "codesign is required"

# The bundle must declare the Calendar usage description, or macOS refuses the
# prompt exactly the way it refuses a client that lacks it.
/usr/libexec/PlistBuddy -c 'Print :NSCalendarsFullAccessUsageDescription' "$PLIST" >/dev/null 2>&1 \
  || die "Info.plist is missing NSCalendarsFullAccessUsageDescription"

APP="$BRIDGE_DIR/$APP_NAME.app"
MACOS_DIR="$APP/Contents/MacOS"

rm -rf "$APP"
mkdir -p "$MACOS_DIR"
cp "$PLIST" "$APP/Contents/Info.plist"

swiftc -O "$SOURCE" -o "$MACOS_DIR/$APP_NAME" \
  -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker "$PLIST" \
  || die "bridge did not compile"

# An ad-hoc signature is enough for a locally built bundle, and TCC needs the
# bundle to be signed before it will remember a decision about it.
codesign --force --sign - --identifier "com.personal-ai-hub.calendar-bridge" "$APP" \
  || die "could not sign the bridge bundle"

printf '%s\n' "$MACOS_DIR/$APP_NAME"
