#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
VENDOR="$ROOT/vendor/apple-calendar-mcp"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

[ -f "$VENDOR/LICENSE" ] || fail "missing vendored license"
[ -f "$VENDOR/pyproject.toml" ] || fail "missing vendored manifest"
[ -f "$VENDOR/uv.lock" ] || fail "missing vendored lock"
[ -f "$VENDOR/UPSTREAM.md" ] || fail "missing upstream metadata"
[ -f "$VENDOR/SHA256SUMS" ] || fail "missing checksum manifest"

grep -Fqx "Upstream-Tag: v0.9.0" "$VENDOR/UPSTREAM.md" || fail "unexpected upstream tag"
grep -Fqx "Upstream-Commit: 94053dc7a48c44303ac1bc351217f8a14a262806" "$VENDOR/UPSTREAM.md" || fail "unexpected upstream commit"
grep -Fqx "Auto-Update: disabled" "$VENDOR/UPSTREAM.md" || fail "automatic updates must be disabled"

(cd "$VENDOR" && shasum -a 256 -c SHA256SUMS) || fail "snapshot checksum mismatch"

printf 'PASS: Apple Calendar upstream snapshot is pinned and intact.\n'
