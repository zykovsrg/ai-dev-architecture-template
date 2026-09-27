#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
VENV="$ROOT/policy/.venv/bin/python"

[ -x "$VENV" ] || { printf 'FAIL: test environment is missing\n' >&2; exit 1; }
PYTHONPATH="$ROOT/policy/src:$ROOT/policy/tests" "$VENV" -m pytest "$ROOT/policy/tests" -q
