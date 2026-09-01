#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
BRIDGE="$ROOT/calendar-policy/bridge"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

[ -f "$BRIDGE/hub_eventkit_bridge.swift" ] || fail "missing local EventKit bridge"
[ -f "$BRIDGE/Info.plist" ] || fail "missing bridge Info.plist"
[ -f "$BRIDGE/SHA256SUMS" ] || fail "missing bridge checksum manifest"

(cd "$BRIDGE" && shasum -a 256 -c SHA256SUMS >/dev/null) || fail "bridge checksum mismatch"

grep -Fq 'requestFullAccessToEvents' "$BRIDGE/hub_eventkit_bridge.swift" || fail "bridge lost its access gate"
grep -Fq 'authorizationStatus' "$BRIDGE/hub_eventkit_bridge.swift" || fail "bridge lost its promptless status path"
grep -Fq 'responsibility_spawnattrs_setdisclaim' "$BRIDGE/hub_eventkit_bridge.swift" \
  || fail "bridge lost its own-identity re-spawn"

# EventKit's all-day end is inclusive and the policy layer's is exclusive. Only
# the bridge converts, and nothing above it can notice if that conversion goes
# missing, so its presence is checked here.
grep -Fq 'inclusiveEnd(end)' "$BRIDGE/hub_eventkit_bridge.swift" \
  || fail "bridge lost the all-day end conversion on write"
grep -Fq 'exclusiveEnd(event.endDate)' "$BRIDGE/hub_eventkit_bridge.swift" \
  || fail "bridge lost the all-day end conversion on read"
grep -Fq 'byAdding: .day' "$BRIDGE/hub_eventkit_bridge.swift" \
  || fail "bridge shifts all-day boundaries by seconds instead of calendar days"

# Without this key macOS refuses the Calendar prompt without ever showing it.
/usr/libexec/PlistBuddy -c 'Print :NSCalendarsFullAccessUsageDescription' "$BRIDGE/Info.plist" >/dev/null 2>&1 \
  || fail "Info.plist is missing NSCalendarsFullAccessUsageDescription"
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$BRIDGE/Info.plist")" = "HubCalendarBridge" ] \
  || fail "Info.plist names an unexpected executable"

# Building only compiles and signs; it never runs the bridge or reads Calendar.
if command -v swiftc >/dev/null 2>&1; then
  BUILD_DIR="$(mktemp -d)"
  trap 'rm -rf "$BUILD_DIR"' EXIT
  cp "$BRIDGE/hub_eventkit_bridge.swift" "$BRIDGE/Info.plist" "$BUILD_DIR/"
  executable="$(bash "$ROOT/scripts/build-calendar-bridge.sh" --bridge-dir "$BUILD_DIR" 2>/dev/null | tail -1)"
  [ -x "$executable" ] || fail "the bridge bundle did not build"
  codesign --verify "$BUILD_DIR/HubCalendarBridge.app" 2>/dev/null || fail "the built bundle is not signed"
else
  printf 'SKIP: swiftc is unavailable, bridge build not checked.\n'
fi

printf 'PASS: local EventKit bridge is present and buildable.\n'
