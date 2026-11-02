#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck source=helpers/shell-scenarios.sh
source "$ROOT/tests/helpers/shell-scenarios.sh"
TEMP_DIR="$(mktemp -d "$ROOT/.test-task-records.XXXXXX")"
cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

make_hub() {
  HUB="$(mktemp -d "$TEMP_DIR/hub.XXXXXX")"
  PROJECT="$HUB/projects/demo"
  mkdir -p "$PROJECT/ai" "$HUB/ai"
  printf '%s\n' '## demo' 'Path: '"$PROJECT" > "$HUB/ai/project-registry.md"
  printf '%s\n' '# Current Task' '' 'Status: active' 'Task ID: TASK-demo-20260909-001' '' '## Goal' '' 'Check records' > "$PROJECT/ai/current-task.md"
  printf '%s\n' '# Future Tasks' '' '### FT-20260909-001 — Follow up' '' 'Status: ready' > "$PROJECT/ai/future-tasks.md"
  printf '%s\n' '# Paused Tasks' > "$PROJECT/ai/paused-tasks.md"
}

accepts_canonical_records() {
  make_hub
  scenario_begin
  scenario_accept_exit 1 $'invalid_status\nERROR: demo: invalid future task records\n'
  scenario_exec code bash "$ROOT/modules/tasks/scripts/check-all-task-records.sh" --hub "$HUB"
  scenario_assert_exit 0 "$code"
  scenario_pass
}

rejects_legacy_future_status() {
  make_hub
  printf '%s\n' '# Future Tasks' '' '### FT-20260909-001 — Invalid state' '' 'Status: open' > "$PROJECT/ai/future-tasks.md"
  scenario_begin
  scenario_accept_exit 1 $'invalid_status\nERROR: demo: invalid future task records\n'
  scenario_exec code bash "$ROOT/modules/tasks/scripts/check-all-task-records.sh" --hub "$HUB"
  scenario_assert_exit 1 "$code"
  scenario_pass
}

scenario_declare accepts-canonical-records accepts_canonical_records
scenario_declare rejects-legacy-future-status rejects_legacy_future_status
scenario_main "$@" >/dev/null
