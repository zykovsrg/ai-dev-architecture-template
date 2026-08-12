#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUB_TEMPLATE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/hub-template"

usage() {
  echo "Usage: $0 [--root DIR ...] [HUB_DIR]" >&2
  exit 1
}

ROOTS=()
HUB_DIR=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --root)
      [ "$#" -ge 2 ] || usage
      ROOTS+=("$2")
      shift 2
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

[ "${#ROOTS[@]}" -gt 0 ] || {
  echo "Hub mode requires at least one --root DIR." >&2
  exit 1
}

[ -d "$HUB_TEMPLATE_DIR" ] || {
  echo "Hub template directory not found: $HUB_TEMPLATE_DIR" >&2
  exit 1
}

HOME_ROOT="$(cd "$HOME" && pwd -P)"
CANONICAL_ROOTS=()
for root in "${ROOTS[@]}"; do
  [ -d "$root" ] || {
    echo "Allowed root does not exist: $root" >&2
    exit 1
  }

  canonical_root="$(cd "$root" && pwd -P)"
  [ "$canonical_root" = "//" ] && canonical_root="/"
  case "$canonical_root" in
    /)
      echo "Allowed root must not be /." >&2
      exit 1
      ;;
  esac
  if [ "$canonical_root" = "$HOME_ROOT" ]; then
    echo "Allowed root must not be the home directory." >&2
    exit 1
  fi
  CANONICAL_ROOTS+=("$canonical_root")
done

case "$(basename "$HUB_DIR")" in
  _ai-hub) ;;
  *) echo "Hub directory must be named _ai-hub." >&2; exit 1 ;;
esac

if [ -e "$HUB_DIR" ]; then
  CANONICAL_HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
  if [ -d "$HUB_DIR" ] && [ -n "$(find "$HUB_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ] \
    && { [ ! -f "$HUB_DIR/AGENTS.md" ] || [ ! -f "$HUB_DIR/ai/architecture.md" ] || [ ! -f "$HUB_DIR/ai/allowed-roots.md" ] || [ ! -f "$HUB_DIR/ai/project-registry.md" ]; }; then
    echo "Target is not an installed personal AI hub; refusing to copy into a nonempty directory." >&2
    exit 1
  fi
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

for canonical_root in "${CANONICAL_ROOTS[@]}"; do
  case "$CANONICAL_HUB_DIR/" in "$canonical_root/"*)
    echo "Hub directory must stay outside every allowed root." >&2
    exit 1
    ;;
  esac
done

mkdir -p "$(dirname "$HUB_DIR")"
mkdir -p "$HUB_DIR"
rsync -av --ignore-existing "$HUB_TEMPLATE_DIR/" "$HUB_DIR/"
mkdir -p "$HUB_DIR/scripts"
[ -e "$HUB_DIR/scripts/check-hub-registry.sh" ] \
  || cp "$SCRIPT_DIR/check-hub-registry.sh" "$HUB_DIR/scripts/check-hub-registry.sh"

ROOTS_FILE="$HUB_DIR/ai/allowed-roots.md"
sed '/^- \/absolute\/path\/to\/projects$/d' "$ROOTS_FILE" > "$ROOTS_FILE.tmp"
mv "$ROOTS_FILE.tmp" "$ROOTS_FILE"
for root in "${CANONICAL_ROOTS[@]}"; do
  grep -Fxq -- "- $root" "$ROOTS_FILE" || printf '%s\n' "- $root" >> "$ROOTS_FILE"
done

if [ ! -e "$HUB_DIR/.git" ]; then
  git -C "$HUB_DIR" init >/dev/null 2>&1
fi

for root in "${CANONICAL_ROOTS[@]}"; do
  for candidate in "$root"/*; do
    [ -d "$candidate" ] || continue
    [ -L "$candidate" ] && continue
    canonical_candidate="$(cd "$candidate" && pwd -P)"
    [ "$canonical_candidate" = "$CANONICAL_HUB_DIR" ] && continue
    echo "Unregistered candidate: ${candidate##*/}"
  done
done

echo "Registration requires confirmation: run project-register in the hub."
