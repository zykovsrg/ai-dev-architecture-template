#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${1:-.}"
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
ROOTS_FILE="$HUB_DIR/ai/allowed-roots.md"
REGISTRY_FILE="$HUB_DIR/ai/project-registry.md"
PROJECTS_ROOT="$HUB_DIR/projects"

die() { echo "ERROR: $*" >&2; exit 1; }
[ -f "$ROOTS_FILE" ] || die "missing $ROOTS_FILE"
[ -f "$REGISTRY_FILE" ] || die "missing $REGISTRY_FILE"

canonicalize_path() {
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
        if [ -L "$child" ]; then
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

validate_projects_root() {
  local root_count recorded_root canonical_root
  [ -d "$PROJECTS_ROOT" ] || die "missing canonical projects root: $PROJECTS_ROOT"
  [ ! -L "$PROJECTS_ROOT" ] || die "canonical projects root must not be a symlink"
  canonical_root="$(cd "$PROJECTS_ROOT" && pwd -P)"
  [ "$canonical_root" = "$PROJECTS_ROOT" ] \
    || die "canonical projects root must not resolve outside the hub"

  root_count="$(grep -Ec '^- ' "$ROOTS_FILE" || true)"
  [ "$root_count" -eq 1 ] \
    || die "allowed-roots must contain exactly one canonical projects root"
  recorded_root="$(sed -n 's/^- //p' "$ROOTS_FILE")"
  [ "$recorded_root" = "$PROJECTS_ROOT" ] \
    || die "allowed root must be exactly the canonical projects root: $PROJECTS_ROOT"
}

validate_project_path() {
  local raw_path="$1" canonical_path
  canonical_path="$(canonicalize_path "$raw_path")" \
    || die "project path must be a direct child of the canonical projects root: $raw_path"
  [ "$(dirname "$canonical_path")" = "$PROJECTS_ROOT" ] \
    || die "project path must be a direct child of the canonical projects root: $raw_path"
  printf '%s\n' "$canonical_path"
}

status_ok() {
  case "$1" in active|paused|archived|missing|registration-pending) return 0 ;; esac
  return 1
}

validate_card_path() {
  local card_path="$1" card_target canonical_card card_root

  case "$card_path" in
    ai/project-cards/*) ;;
    *) die "card path must stay beneath ai/project-cards: $card_path" ;;
  esac

  card_target="$HUB_DIR/$card_path"
  canonical_card="$(canonicalize_path "$card_target")" \
    || die "card path must stay beneath ai/project-cards: $card_path"
  card_root="$HUB_DIR/ai/project-cards"
  case "$canonical_card" in "$card_root/"*) ;; *)
    die "card path must stay beneath ai/project-cards: $card_path"
    ;;
  esac
  [ -f "$canonical_card" ] || die "missing card for $current_id"
  printf '%s\n' "$canonical_card"
}

reset_entry() {
  entry_name=""
  entry_type=""
  entry_status=""
  entry_path=""
  entry_tags=""
  entry_card=""
  canonical_path=""
}

validate_entry_schema() {
  local canonical_card card_memory canonical_memory card_count
  [ -n "$current_id" ] || return 0
  [ -n "$entry_name" ] || die "missing Name for $current_id"
  [ -n "$entry_type" ] || die "missing Type for $current_id"
  [ -n "$entry_status" ] || die "missing Status for $current_id"
  [ -n "$entry_path" ] || die "missing Path for $current_id"
  [ -n "$entry_tags" ] || die "missing Tags for $current_id"
  [ -n "$entry_card" ] || die "missing Card for $current_id"
  [ "$entry_card" = "ai/project-cards/$current_id.md" ] \
    || die "Card must be ai/project-cards/$current_id.md for $current_id"

  # Validate the project boundary before opening a card or parsing its memory path.
  canonical_path="$(validate_project_path "$entry_path")"
  canonical_card="$(validate_card_path "$entry_card")"
  for card_field in 'Project ID:' 'Name:' 'Type:' 'Status:' 'Last updated:' 'Purpose:' 'Typical tasks:' 'Memory entry point:'; do
    card_count="$(grep -Ec "^$card_field .+" "$canonical_card" || true)"
    [ "$card_count" -ge 1 ] || die "missing card $card_field for $current_id"
    [ "$card_count" -eq 1 ] || die "duplicate card $card_field for $current_id"
  done
  grep -Fqx "Project ID: $current_id" "$canonical_card" \
    || die "card Project ID mismatch for $current_id"
  grep -Fqx "Name: $entry_name" "$canonical_card" \
    || die "card Name mismatch for $current_id"
  grep -Fqx "Type: $entry_type" "$canonical_card" \
    || die "card Type mismatch for $current_id"
  grep -Fqx "Status: $entry_status" "$canonical_card" \
    || die "card Status mismatch for $current_id"
  card_memory="$(sed -n 's/^Memory entry point: //p' "$canonical_card")"
  canonical_memory="$(canonicalize_path "$card_memory")" \
    || die "card Memory entry point must stay beneath the registered project ai directory for $current_id"
  case "$canonical_memory" in "$canonical_path/ai/"*) ;; *)
    die "card Memory entry point must stay beneath the registered project ai directory for $current_id"
    ;;
  esac
}

validate_projects_root

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
    'Path: '*) entry_path="${line#Path: }" ;;
    'Tags: '*) entry_tags="${line#Tags: }" ;;
    'Card: '*) entry_card="${line#Card: }" ;;
  esac
done < "$REGISTRY_FILE"
validate_entry_schema

echo "Registry check passed: $project_count projects"
