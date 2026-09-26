#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MODE="${1:---unit}"

unit() {
  python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
  bash "$ROOT/tests/test_hub_update_check.sh"
  for test in "$ROOT"/tests/test-*.sh; do bash "$test"; done
  for test in "$ROOT"/tests/test-*.py; do python3 "$test"; done
}

integration() {
  bash "$ROOT/scripts/assistant-workflows-test.sh"
  bash "$ROOT/scripts/obsidian-projects-kanban-test.sh"
  bash "$ROOT/scripts/obsidian-task-sync-test.sh"
  bash "$ROOT/scripts/hub-smoke-test.sh"
}

case "$MODE" in
  --unit) unit ;;
  --integration) integration ;;
  --all) unit; integration ;;
  *) echo "Usage: $0 [--unit|--integration|--all]" >&2; exit 64 ;;
esac
