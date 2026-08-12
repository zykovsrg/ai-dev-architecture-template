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

mkdir -p "$HUB_DIR"
rsync -av --ignore-existing "$HUB_TEMPLATE_DIR/" "$HUB_DIR/"

ROOTS_FILE="$HUB_DIR/ai/allowed-roots.md"
for root in "${CANONICAL_ROOTS[@]}"; do
  grep -Fxq -- "- $root" "$ROOTS_FILE" || printf '%s\n' "- $root" >> "$ROOTS_FILE"
done

if [ ! -e "$HUB_DIR/.git" ]; then
  git -C "$HUB_DIR" init >/dev/null 2>&1
fi

for root in "${CANONICAL_ROOTS[@]}"; do
  for candidate in "$root"/*; do
    [ -d "$candidate" ] || continue
    echo "Unregistered candidate: ${candidate##*/}"
  done
done

echo "Registration requires confirmation: run project-register in the hub."
