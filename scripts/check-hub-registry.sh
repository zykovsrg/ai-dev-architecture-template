#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${1:-.}"
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
ROOTS_FILE="$HUB_DIR/ai/allowed-roots.md"
REGISTRY_FILE="$HUB_DIR/ai/project-registry.md"

die() { echo "ERROR: $*" >&2; exit 1; }
[ -f "$ROOTS_FILE" ] || die "missing $ROOTS_FILE"
[ -f "$REGISTRY_FILE" ] || die "missing $REGISTRY_FILE"

root_contains() {
  local candidate="$1" root canonical_root
  while IFS= read -r root; do
    root="${root#- }"
    [ -d "$root" ] || continue
    canonical_root="$(cd "$root" && pwd -P)"
    case "$candidate/" in "$canonical_root/"*) return 0 ;; esac
  done < <(grep -E '^- /' "$ROOTS_FILE" || true)
  return 1
}

status_ok() {
  case "$1" in active|paused|archived|missing|registration-pending) return 0 ;; esac
  return 1
}

ids=""
current_id=""
while IFS= read -r line; do
  case "$line" in
    '## '*)
      current_id="${line#\#\# }"
      printf '%s\n' "$ids" | grep -Fxq "$current_id" && die "duplicate project ID: $current_id"
      ids="${ids}${current_id}
"
      ;;
    'Status: '*) status_ok "${line#Status: }" || die "invalid status for $current_id" ;;
    'Path: '*)
      path="${line#Path: }"
      if [ -d "$path" ]; then
        canonical_path="$(cd "$path" && pwd -P)"
        root_contains "$canonical_path" || die "project path outside allowed roots: $path"
      else
        root_contains "$path" || die "project path outside allowed roots: $path"
      fi
      ;;
    'Card: '*) [ -f "$HUB_DIR/${line#Card: }" ] || die "missing card for $current_id" ;;
  esac
done < "$REGISTRY_FILE"

echo "Registry check passed"
