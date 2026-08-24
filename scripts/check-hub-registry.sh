#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${1:-.}"
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
ROOTS_FILE="$HUB_DIR/ai/allowed-roots.md"
REGISTRY_FILE="$HUB_DIR/ai/project-registry.md"
PROJECTS_ROOT="$HUB_DIR/projects"
ARCHIPROJECTS_FILE="$HUB_DIR/ai/archiprojects.md"

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

# Entry files stay equal in meaning; only the tool-specific header lines may differ.
# This is a parity check, not an existence check: a registry fixture that carries
# no entry file at all is out of scope, but one missing half is always an error.
validate_entry_files() {
  local claude="$HUB_DIR/CLAUDE.md" agents="$HUB_DIR/AGENTS.md"
  [ -f "$claude" ] || [ -f "$agents" ] || return 0
  [ -f "$claude" ] || die "missing $claude while AGENTS.md is present"
  [ -f "$agents" ] || die "missing $agents while CLAUDE.md is present"
  diff -q \
    <(grep -v -e '^# Personal AI Hub' -e '^<!-- Tool-specific activation:' "$claude") \
    <(grep -v -e '^# Personal AI Hub' -e '^<!-- Tool-specific activation:' "$agents") \
    >/dev/null \
    || die "CLAUDE.md and AGENTS.md diverge outside their tool-specific header lines"
}

# Existence only: the check never reads project memory content.
validate_project_memory() {
  local project_path="$1" memory_file
  for memory_file in current-task paused-tasks future-tasks project-context decisions changelog; do
    [ ! -L "$project_path/ai/$memory_file.md" ] \
      || die "project memory file must not be a symlink: $current_id ai/$memory_file.md"
    [ -f "$project_path/ai/$memory_file.md" ] \
      || die "missing project memory file for $current_id: ai/$memory_file.md"
  done
}

archiproject_ids=""
archiproject_registry_loaded=0

archiproject_id_known() {
  printf '%s\n' "$archiproject_ids" | grep -Fxq "$1"
}

reset_archiproject_entry_fields() {
  archiproject_id_count=0
  archiproject_name_count=0
  archiproject_status_count=0
  archiproject_target_count=0
  archiproject_unit_count=0
  archiproject_due_count=0
  archiproject_value_id=""
}

archiproject_field_count() {
  case "$1" in
    id) printf '%s\n' "$archiproject_id_count" ;;
    name) printf '%s\n' "$archiproject_name_count" ;;
    status) printf '%s\n' "$archiproject_status_count" ;;
    target) printf '%s\n' "$archiproject_target_count" ;;
    unit) printf '%s\n' "$archiproject_unit_count" ;;
    due) printf '%s\n' "$archiproject_due_count" ;;
  esac
}

increment_archiproject_field() {
  case "$1" in
    id) archiproject_id_count=$((archiproject_id_count + 1)) ;;
    name) archiproject_name_count=$((archiproject_name_count + 1)) ;;
    status) archiproject_status_count=$((archiproject_status_count + 1)) ;;
    target) archiproject_target_count=$((archiproject_target_count + 1)) ;;
    unit) archiproject_unit_count=$((archiproject_unit_count + 1)) ;;
    due) archiproject_due_count=$((archiproject_due_count + 1)) ;;
  esac
}

validate_archiproject_entry() {
  local field
  [ -n "$archiproject_entry_id" ] || return 0
  [ "$archiproject_fence_open" = 1 ] && die "unterminated archiproject registry entry: $archiproject_entry_id"
  [ "$archiproject_fence_closed" = 1 ] || die "missing YAML block for archiproject registry entry: $archiproject_entry_id"
  for field in id name status target unit due; do
    [ "$(archiproject_field_count "$field")" -eq 1 ] \
      || die "missing or duplicate $field in archiproject registry entry: $archiproject_entry_id"
  done
  [ "$archiproject_value_id" = "$archiproject_entry_id" ] \
    || die "archiproject registry entry ID mismatch: $archiproject_entry_id"
  archiproject_id_known "$archiproject_entry_id" \
    && die "duplicate archiproject registry ID: $archiproject_entry_id"
  archiproject_ids="${archiproject_ids}${archiproject_entry_id}
"
}

load_archiproject_registry() {
  local line field
  [ "$archiproject_registry_loaded" = 0 ] || return 0
  [ -f "$ARCHIPROJECTS_FILE" ] || die "missing $ARCHIPROJECTS_FILE"
  [ ! -L "$ARCHIPROJECTS_FILE" ] || die "archiproject registry must not be a symlink"

  archiproject_entry_id=""
  archiproject_fence_open=0
  archiproject_fence_closed=0
  reset_archiproject_entry_fields

  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      '## '*)
        validate_archiproject_entry
        archiproject_entry_id="${line#\#\# }"
        case "$archiproject_entry_id" in
          Schema|'<'*'>') archiproject_entry_id="" ;;
          '') die 'empty archiproject registry heading' ;;
        esac
        archiproject_fence_open=0
        archiproject_fence_closed=0
        reset_archiproject_entry_fields
        ;;
      *)
        [ -n "$archiproject_entry_id" ] || continue
        if [ "$archiproject_fence_open" = 0 ]; then
          [ -z "$line" ] && continue
          [ "$line" = '```yaml' ] \
            || die "missing YAML block for archiproject registry entry: $archiproject_entry_id"
          archiproject_fence_open=1
          continue
        fi
        if [ "$archiproject_fence_closed" = 1 ]; then
          [ -z "$line" ] || die "unexpected content after archiproject registry entry: $archiproject_entry_id"
          continue
        fi
        if [ "$line" = '```' ]; then
          archiproject_fence_open=0
          archiproject_fence_closed=1
          continue
        fi
        for field in id name status target unit due; do
          case "$line" in
            "$field: "*)
              increment_archiproject_field "$field"
              if [ "$field" = id ]; then
                archiproject_value_id="${line#id: }"
              fi
              ;;
          esac
        done
        ;;
    esac
  done < "$ARCHIPROJECTS_FILE"
  validate_archiproject_entry
  archiproject_registry_loaded=1
}

validate_archiproject_metadata() {
  local canonical_card="$1" primary contribution related related_id seen_related
  local primary_count contribution_count related_count

  primary_count="$(grep -Ec '^Primary archiproject: ' "$canonical_card" || true)"
  contribution_count="$(grep -Ec '^Archiproject contribution: ' "$canonical_card" || true)"
  related_count="$(grep -Ec '^Related archiprojects: ' "$canonical_card" || true)"
  [ "$primary_count" -eq 0 ] && [ "$contribution_count" -eq 0 ] && [ "$related_count" -eq 0 ] && return 0
  [ "$primary_count" -eq 1 ] && [ "$contribution_count" -eq 1 ] && [ "$related_count" -eq 1 ] \
    || die "archiproject fields must be supplied together for $current_id"

  primary="$(sed -n 's/^Primary archiproject: //p' "$canonical_card")"
  contribution="$(sed -n 's/^Archiproject contribution: //p' "$canonical_card")"
  related="$(sed -n 's/^Related archiprojects: //p' "$canonical_card")"
  [ -n "$primary" ] && [ -n "$contribution" ] && [ -n "$related" ] \
    || die "archiproject fields must be non-empty for $current_id"
  load_archiproject_registry

  if [ "$primary" = none ]; then
    [ "$contribution" = none ] \
      || die "archiproject contribution must be none when primary archiproject is none for $current_id"
  else
    archiproject_id_known "$primary" \
      || die "unknown primary archiproject for $current_id: $primary"
    [[ "$contribution" =~ ^[0-9]+([.][0-9]+)?$ ]] && awk "BEGIN { exit !($contribution > 0) }" \
      || die "archiproject contribution must be a positive number for $current_id"
  fi

  [ "$related" = none ] && return 0
  seen_related=""
  IFS=',' read -r -a related_ids <<< "$related"
  for related_id in "${related_ids[@]}"; do
    related_id="${related_id## }"
    related_id="${related_id%% }"
    [ -n "$related_id" ] || die "related archiproject must not be empty for $current_id"
    printf '%s\n' "$seen_related" | grep -Fxq "$related_id" \
      && die "duplicate related archiproject for $current_id: $related_id"
    seen_related="${seen_related}${related_id}
"
  done
  for related_id in "${related_ids[@]}"; do
    related_id="${related_id## }"
    related_id="${related_id%% }"
    archiproject_id_known "$related_id" \
      || die "unknown related archiproject for $current_id: $related_id"
    [ "$related_id" != "$primary" ] \
      || die "related archiproject must not equal primary archiproject for $current_id"
  done
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

  case "$entry_status" in
    active|paused) validate_project_memory "$canonical_path" ;;
  esac
  validate_archiproject_metadata "$canonical_card"
}

# A directory without the hub- prefix is a leftover from a pre-1.3 hub whose
# update did not remove the superseded path.
validate_skill_namespace() {
  local skills_dir="$HUB_DIR/ai/skills" skill_dir
  [ -d "$skills_dir" ] || return 0
  for skill_dir in "$skills_dir"/*/; do
    [ -d "$skill_dir" ] || continue
    case "$(basename "$skill_dir")" in
      hub-*) ;;
      *) die "hub skill directory must be named hub-*: ai/skills/$(basename "$skill_dir")" ;;
    esac
  done
}

validate_entry_files
validate_skill_namespace
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

# Reverse direction: the registry loop above proves every entry has a directory.
# This proves the operator sees directories that have no entry. Names only —
# nothing inside a project is opened. A warning, never an error: the router only
# ever opens registered paths, and hub-project-migrate legitimately leaves a
# moved folder unregistered until its separate registration confirmation.
warn_unregistered_directories() {
  local child name
  for child in "$PROJECTS_ROOT"/*/; do
    [ -d "$child" ] || continue
    name="$(basename "$child")"
    if printf '%s\n' "$ids" | grep -Fxq "$name"; then
      continue
    fi
    echo "WARNING: unregistered directory in projects root: $name" >&2
  done
}

warn_unregistered_directories

echo "Registry check passed: $project_count projects"
