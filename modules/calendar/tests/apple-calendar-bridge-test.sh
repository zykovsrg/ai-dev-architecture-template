#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SOURCE="$(cd "$ROOT/../.." && pwd -P)"
BRIDGE="$ROOT/policy/bridge"
BUILDER="$ROOT/scripts/build-calendar-bridge.sh"
source "$SOURCE/tests/helpers/shell-scenarios.sh"
WORK="$(mktemp -d "${TMPDIR:-/private/tmp}/calendar-bridge-scenarios.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

expect_ok() {
  local code
  scenario_accept_exit 1 ''
  scenario_exec code "$@"
  scenario_assert_exit 0 "$code"
}

assets_and_checksums() {
  local code
  scenario_begin
  expect_ok test -f "$BRIDGE/hub_eventkit_bridge.swift"
  expect_ok test -f "$BRIDGE/Info.plist"
  expect_ok test -f "$BRIDGE/SHA256SUMS"
  scenario_accept_exit 1 $'shasum: WARNING: 1 computed checksum did NOT match\n'
  scenario_exec code bash -c 'cd "$1" && shasum -a 256 -c SHA256SUMS' calendar-checksum "$BRIDGE" >"$WORK/checksums"
  scenario_assert_exit 0 "$code"
  scenario_pass
}

access_and_identity() {
  local token
  scenario_begin
  for token in requestFullAccessToEvents authorizationStatus responsibility_spawnattrs_setdisclaim; do
    expect_ok grep -Fq "$token" "$BRIDGE/hub_eventkit_bridge.swift"
  done
  scenario_pass
}

all_day_boundaries() {
  local token
  scenario_begin
  for token in 'inclusiveEnd(end)' 'exclusiveEnd(event.endDate)' 'byAdding: .day'; do
    expect_ok grep -Fq "$token" "$BRIDGE/hub_eventkit_bridge.swift"
  done
  scenario_pass
}

timezone_text() {
  local token
  scenario_begin
  for token in 'func isoText(_ date: Date, timezone: TimeZone)' 'formatter.timeZone = timezone' \
    'let eventZone = event.timeZone ?? TimeZone.current' \
    '"start": isoText(event.startDate, timezone: eventZone)' \
    '"end": isoText(event.isAllDay ? (exclusiveEnd(event.endDate) ?? event.endDate) : event.endDate, timezone: eventZone)'; do
    expect_ok grep -Fq "$token" "$BRIDGE/hub_eventkit_bridge.swift"
  done
  scenario_pass
}

bundle_metadata() {
  local code
  scenario_begin
  scenario_accept_exit 1 $'Print: Entry, ":NSCalendarsFullAccessUsageDescription", Does Not Exist\n'
  scenario_exec code /usr/libexec/PlistBuddy -c 'Print :NSCalendarsFullAccessUsageDescription' "$BRIDGE/Info.plist" >"$WORK/usage"
  scenario_assert_exit 0 "$code"
  scenario_accept_exit 1 $'Print: Entry, ":CFBundleExecutable", Does Not Exist\n'
  scenario_exec code /usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$BRIDGE/Info.plist" >"$WORK/executable"
  scenario_assert_exit 0 "$code"
  expect_ok grep -Fxq HubCalendarBridge "$WORK/executable"
  scenario_pass
}

real_compile_and_signature() {
  local code executable compiler developer sdk build="$WORK/build"
  scenario_begin
  command -v swiftc >/dev/null 2>&1 || scenario__die 'swiftc is required for the existing compile contract'
  command -v codesign >/dev/null 2>&1 || scenario__die 'codesign is required for the existing signature contract'
  expect_ok grep -Fq 'swiftc -O -j 2 -num-threads 1' "$BUILDER"
  developer="$(/usr/bin/xcode-select -p)"
  compiler="$developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc"
  sdk="$developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
  if [ ! -x "$compiler" ]; then
    compiler="$developer/usr/bin/swiftc"
    sdk="$developer/SDKs/MacOSX.sdk"
  fi
  [ -x "$compiler" ] && [ -d "$sdk" ] || scenario__die 'configured compiler or SDK is unavailable'
  mkdir -p "$build" "$WORK/bin"
  # Реальный компилятор получает только временный кэш; его код не имитируется.
  cat > "$WORK/bin/swiftc" <<WRAPPER
#!/bin/sh
exec "$compiler" -sdk "$sdk" -module-cache-path "$WORK/module-cache" "\$@"
WRAPPER
  chmod +x "$WORK/bin/swiftc"
  cp "$BRIDGE/hub_eventkit_bridge.swift" "$BRIDGE/Info.plist" "$build/"
  scenario_exec code env PATH="$WORK/bin:$PATH" bash "$BUILDER" --bridge-dir "$build" >"$WORK/build-output"
  scenario_assert_exit 0 "$code"
  executable="$(tail -1 "$WORK/build-output")"
  expect_ok test -x "$executable"
  scenario_exec code codesign --verify "$build/HubCalendarBridge.app"
  scenario_assert_exit 0 "$code"
  # Созданный исполняемый файл никогда не запускается: это только сборка и подпись.
  scenario_pass
}

scenario_declare bridge-assets-and-checksums assets_and_checksums
scenario_declare bridge-access-status-and-own-identity access_and_identity
scenario_declare bridge-all-day-boundaries all_day_boundaries
scenario_declare bridge-timezone-aware-text timezone_text
scenario_declare bridge-bundle-metadata bundle_metadata
scenario_declare bridge-real-compile-and-signature real_compile_and_signature
scenario_main "$@"
