#!/usr/bin/env bash
# Copy the planning scripts and the task/calendar helpers they call into one directory (Hub layout).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
DEST="${1:?usage: stage-scripts.sh <dir>}"
mkdir -p "$DEST/lib"
cp -p "$ROOT"/modules/planning/scripts/*.sh "$DEST/"
cp -p "$ROOT"/modules/planning/scripts/*.py "$DEST/"
cp -p "$ROOT/scripts/task_records.py" "$DEST/"
cp -p "$ROOT/scripts/read-compact-task-index.py" "$DEST/"
cp -p "$ROOT/scripts/lib/calendar-date.sh" "$DEST/lib/"
