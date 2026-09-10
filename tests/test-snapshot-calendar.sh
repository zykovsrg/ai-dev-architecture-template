#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TEMP_DIR="$(mktemp -d "$ROOT/.test-snapshot.XXXXXX")"
cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

HUB="$TEMP_DIR/hub"
mkdir -p "$HUB/ai"
first="$(printf '09:00|10:00|First|Calendar\n' | bash "$ROOT/scripts/snapshot-calendar.sh" --hub "$HUB" --at 2026-09-09-0900)"
second="$(printf '10:00|11:00|Second|Calendar\n' | bash "$ROOT/scripts/snapshot-calendar.sh" --hub "$HUB" --at 2026-09-09-0900)"
[ "$first" != "$second" ]
grep -Fqx '09:00|10:00|First|Calendar' "$first"
grep -Fqx '10:00|11:00|Second|Calendar' "$second"

if bash "$ROOT/scripts/snapshot-calendar.sh" --hub "$HUB" --at 2026-02-30-0900 </dev/null; then
  echo 'FAIL: impossible date accepted' >&2
  exit 1
fi

if bash "$ROOT/scripts/snapshot-calendar.sh" --hub "$HUB" --at 2026-99-99-0900 </dev/null; then
  echo 'FAIL: impossible month accepted' >&2
  exit 1
fi
