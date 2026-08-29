#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
VENV="$ROOT/calendar-policy/.venv/bin/python"

[ -x "$VENV" ] || { printf 'FAIL: test environment is missing\n' >&2; exit 1; }
PYTHONPATH="$ROOT/calendar-policy/src:$ROOT/calendar-policy/tests" "$VENV" -m pytest "$ROOT/calendar-policy/tests" -q
