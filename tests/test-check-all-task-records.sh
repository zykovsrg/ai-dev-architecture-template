#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TEMP_DIR="$(mktemp -d "$ROOT/.test-task-records.XXXXXX")"
cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

HUB="$TEMP_DIR/hub"
PROJECT="$HUB/projects/demo"
mkdir -p "$PROJECT/ai" "$HUB/ai"

printf '%s\n' '## demo' 'Path: '"$PROJECT" > "$HUB/ai/project-registry.md"
printf '%s\n' '# Current Task' '' 'Status: active' 'Task ID: TASK-demo-20260909-001' '' '## Goal' '' 'Check records' > "$PROJECT/ai/current-task.md"
printf '%s\n' '# Future Tasks' '' '### FT-20260909-001 — Follow up' '' 'Status: ready' > "$PROJECT/ai/future-tasks.md"
printf '%s\n' '# Paused Tasks' > "$PROJECT/ai/paused-tasks.md"

bash "$ROOT/scripts/check-all-task-records.sh" --hub "$HUB" >/dev/null

printf '%s\n' '# Future Tasks' '' '### FT-20260909-001 — Invalid state' '' 'Status: open' > "$PROJECT/ai/future-tasks.md"
if bash "$ROOT/scripts/check-all-task-records.sh" --hub "$HUB" >/dev/null 2>&1; then
  echo 'FAIL: legacy status accepted' >&2
  exit 1
fi
