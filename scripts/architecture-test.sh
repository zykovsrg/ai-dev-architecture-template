#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MODE="${1:---unit}"

unit() {
  python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
  python3 -m unittest discover -s "$ROOT/modules/obsidian/tests" -p 'test_*.py' -v
  python3 -m unittest discover -s "$ROOT/modules/planning/tests" -p 'test_*.py' -v
  bash "$ROOT/tests/test_hub_update_check.sh"
  bash "$ROOT/modules/obsidian/tests/obsidian-task-sync-watch-test.sh"
  for test in "$ROOT"/tests/test-*.sh; do bash "$test"; done
  for test in "$ROOT"/tests/test-*.py; do python3 "$test"; done
  for test in "$ROOT"/modules/planning/tests/test-*.sh; do bash "$test"; done
  for test in "$ROOT"/modules/planning/tests/test-*.py; do python3 "$test"; done
  python3 "$ROOT/scripts/check-module-boundaries.py" --source "$ROOT"
}

integration() {
  bash "$ROOT/scripts/assistant-workflows-test.sh"
  bash "$ROOT/modules/obsidian/tests/obsidian-projects-kanban-test.sh"
  bash "$ROOT/modules/obsidian/tests/obsidian-task-sync-test.sh"
  bash "$ROOT/scripts/hub-smoke-test.sh"
}

case "$MODE" in
  --unit) unit ;;
  --integration) integration ;;
  --all) unit; integration ;;
  *) echo "Usage: $0 [--unit|--integration|--all]" >&2; exit 64 ;;
esac
