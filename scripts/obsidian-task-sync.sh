#!/usr/bin/env bash
# Create local, confirmable proposals for edits to the generated Obsidian board.
set -euo pipefail

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
is_absolute() { [[ "$1" = /* ]]; }
inside() { [[ "$1" == "$2" || "$1" == "$2"/* ]]; }
physical_dir() { cd "$1" && pwd -P; }
hash_file() { shasum -a 256 "$1" | awk '{print $1}'; }
trim() { sed 's/^[[:space:]]*//; s/[[:space:]]*$//' <<< "$1"; }

HUB='' SCOPE='' VAULT='' COMMAND=''
while [ "$#" -gt 0 ]; do
  case "$1" in
    scan|status|dismiss) [ -z "$COMMAND" ] || die 'choose one command'; COMMAND="$1"; shift;;
    --hub|--scope|--vault) [ "$#" -ge 2 ] || die "missing value for $1"; case "$1" in --hub) HUB=$2;; --scope) SCOPE=$2;; --vault) VAULT=$2;; esac; shift 2;;
    *) die "unknown argument: $1";;
  esac
done
[ -n "$COMMAND" ] || die 'usage: scan --hub <absolute-path> --scope <absolute-path> --vault <absolute-path> | status --vault <absolute-path> | dismiss --vault <absolute-path>'

require_safe_vault() {
  [ -n "$VAULT" ] && is_absolute "$VAULT" || die 'vault must be an absolute path'
  [ -d "$VAULT" ] && [ ! -L "$VAULT" ] || die 'vault must be a non-symlink directory'
  VAULT="$(physical_dir "$VAULT")"
  TASKS="$VAULT/Obsidian/Tasks-Kanban.md"
  MANIFEST="$VAULT/Obsidian/AI-Architecture.manifest.json"
  RUNTIME="$VAULT/.ai-architecture-sync"
  PROPOSAL="$RUNTIME/pending-proposal.json"
  [ ! -e "$RUNTIME" ] || { [ -d "$RUNTIME" ] && [ ! -L "$RUNTIME" ]; } || die 'runtime directory is unsafe'
  [ ! -e "$PROPOSAL" ] || { [ -f "$PROPOSAL" ] && [ ! -L "$PROPOSAL" ]; } || die 'proposal path is unsafe'
}

require_safe_paths() {
  [ -n "$HUB" ] && [ -n "$SCOPE" ] || die 'scan requires --hub and --scope'
  is_absolute "$HUB" && is_absolute "$SCOPE" || die 'hub and scope must be absolute paths'
  [ -d "$HUB" ] && [ ! -L "$HUB" ] || die 'hub must be a non-symlink directory'
  HUB="$(physical_dir "$HUB")"
  [ -f "$SCOPE" ] && [ ! -L "$SCOPE" ] || die 'scope must be a regular non-symlink file'
  SCOPE="$(cd "$(dirname "$SCOPE")" && pwd -P)/$(basename "$SCOPE")"
  inside "$SCOPE" "$HUB" || die 'scope must be inside hub'
  require_safe_vault
  [ -f "$TASKS" ] && [ ! -L "$TASKS" ] || die 'missing or unsafe task board'
  [ -f "$MANIFEST" ] && [ ! -L "$MANIFEST" ] || die 'missing or unsafe manifest'
  [ -f "$HUB/ai/project-registry.md" ] && [ ! -L "$HUB/ai/project-registry.md" ] || die 'missing or unsafe project registry'
  /usr/bin/jq -e '.format_version == 3 and (.tasks | type == "array")' "$MANIFEST" >/dev/null || die 'manifest must be format version 3'
  [ ! -e "$PROPOSAL" ] || die 'pending proposal exists; dismiss it before scanning again'
}

column_to_status() {
  case "$1" in
    Ideas) printf idea;; Ready) printf ready;; Active) printf active;; Waiting) printf waiting;; Blocked) printf blocked;; Review) printf review;; Paused) printf paused;; Done) printf done;;
    *) return 1;;
  esac
}
status_to_column() {
  case "$1" in
    idea) printf Ideas;; ready|in_progress) printf Ready;; active) printf Active;; waiting) printf Waiting;; blocked) printf Blocked;; review) printf Review;; paused) printf Paused;; done|completed) printf Done;;
    *) return 1;;
  esac
}
valid_column() { column_to_status "$1" >/dev/null; }

PROJECT_IDS=() PROJECT_NAMES=() PROJECT_PATHS=()
load_projects() {
  local registry="$HUB/ai/project-registry.md" id block name path
  while IFS= read -r id; do
    block="$(awk -v heading="## $id" '$0 == heading {found=1; next} found && /^## / {exit} found {print}' "$registry")"
    name="$(printf '%s\n' "$block" | sed -n 's/^Name: //p' | head -n 1)"
    path="$(printf '%s\n' "$block" | sed -n 's/^Path: //p' | head -n 1)"
    [ -n "$name" ] && [ -n "$path" ] && is_absolute "$path" || die "incomplete registry entry: $id"
    [ -d "$path/ai" ] && [ ! -L "$path" ] && [ ! -L "$path/ai" ] || die "unsafe project path: $id"
    path="$(physical_dir "$path")"
    inside "$path" "$HUB/projects" || die "project path outside hub projects: $id"
    PROJECT_IDS+=("$id"); PROJECT_NAMES+=("$name"); PROJECT_PATHS+=("$path")
  done < <(sed -nE 's/^## ([a-z0-9][a-z0-9-]*)$/\1/p' "$registry")
  [ "${#PROJECT_IDS[@]}" -gt 0 ] || die 'registry is empty'
}

SCOPE_IDS=()
load_scope_and_validate_vault() {
  local id i architecture_index=''
  while IFS= read -r id; do
    id="$(trim "$id")"; [ -n "$id" ] || continue
    [[ "$id" =~ ^[a-z0-9][a-z0-9-]*$ ]] || die "invalid project ID in scope: $id"
    for i in "${!SCOPE_IDS[@]}"; do [ "${SCOPE_IDS[$i]}" = "$id" ] && die "duplicate project ID in scope: $id"; done
    SCOPE_IDS+=("$id")
  done < "$SCOPE"
  [ "${#SCOPE_IDS[@]}" -gt 0 ] || die 'scope is empty'
  for i in "${!PROJECT_IDS[@]}"; do [ "${PROJECT_IDS[$i]}" = ai-dev-architecture ] && architecture_index="$i"; done
  [ -n "$architecture_index" ] || die 'registry has no ai-dev-architecture project'
  [ "$VAULT" = "${PROJECT_PATHS[$architecture_index]}/obsidian-vault" ] || die 'vault must be the local ai-dev-architecture vault'
}

scope_contains() {
  local wanted="$1" id
  for id in "${SCOPE_IDS[@]}"; do [ "$id" = "$wanted" ] && return 0; done
  return 1
}

project_index_for_name() {
  local wanted="$1" i matches=() 
  for i in "${!PROJECT_NAMES[@]}"; do [ "${PROJECT_NAMES[$i]}" = "$wanted" ] && matches+=("$i"); done
  [ "${#matches[@]}" -eq 1 ] || return 1
  printf '%s' "${matches[0]}"
}

KNOWN_IDS=() KNOWN_COLUMNS=() KNOWN_TITLES=() KNOWN_PROJECTS=() KNOWN_PROJECT_IDS=() KNOWN_DUES=() KNOWN_SOURCES=() KNOWN_SHAS=() KNOWN_STATUSES=()
source_record() {
  local source="$1" wanted_id="$2" base result id status title due count
  base="$(basename "$source")"
  case "$base" in
    current-task.md)
      id="$(sed -n '/^## /q; /^Task ID: /s/^Task ID: //p' "$source" | head -n 1)"; id="$(trim "$id")"
      [ "$id" = "$wanted_id" ] || return 1
      status="$(awk '/^## / {exit} /^Status: / {print substr($0, 9); exit}' "$source")"
      title="$(awk '/^## Goal[[:space:]]*$/ {goal=1; next} goal && /^## / {exit} goal && NF {print; exit}' "$source" | sed 's/[[:space:]]*$//')"
      due="$(sed -nE 's/^[[:space:]]*due:[[:space:]]*([0-9]{4}-[0-9]{2}-[0-9]{2})[[:space:]]*$/\1/p' "$source" | head -n 1)"
      printf '%s\t%s\t%s\n' "$status" "$title" "$due"
      ;;
    future-tasks.md)
      result="$(awk -v wanted="$wanted_id" '
        function flush() { if (entry && id == wanted) { print status "\t" title "\t" due; count++ } }
        /^### / { flush(); entry=1; id=$2; status=""; due=""; title=$0; sub(/^### [^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]*/, "", title); next }
        entry && /^Status: / { status=substr($0, 9); next }
        entry && /^[[:space:]]*due:[[:space:]]*[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]*$/ { due=$0; sub(/^[[:space:]]*due:[[:space:]]*/, "", due); sub(/[[:space:]]*$/, "", due) }
        END { flush(); if (count != 1) exit 1 }
      ' "$source")" || return 1
      printf '%s\n' "$result"
      ;;
    paused-tasks.md)
      result="$(awk -v wanted="$wanted_id" '
        function flush() { if (entry && id == wanted) { print status "\t" title "\t"; count++ } }
        /^### / { flush(); entry=1; id=""; status=""; title=$0; sub(/^### [^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]*/, "", title); next }
        entry && /^Task ID: / { id=substr($0, 10); sub(/^[[:space:]]+/, "", id); sub(/[[:space:]]+$/, "", id); next }
        entry && /^Status: / { status=substr($0, 9) }
        END { flush(); if (count != 1) exit 1 }
      ' "$source")" || return 1
      printf '%s\n' "$result"
      ;;
    *) return 1;;
  esac
}

load_known_cards() {
  local task_id project_id source source_sha project_index record status title due column actual_sha
  while IFS=$'\t' read -r task_id project_id source source_sha; do
    [ -n "$task_id" ] && [ -n "$project_id" ] && [ -n "$source" ] && [ -n "$source_sha" ] || die 'invalid manifest task entry'
    [[ "$task_id" =~ ^(TASK-[0-9]{8}-[0-9]{3}|FT-[0-9]{8}-[0-9]+)$ ]] || die "invalid manifest task ID: $task_id"
    [ -f "$source" ] && [ ! -L "$source" ] || die "unsafe manifest source: $task_id"
    inside "$source" "$HUB/projects/$project_id/ai" || die "manifest source outside registered task memory: $task_id"
    scope_contains "$project_id" || die "manifest task project is outside scope: $project_id"
    actual_sha="$(hash_file "$source")"; [ "$actual_sha" = "$source_sha" ] || die "canonical source differs from manifest: $source"
    project_index=''; for project_index in "${!PROJECT_IDS[@]}"; do [ "${PROJECT_IDS[$project_index]}" = "$project_id" ] && break; done
    [ -n "$project_index" ] && [ "${PROJECT_IDS[$project_index]}" = "$project_id" ] || die "manifest task has unknown project: $task_id"
    record="$(source_record "$source" "$task_id")" || die "manifest task is not a unique canonical record: $task_id"
    IFS=$'\t' read -r status title due <<< "$record"
    column="$(status_to_column "$status")" || die "unsupported canonical status for $task_id: $status"
    KNOWN_IDS+=("$task_id"); KNOWN_COLUMNS+=("$column"); KNOWN_TITLES+=("$title"); KNOWN_PROJECTS+=("${PROJECT_NAMES[$project_index]}"); KNOWN_PROJECT_IDS+=("$project_id"); KNOWN_DUES+=("$due"); KNOWN_SOURCES+=("$source"); KNOWN_SHAS+=("$actual_sha"); KNOWN_STATUSES+=("$status")
  done < <(/usr/bin/jq -r '.tasks[] | [.task_id, .project_id, .source_file, .source_sha256] | @tsv' "$MANIFEST")
  [ "${#KNOWN_IDS[@]}" -gt 0 ] || die 'manifest contains no tasks'
}

BOARD_COLUMNS=() BOARD_IDS=() BOARD_TITLES=() BOARD_PROJECTS=() BOARD_DUES=() BOARD_ERRORS=()
parse_cards() {
  local row column id title project due
  while IFS=$'\034' read -r column id title project due; do
    BOARD_COLUMNS+=("$column"); BOARD_IDS+=("$id"); BOARD_TITLES+=("$title"); BOARD_PROJECTS+=("$project"); BOARD_DUES+=("$due")
    valid_column "$column" || BOARD_ERRORS+=("unknown column: $column")
    [ -n "$title" ] || BOARD_ERRORS+=("card title is empty in column: $column")
    [ -z "$due" ] || [[ "$due" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || BOARD_ERRORS+=("invalid due date for card: $title")
  done < <(awk '
    function flush() { if (card) print column "\034" id "\034" title "\034" project "\034" due }
    /^## / { flush(); card=0; column=$0; sub(/^## /, "", column); next }
    /^- \[[ xX]\] / {
      flush(); card=1; line=$0; sub(/^- \[[ xX]\] /, "", line); id=""; project=""; due=""
      if (match(line, / \^[^[:space:]]+$/)) { id=substr(line, RSTART + 2); line=substr(line, 1, RSTART - 1) }
      title=line; next
    }
    card && /^  - project: / { project=$0; sub(/^  - project: /, "", project); next }
    card && /^  - 📅 / { due=$0; sub(/^  - 📅 /, "", due); next }
    END { flush() }
  ' "$TASKS")
  [ "${#BOARD_COLUMNS[@]}" -gt 0 ] || die 'board contains no task cards'
}

known_index() {
  local wanted="$1" i found=''
  for i in "${!KNOWN_IDS[@]}"; do
    [ "${KNOWN_IDS[$i]}" = "$wanted" ] || continue
    [ -z "$found" ] || return 2
    found="$i"
  done
  [ -n "$found" ] || return 1
  printf '%s' "$found"
}

OPERATION_LINES=() BLOCK_REASONS=() AFFECTED_LINES=()
add_operation() { OPERATION_LINES+=("$1"); }
add_affected_source() { AFFECTED_LINES+=("$1"$'\t'"$2"); }
find_known_title_project() {
  local title="$1" project="$2" i
  for i in "${!KNOWN_IDS[@]}"; do [ "${KNOWN_TITLES[$i]}" = "$title" ] && [ "${KNOWN_PROJECTS[$i]}" = "$project" ] && return 0; done
  return 1
}

diff_cards() {
  local i id known title project due column count project_index status future_source
  for i in "${!KNOWN_IDS[@]}"; do
    count=0
    for id in "${BOARD_IDS[@]}"; do [ "$id" = "${KNOWN_IDS[$i]}" ] && count=$((count + 1)); done
    [ "$count" -eq 1 ] || BLOCK_REASONS+=("missing or duplicate known task ID: ${KNOWN_IDS[$i]}")
  done
  for i in "${!BOARD_IDS[@]}"; do
    id="${BOARD_IDS[$i]}"; title="${BOARD_TITLES[$i]}"; project="${BOARD_PROJECTS[$i]}"; due="${BOARD_DUES[$i]}"; column="${BOARD_COLUMNS[$i]}"
    [ -z "$id" ] || {
      known=''; if known="$(known_index "$id")"; then
        [ "$project" = "${KNOWN_PROJECTS[$known]}" ] || BLOCK_REASONS+=("known task project changed or missing: $id")
        [ "$title" = "${KNOWN_TITLES[$known]}" ] || add_operation "$(/usr/bin/jq -cn --arg id "$id" --arg from "${KNOWN_TITLES[$known]}" --arg to "$title" '{operation:"rename", task_id:$id, from:$from, to:$to}')"
        [ "$column" = "${KNOWN_COLUMNS[$known]}" ] || add_operation "$(/usr/bin/jq -cn --arg id "$id" --arg from "${KNOWN_STATUSES[$known]}" --arg to "$(column_to_status "$column" || true)" '{operation:"set_status", task_id:$id, from:$from, to:$to}')"
        [ "$due" = "${KNOWN_DUES[$known]}" ] || add_operation "$(/usr/bin/jq -cn --arg id "$id" --arg from "${KNOWN_DUES[$known]}" --arg to "$due" '{operation:"set_due", task_id:$id, from:$from, to:$to}')"
        add_affected_source "${KNOWN_SOURCES[$known]}" "${KNOWN_SHAS[$known]}"
      else
        BLOCK_REASONS+=("unknown task ID: $id")
      fi
      continue
    }
    [ -n "$project" ] || { BLOCK_REASONS+=("new card has no project: $title"); continue; }
    project_index="$(project_index_for_name "$project")" || { BLOCK_REASONS+=("new card has unknown or ambiguous project: $project"); continue; }
    find_known_title_project "$title" "$project" && { BLOCK_REASONS+=("new card duplicates a known title without its block ID: $title"); continue; }
    case "$column" in Ideas|Ready|Blocked) ;; *) BLOCK_REASONS+=("new card uses unsupported future status: $column"); continue;; esac
    future_source="${PROJECT_PATHS[$project_index]}/ai/future-tasks.md"
    [ -f "$future_source" ] && [ ! -L "$future_source" ] || { BLOCK_REASONS+=("new card project has unsafe future task source: $project"); continue; }
    add_operation "$(/usr/bin/jq -cn --arg project_id "${PROJECT_IDS[$project_index]}" --arg title "$title" --arg status "$(column_to_status "$column")" --arg due "$due" '{operation:"create_future", project_id:$project_id, title:$title, status:$status, due:$due}')"
    add_affected_source "$future_source" "$(hash_file "$future_source")"
  done
  if [ "${#BOARD_ERRORS[@]}" -gt 0 ]; then BLOCK_REASONS+=("${BOARD_ERRORS[@]}"); fi
}

write_proposal() {
  local state operations affected reasons payload proposal_sha tmp
  if [ "${#OPERATION_LINES[@]}" -eq 0 ] && [ "${#BLOCK_REASONS[@]}" -eq 0 ]; then
    printf 'board matches canonical task records\n'
    return 0
  fi
  if [ "${#OPERATION_LINES[@]}" -eq 0 ]; then operations='[]'; else operations="$(printf '%s\n' "${OPERATION_LINES[@]}" | /usr/bin/jq -s .)"; fi
  if [ "${#AFFECTED_LINES[@]}" -eq 0 ]; then affected='[]'; else affected="$(printf '%s\n' "${AFFECTED_LINES[@]}" | sort -u | /usr/bin/jq -R 'split("\t") | {source_file: .[0], source_sha256: .[1]}' | /usr/bin/jq -s .)"; fi
  if [ "${#BLOCK_REASONS[@]}" -eq 0 ]; then state='ready'; reasons='[]'; else state='blocked'; reasons="$(printf '%s\n' "${BLOCK_REASONS[@]}" | sed '/^$/d' | /usr/bin/jq -R . | /usr/bin/jq -s .)"; fi
  payload="$(/usr/bin/jq -n --arg state "$state" --arg board_sha256 "$(hash_file "$TASKS")" --arg manifest_sha256 "$(hash_file "$MANIFEST")" --argjson affected_sources "$affected" --argjson operations "$operations" --argjson blocked_reasons "$reasons" '{state:$state, board_sha256:$board_sha256, manifest_sha256:$manifest_sha256, affected_sources:$affected_sources, operations:$operations, blocked_reasons:$blocked_reasons}')"
  proposal_sha="$(printf '%s' "$payload" | shasum -a 256 | awk '{print $1}')"
  mkdir -p "$RUNTIME"; [ -d "$RUNTIME" ] && [ ! -L "$RUNTIME" ] || die 'cannot create safe runtime directory'
  tmp="$(mktemp "$RUNTIME/.pending-proposal.json.XXXXXX")"
  trap 'rm -f "$tmp"' EXIT
  /usr/bin/jq -n --arg proposal_sha256 "$proposal_sha" --argjson payload "$payload" '$payload + {proposal_sha256:$proposal_sha256}' > "$tmp"
  mv -f "$tmp" "$PROPOSAL"
  trap - EXIT
  printf 'created %s (%s)\n' "$PROPOSAL" "$proposal_sha"
}

scan() { require_safe_paths; load_projects; load_scope_and_validate_vault; load_known_cards; parse_cards; diff_cards; write_proposal; }
status() { require_safe_vault; [ -f "$PROPOSAL" ] || die 'no pending proposal'; /usr/bin/jq -e . "$PROPOSAL"; }
dismiss() { require_safe_vault; rm -f -- "$PROPOSAL"; }

case "$COMMAND" in
  scan) scan;;
  status) [ -z "$HUB$SCOPE" ] || die 'status accepts only --vault'; status;;
  dismiss) [ -z "$HUB$SCOPE" ] || die 'dismiss accepts only --vault'; dismiss;;
esac
