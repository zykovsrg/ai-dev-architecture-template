#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
BRIDGE="$ROOT/calendar-policy/bridge"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

[ -f "$BRIDGE/hub_eventkit_bridge.swift" ] || fail "missing local EventKit bridge"
[ -f "$BRIDGE/SHA256SUMS" ] || fail "missing bridge checksum manifest"

(cd "$BRIDGE" && shasum -a 256 -c SHA256SUMS >/dev/null) || fail "bridge checksum mismatch"

grep -Fq 'requestFullAccessToEvents' "$BRIDGE/hub_eventkit_bridge.swift" || fail "bridge lost its access gate"
grep -Fq 'authorizationStatus' "$BRIDGE/hub_eventkit_bridge.swift" || fail "bridge lost its promptless status path"

# Compilation only; it never runs the bridge and never touches Calendar.
if command -v swiftc >/dev/null 2>&1; then
  swiftc -typecheck "$BRIDGE/hub_eventkit_bridge.swift" || fail "bridge does not compile"
else
  printf 'SKIP: swiftc is unavailable, bridge compilation not checked.\n'
fi

printf 'PASS: local EventKit bridge is present and intact.\n'
