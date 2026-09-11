#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TEMP_DIR="$(mktemp -d "$ROOT/.test-hub-update.XXXXXX")"
cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

HUB="$TEMP_DIR/_ai-hub"
mkdir -p "$HUB"
bash "$ROOT/scripts/install.sh" --mode hub "$HUB" >/dev/null
printf '\n<!-- local drift -->\n' >> "$HUB/AGENTS.md"

if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB" --source "$ROOT" --check >"$TEMP_DIR/result" 2>&1; then
  echo "FAIL: --check accepted changed managed file" >&2
  exit 1
fi
grep -Fq 'Managed files differ' "$TEMP_DIR/result"
grep -Fq 'AGENTS.md' "$TEMP_DIR/result"

# The updater must delegate preview/apply to the content-addressed release engine.
grep -Fq 'hub_release.py' "$ROOT/scripts/update-installed-hub.sh" || {
  echo 'FAIL: updater does not use hub_release.py' >&2
  exit 1
}
grep -Fq 'ls-remote' "$ROOT/scripts/update-installed-hub.sh" || {
  echo 'FAIL: remote symbolic ref is not pinned to a commit SHA' >&2
  exit 1
}
grep -Fq 'RESOLVED_SHA' "$ROOT/scripts/update-installed-hub.sh" || {
  echo 'FAIL: updater does not retain one resolved revision' >&2
  exit 1
}
