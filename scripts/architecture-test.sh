#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MODE="${1:---unit}"

# Модуль «Обсидиан» в архиве с 2026-10-29: его тесты не входят в общие проверки.
unit() {
  python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
  python3 -m unittest discover -s "$ROOT/modules/planning/tests" -p 'test_*.py' -v
  python3 -m unittest discover -s "$ROOT/modules/learning/tests" -p 'test_*.py' -v
  python3 -m unittest discover -s "$ROOT/modules/tasks/tests" -p 'test_*.py' -v
  bash "$ROOT/tests/test_hub_update_check.sh"
  if [ "$(uname -s)" = Darwin ]; then
    bash "$ROOT/scripts/test-refresh-session-inventory.sh"
  else
    printf '%s\n' 'SKIP: Session inventory fixture uses macOS file metadata commands.'
  fi
  for test in "$ROOT"/tests/test-*.sh; do bash "$test"; done
  for test in "$ROOT"/modules/planning/tests/test-*.sh; do bash "$test"; done
  python3 "$ROOT/scripts/check-module-boundaries.py" --source "$ROOT" --strict
}

integration() {
  bash "$ROOT/scripts/assistant-workflows-test.sh"
  bash "$ROOT/scripts/hub-smoke-test.sh"
}

calendar_unit() {
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='-p pytest_asyncio.plugin' \
    bash "$ROOT/modules/calendar/tests/apple-calendar-policy-test.sh"
}

calendar_integration() {
  bash "$ROOT/modules/calendar/tests/calendar-venv-install-test.sh"
  if [ "$(uname -s)" = Darwin ]; then
    bash "$ROOT/modules/calendar/tests/calendar-policy-install-test.sh"
    bash "$ROOT/modules/calendar/tests/apple-calendar-bridge-test.sh"
  else
    printf '%s\n' 'SKIP: Calendar bridge installation and compilation require macOS.'
  fi
}

case "$MODE" in
  --unit) unit ;;
  --integration) integration ;;
  --calendar-unit) calendar_unit ;;
  --calendar-integration) calendar_integration ;;
  --calendar) calendar_unit; calendar_integration ;;
  --mutation) shift; python3 "$ROOT/scripts/mutation-check.py" "$@" ;;
  --all) unit; integration; calendar_unit; calendar_integration; python3 "$ROOT/scripts/mutation-check.py" ;;
  *) echo "Usage: $0 [--unit|--integration|--calendar|--calendar-unit|--calendar-integration|--mutation|--all]" >&2; exit 64 ;;
esac
