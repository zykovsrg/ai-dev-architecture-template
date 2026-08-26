#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUB_TEMPLATE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/hub-template"

usage() {
  echo "Usage: $0 [HUB_DIR]" >&2
  exit 1
}

HUB_DIR=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --root)
      echo "--root is not supported in portable hub mode: projects live in _ai-hub/projects/." >&2
      exit 1
      ;;
    --)
      shift
      [ "$#" -le 1 ] || usage
      HUB_DIR="${1:-.}"
      break
      ;;
    -*)
      usage
      ;;
    *)
      [ -z "$HUB_DIR" ] || usage
      HUB_DIR="$1"
      shift
      ;;
  esac
done

HUB_DIR="${HUB_DIR:-.}"

[ -d "$HUB_TEMPLATE_DIR" ] || {
  echo "Hub template directory not found: $HUB_TEMPLATE_DIR" >&2
  exit 1
}
[ -f "$HUB_TEMPLATE_DIR/ai/skills/hub-workflows/SKILL.md" ] || {
  echo "Hub template is missing mandatory skill: hub-workflows" >&2
  exit 1
}

case "$(basename "$HUB_DIR")" in
  _ai-hub) ;;
  *) echo "Hub directory must be named _ai-hub." >&2; exit 1 ;;
esac

path_component="$HUB_DIR"
while [ "$path_component" != "/" ] && [ "$path_component" != "." ]; do
  if [ -L "$path_component" ]; then
    echo "Hub directory path must not contain symlinks." >&2
    exit 1
  fi
  path_component="$(dirname "$path_component")"
done

if [ -e "$HUB_DIR" ]; then
  CANONICAL_HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
else
  target_parent="$(dirname "$HUB_DIR")"
  missing_suffix=""
  while [ ! -d "$target_parent" ]; do
    [ "$target_parent" != "/" ] || { echo "Cannot resolve hub directory parent." >&2; exit 1; }
    missing_suffix="/$(basename "$target_parent")$missing_suffix"
    target_parent="$(dirname "$target_parent")"
  done
  CANONICAL_HUB_DIR="$(cd "$target_parent" && pwd -P)$missing_suffix/$(basename "$HUB_DIR")"
fi

PROJECTS_ROOT="$CANONICAL_HUB_DIR/projects"

if [ -d "$HUB_DIR" ] && [ -n "$(find "$HUB_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  if [ ! -d "$HUB_DIR/.git" ] \
    || [ ! -f "$HUB_DIR/AGENTS.md" ] \
    || [ ! -f "$HUB_DIR/ai/architecture.md" ] \
    || [ ! -f "$HUB_DIR/ai/allowed-roots.md" ] \
    || [ ! -f "$HUB_DIR/ai/project-registry.md" ] \
    || [ "$(grep -Fxc -- "- $PROJECTS_ROOT" "$HUB_DIR/ai/allowed-roots.md" 2>/dev/null || true)" -ne 1 ] \
    || [ "$(grep -Ec '^- ' "$HUB_DIR/ai/allowed-roots.md" 2>/dev/null || true)" -ne 1 ]; then
    echo "Target is not an installed personal AI hub; refusing to copy into a nonempty directory." >&2
    exit 1
  fi
fi

mkdir -p "$(dirname "$HUB_DIR")"
mkdir -p "$HUB_DIR"
rsync -av --ignore-existing "$HUB_TEMPLATE_DIR/" "$HUB_DIR/"
[ -f "$HUB_DIR/ai/skills/hub-workflows/SKILL.md" ] || {
  echo "Hub install did not copy mandatory skill: hub-workflows" >&2
  exit 1
}
mkdir -p "$HUB_DIR/projects"
grep -Fqx '/projects/' "$HUB_DIR/.gitignore" 2>/dev/null \
  || printf '%s\n' '/projects/' >> "$HUB_DIR/.gitignore"
mkdir -p "$HUB_DIR/scripts"
[ -e "$HUB_DIR/scripts/check-hub-registry.sh" ] \
  || cp "$SCRIPT_DIR/check-hub-registry.sh" "$HUB_DIR/scripts/check-hub-registry.sh"
[ -e "$HUB_DIR/scripts/read-compact-project-index.sh" ] \
  || cp "$SCRIPT_DIR/read-compact-project-index.sh" "$HUB_DIR/scripts/read-compact-project-index.sh"

ROOTS_FILE="$HUB_DIR/ai/allowed-roots.md"
printf '%s\n' '# Allowed Roots' '' "- $PROJECTS_ROOT" > "$ROOTS_FILE"

if [ ! -e "$HUB_DIR/.git" ]; then
  git -C "$HUB_DIR" init >/dev/null 2>&1
fi

echo "No projects were inspected or registered automatically."
echo "Registration requires confirmation: run project-register in the hub."
