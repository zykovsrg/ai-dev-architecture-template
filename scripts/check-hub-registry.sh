#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${1:-.}"
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
ROOTS_FILE="$HUB_DIR/ai/allowed-roots.md"
REGISTRY_FILE="$HUB_DIR/ai/project-registry.md"

die() { echo "ERROR: $*" >&2; exit 1; }
[ -f "$ROOTS_FILE" ] || die "missing $ROOTS_FILE"
[ -f "$REGISTRY_FILE" ] || die "missing $REGISTRY_FILE"

validate_allowed_roots() {
  local root canonical_root
  while IFS= read -r root; do
    root="${root#- }"
    [ -n "$root" ] || die "allowed root must be a nonempty absolute path"
    case "$root" in /*) ;; *) die "allowed root must be a nonempty absolute path" ;; esac
    [ -d "$root" ] || die "allowed root does not exist: $root"
    canonical_root="$(cd "$root" && pwd -P)"
    [ "$canonical_root" = "//" ] && canonical_root="/"
    [ "$canonical_root" != "/" ] || die "allowed root must not be /"
  done < <(grep -E '^- ' "$ROOTS_FILE" || true)
}

root_contains() {
  local candidate="$1" root canonical_root
  while IFS= read -r root; do
    root="${root#- }"
    [ -d "$root" ] || die "allowed root does not exist: $root"
    canonical_root="$(cd "$root" && pwd -P)"
    case "$candidate/" in "$canonical_root/"*) return 0 ;; esac
  done < <(grep -E '^- ' "$ROOTS_FILE" || true)
  return 1
}

canonicalize_project_path() {
  local path="$1" remaining component resolved child
  case "$path" in
    /*) remaining="${path#/}" ;;
    *) return 1 ;;
  esac

  resolved="/"
  while [ -n "$remaining" ]; do
    component="${remaining%%/*}"
    if [ "$remaining" = "$component" ]; then
      remaining=""
    else
      remaining="${remaining#*/}"
    fi

    case "$component" in
      ''|.) ;;
      ..)
        if [ -d "$resolved" ]; then
          resolved="$(cd "$resolved/.." && pwd -P)" || return 1
        else
          resolved="${resolved%/*}"
          [ -n "$resolved" ] || resolved="/"
        fi
        ;;
      *)
        if [ "$resolved" = "/" ]; then
          child="/$component"
        else
          child="$resolved/$component"
        fi
        if [ -L "$child" ] && [ ! -d "$child" ]; then
          return 1
        elif [ -d "$child" ]; then
          resolved="$(cd "$child" && pwd -P)" || return 1
        else
          resolved="$child"
        fi
        ;;
    esac
  done

  printf '%s\n' "$resolved"
}

status_ok() {
  case "$1" in active|paused|archived|missing|registration-pending) return 0 ;; esac
  return 1
}

reset_entry() {
  entry_name=""
  entry_type=""
  entry_status=""
  entry_path=""
  entry_tags=""
  entry_card=""
}

validate_entry_schema() {
  [ -n "$current_id" ] || return 0
  [ -n "$entry_name" ] || die "missing Name for $current_id"
  [ -n "$entry_type" ] || die "missing Type for $current_id"
  [ -n "$entry_status" ] || die "missing Status for $current_id"
  [ -n "$entry_path" ] || die "missing Path for $current_id"
  [ -n "$entry_tags" ] || die "missing Tags for $current_id"
  [ -n "$entry_card" ] || die "missing Card for $current_id"
  grep -Fqx "Project ID: $current_id" "$HUB_DIR/$entry_card" \
    || die "card Project ID mismatch for $current_id"
}

validate_allowed_roots

ids=""
current_id=""
project_count=0
reset_entry
while IFS= read -r line; do
  case "$line" in
    '## '*)
      validate_entry_schema
      current_id="${line#\#\# }"
      printf '%s\n' "$ids" | grep -Fxq "$current_id" && die "duplicate project ID: $current_id"
      ids="${ids}${current_id}
"
      project_count=$((project_count + 1))
      reset_entry
      ;;
    'Name: '*) entry_name="${line#Name: }" ;;
    'Type: '*) entry_type="${line#Type: }" ;;
    'Status: '*)
      entry_status="${line#Status: }"
      status_ok "$entry_status" || die "invalid status for $current_id"
      ;;
    'Path: '*)
      entry_path="${line#Path: }"
      canonical_path="$(canonicalize_project_path "$entry_path")" || die "cannot resolve project path: $entry_path"
      root_contains "$canonical_path" || die "project path outside allowed roots: $entry_path"
      ;;
    'Tags: '*) entry_tags="${line#Tags: }" ;;
    'Card: '*)
      entry_card="${line#Card: }"
      [ -f "$HUB_DIR/$entry_card" ] || die "missing card for $current_id"
      ;;
  esac
done < "$REGISTRY_FILE"
validate_entry_schema

echo "Registry check passed: $project_count projects"
