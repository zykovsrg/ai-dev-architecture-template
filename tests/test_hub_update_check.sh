#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TEMP_DIR="$(mktemp -d "$ROOT/.test-hub-update.XXXXXX")"
cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

HUB="$TEMP_DIR/_ai-hub"
mkdir -p "$HUB/scripts" "$HUB/projects"
cp -R "$ROOT/hub-template/." "$HUB/"
cp "$ROOT/scripts/check-hub-registry.sh" "$ROOT/scripts/read-compact-project-index.sh" \
  "$ROOT/scripts/obsidian-task-sync.sh" "$ROOT/scripts/generate-obsidian-projects-kanban.sh" "$HUB/scripts/"
git -C "$HUB" init >/dev/null
printf '\n<!-- local drift -->\n' >> "$HUB/AGENTS.md"

if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB" --source "$ROOT" --check >"$TEMP_DIR/result" 2>&1; then
  echo "FAIL: --check accepted matching version with changed managed file" >&2
  exit 1
fi
grep -Fq 'Managed files differ' "$TEMP_DIR/result"
