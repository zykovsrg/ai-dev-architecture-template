#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
HUB_DIR="${1:-.}"
die() { echo "ERROR: $*" >&2; exit 1; }

case "$(basename "$HUB_DIR")" in _ai-hub) ;; *) die "Hub directory must be named _ai-hub." ;; esac

path_component="$HUB_DIR"
while [ "$path_component" != "/" ] && [ "$path_component" != "." ]; do
  [ ! -L "$path_component" ] || die "Hub directory path must not contain symlinks."
  path_component="$(dirname "$path_component")"
done

mkdir -p "$(dirname "$HUB_DIR")"
if [ -d "$HUB_DIR" ] && [ -n "$(find "$HUB_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  if [ -f "$HUB_DIR/AGENTS.md" ] && [ -f "$HUB_DIR/ai/architecture.md" ] && [ -f "$HUB_DIR/ai/project-registry.md" ]; then
    echo "Existing Hub detected. Installation does not overwrite/update an installed Hub." >&2
    echo "Review the content-addressed update plan instead:" >&2
    echo "  bash $SCRIPT_DIR/update-installed-hub.sh --hub $HUB_DIR --source $SOURCE_ROOT --dry-run" >&2
    exit 2
  fi
  die "Target is nonempty and is not an installed personal AI Hub."
fi

mkdir -p "$HUB_DIR"
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
PROJECTS_ROOT="$HUB_DIR/projects"

[ -f "$SOURCE_ROOT/scripts/hub_release.py" ] || die "source is missing scripts/hub_release.py"
PLAN_JSON="$(python3 "$SOURCE_ROOT/scripts/hub_release.py" preview --source "$SOURCE_ROOT" --hub "$HUB_DIR")"
PLAN_SHA="$(printf '%s' "$PLAN_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["plan_sha256"])')"
python3 "$SOURCE_ROOT/scripts/hub_release.py" apply --source "$SOURCE_ROOT" --hub "$HUB_DIR" --confirm-plan "$PLAN_SHA" >/dev/null

[ -f "$HUB_DIR/AGENTS.md" ] || die "Hub release did not install AGENTS.md"
[ -f "$HUB_DIR/ai/skills/hub-workflows/SKILL.md" ] || die "Hub release did not install hub-workflows"
[ -f "$HUB_DIR/scripts/read-compact-task-index.py" ] || die "Hub release did not install compact task index"

mkdir -p "$PROJECTS_ROOT"
grep -Fqx '/projects/' "$HUB_DIR/.gitignore" 2>/dev/null || printf '%s\n' '/projects/' >> "$HUB_DIR/.gitignore"
printf '%s\n' '# Allowed Roots' '' "- $PROJECTS_ROOT" > "$HUB_DIR/ai/allowed-roots.md"

if [ -d "$SOURCE_ROOT/calendar-policy" ]; then
  bash "$SCRIPT_DIR/sync-calendar-policy.sh" --source "$SOURCE_ROOT" --hub "$HUB_DIR"
fi

if [ ! -e "$HUB_DIR/.git" ]; then git -C "$HUB_DIR" init >/dev/null 2>&1; fi

echo "Installed Personal AI Hub: $HUB_DIR"
echo "No projects were inspected or registered automatically."
echo "Registration, creation, and migration each require their documented confirmation flow."
