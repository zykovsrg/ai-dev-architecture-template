#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TEMP_DIR="$(mktemp -d "$ROOT/.test-memory.XXXXXX")"
cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT
mkdir -p "$TEMP_DIR/hub/ai"
printf '%s\n' '# Workflow observations' '' '- 2028-02-29 | day-plan | friction | valid leap day' > "$TEMP_DIR/hub/ai/workflow-observations.md"
printf '%s\n' '# Workflow context' '' '- 2028-02-29 | short rule | основание: test' > "$TEMP_DIR/hub/ai/workflow-context.md"
bash "$ROOT/scripts/check-workflow-memory.sh" --hub "$TEMP_DIR/hub" >/dev/null

printf '%s\n' '# Workflow observations' '' '- 2026-02-30 | day-plan | friction | impossible date' > "$TEMP_DIR/hub/ai/workflow-observations.md"
if bash "$ROOT/scripts/check-workflow-memory.sh" --hub "$TEMP_DIR/hub" >/dev/null; then
  echo 'FAIL: impossible observation date accepted' >&2
  exit 1
fi
