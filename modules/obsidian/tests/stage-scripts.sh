#!/usr/bin/env bash
# Copy the Obsidian scripts and the task helpers they call into one directory (Hub layout).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
DEST="${1:?usage: stage-scripts.sh <dir>}"
mkdir -p "$DEST/lib"
cp -p "$ROOT"/modules/obsidian/scripts/*.sh "$DEST/"
cp -p "$ROOT/scripts/task_records.py" "$DEST/"
cp -p "$ROOT/scripts/lib/calendar-date.sh" "$DEST/lib/"
