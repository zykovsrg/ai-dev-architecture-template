#!/usr/bin/env bash
# Create local, confirmable proposals for edits to the generated Obsidian board.
set -euo pipefail

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
is_absolute() { [[ "$1" = /* ]]; }
inside() { [[ "$1" == "$2" || "$1" == "$2"/* ]]; }
physical_dir() { cd "$1" && pwd -P; }
hash_file() { shasum -a 256 "$1" | awk '{print $1}'; }
trim() { sed 's/^[[:space:]]*//; s/[[:space:]]*$//' <<< "$1"; }

HUB='' SCOPE='' VAULT='' COMMAND='' CONFIRM_PROPOSAL=''
while [ "$#" -gt 0 ]; do
  case "$1" in
    scan|status|dismiss|apply) [ -z "$COMMAND" ] || die 'choose one command'; COMMAND="$1"; shift;;
    --hub|--scope|--vault) [ "$#" -ge 2 ] || die "missing value for $1"; case "$1" in --hub) HUB=$2;; --scope) SCOPE=$2;; --vault) VAULT=$2;; esac; shift 2;;
    --confirm-proposal) [ "$#" -ge 2 ] || die 'missing value for --confirm-proposal'; CONFIRM_PROPOSAL=$2; shift 2;;
    *) die "unknown argument: $1";;
  esac
done
[ -n "$COMMAND" ] || die 'usage: scan --hub <absolute-path> --scope <absolute-path> --vault <absolute-path> | apply --hub <absolute-path> --scope <absolute-path> --vault <absolute-path> --confirm-proposal <sha256> | status --vault <absolute-path> | dismiss --vault <absolute-path>'

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
  [ "$COMMAND" != scan ] || [ ! -e "$PROPOSAL" ] || die 'pending proposal exists; dismiss it before scanning again'
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
  local source="$1" wanted_id="$2" record_source="${3:-$1}" base result id status title due count
  base="$(basename "$record_source")"
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
        function flush() { if (entry && id == wanted) { sub(/[[:space:]]*$/, "", title); print status "\t" title "\t" due; count++ } }
        /^### / { flush(); entry=1; id=$2; status=""; due=""; title=$0; sub(/^### [^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]*/, "", title); next }
        entry && /^Status: / { status=substr($0, 9); next }
        entry && /^[[:space:]]*due:[[:space:]]*[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]*$/ { due=$0; sub(/^[[:space:]]*due:[[:space:]]*/, "", due); sub(/[[:space:]]*$/, "", due) }
        END { flush(); if (count != 1) exit 1 }
      ' "$source")" || return 1
      printf '%s\n' "$result"
      ;;
    paused-tasks.md)
      result="$(awk -v wanted="$wanted_id" '
        function flush() { if (entry && id == wanted) { sub(/[[:space:]]*$/, "", title); print status "\t" title "\t"; count++ } }
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

BOARD_COLUMNS=() BOARD_IDS=() BOARD_TITLES=() BOARD_PROJECTS=() BOARD_DUES=() BOARD_DONE=() BOARD_ERRORS=()
parse_cards() {
  local row column id title project due done_mark extra
  while IFS=$'\034' read -r column id title project due done_mark extra; do
    BOARD_COLUMNS+=("$column"); BOARD_IDS+=("$id"); BOARD_TITLES+=("$title"); BOARD_PROJECTS+=("$project"); BOARD_DUES+=("$due"); BOARD_DONE+=("$done_mark")
    valid_column "$column" || BOARD_ERRORS+=("unknown column: $column")
    [ -n "$title" ] || BOARD_ERRORS+=("card title is empty in column: $column")
    [ -z "$due" ] || [[ "$due" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || BOARD_ERRORS+=("invalid due date for card: $title")
    # A field the synchronizer cannot model would be reverted without ever
    # appearing in the confirmed diff, so refuse the whole board instead.
    [ "$extra" -eq 0 ] || BOARD_ERRORS+=("card has an unsupported field: $title")
  done < <(awk '
    function flush() { if (card) print column "\034" id "\034" title "\034" project "\034" due "\034" done_mark "\034" extra }
    /^## / { flush(); card=0; column=$0; sub(/^## /, "", column); next }
    /^- \[[ xX]\] / {
      flush(); card=1; line=$0; done_mark=substr(line, 4, 1); sub(/^- \[[ xX]\] /, "", line); id=""; project=""; due=""; extra=0
      if (match(line, / \^[^[:space:]]+$/)) { id=substr(line, RSTART + 2); line=substr(line, 1, RSTART - 1) }
      title=line; next
    }
    card && /^  - project: / { project=$0; sub(/^  - project: /, "", project); next }
    card && /^  - 📅 / { due=$0; sub(/^  - 📅 /, "", due); next }
    card && /^[[:space:]]/ { extra=1; next }
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
add_promotion_replacement_sources() {
  local known_index="$1" project_id="${KNOWN_PROJECT_IDS[$1]}" project_index='' source
  for project_index in "${!PROJECT_IDS[@]}"; do [ "${PROJECT_IDS[$project_index]}" = "$project_id" ] && break; done
  [ -n "$project_index" ] && [ "${PROJECT_IDS[$project_index]}" = "$project_id" ] || die "unknown project for promoted task: ${KNOWN_IDS[$known_index]}"
  for source in "${PROJECT_PATHS[$project_index]}/ai/current-task.md" "${PROJECT_PATHS[$project_index]}/ai/paused-tasks.md"; do
    [ -f "$source" ] && [ ! -L "$source" ] || die "unsafe promotion replacement source: $source"
    add_affected_source "$source" "$(hash_file "$source")"
  done
}
record_kind() {
  case "$1" in current-task.md) printf current;; future-tasks.md) printf future;; paused-tasks.md) printf paused;; *) return 1;; esac
}
# Only offer a transition that apply can actually perform. Otherwise the user
# would confirm a proposal that fails halfway through the canonical write.
transition_supported() {
  case "$1" in
    # Pausing needs task-switch and finishing needs task-finish, so the board
    # may only set the states those workflows do not own.
    current-task.md) case "$2" in active|blocked|review) return 0;; *) return 1;; esac;;
    future-tasks.md) case "$2" in idea|ready|blocked|active) return 0;; *) return 1;; esac;;
    paused-tasks.md) case "$2" in paused) return 0;; *) return 1;; esac;;
  esac
  return 1
}
find_known_title_project() {
  local title="$1" project="$2" i
  for i in "${!KNOWN_IDS[@]}"; do [ "${KNOWN_TITLES[$i]}" = "$title" ] && [ "${KNOWN_PROJECTS[$i]}" = "$project" ] && return 0; done
  return 1
}

diff_cards() {
  local i id known title project due column count project_index status future_source j k active_count future_active_count duplicate_project known_base new_status expected_done
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
        known_base="$(basename "${KNOWN_SOURCES[$known]}")"
        if [ "${KNOWN_COLUMNS[$known]}" = Done ]; then expected_done=x; else expected_done=' '; fi
        [ "${BOARD_DONE[$i]}" = "$expected_done" ] || BLOCK_REASONS+=("card checkbox does not match its canonical state: $id")
        if [ "$column" != "${KNOWN_COLUMNS[$known]}" ]; then
          new_status="$(column_to_status "$column" || true)"
          if transition_supported "$known_base" "$new_status"; then
            add_operation "$(/usr/bin/jq -cn --arg id "$id" --arg from "${KNOWN_STATUSES[$known]}" --arg to "$new_status" '{operation:"set_status", task_id:$id, from:$from, to:$to}')"
            [ "$column" != Active ] || [ "$known_base" != future-tasks.md ] || add_promotion_replacement_sources "$known"
          else
            BLOCK_REASONS+=("unsupported status transition for $(record_kind "$known_base") task: $id to column $column")
          fi
        fi
        if [ "$due" != "${KNOWN_DUES[$known]}" ]; then
          if [ "$known_base" = paused-tasks.md ] && [ -n "$due" ]; then
            BLOCK_REASONS+=("due dates are not supported for paused task: $id")
          else
            add_operation "$(/usr/bin/jq -cn --arg id "$id" --arg from "${KNOWN_DUES[$known]}" --arg to "$due" '{operation:"set_due", task_id:$id, from:$from, to:$to}')"
          fi
        fi
        add_affected_source "${KNOWN_SOURCES[$known]}" "${KNOWN_SHAS[$known]}"
      else
        BLOCK_REASONS+=("unknown task ID: $id")
      fi
      continue
    }
    [ "${BOARD_DONE[$i]}" = " " ] || BLOCK_REASONS+=("new card must be unchecked: $title")
    [ -n "$project" ] || { BLOCK_REASONS+=("new card has no project: $title"); continue; }
    project_index="$(project_index_for_name "$project")" || { BLOCK_REASONS+=("new card has unknown or ambiguous project: $project"); continue; }
    find_known_title_project "$title" "$project" && { BLOCK_REASONS+=("new card duplicates a known title without its block ID: $title"); continue; }
    case "$column" in Ideas|Ready|Blocked) ;; *) BLOCK_REASONS+=("new card uses unsupported future status: $column"); continue;; esac
    future_source="${PROJECT_PATHS[$project_index]}/ai/future-tasks.md"
    [ -f "$future_source" ] && [ ! -L "$future_source" ] || { BLOCK_REASONS+=("new card project has unsafe future task source: $project"); continue; }
    add_operation "$(/usr/bin/jq -cn --arg project_id "${PROJECT_IDS[$project_index]}" --arg title "$title" --arg status "$(column_to_status "$column")" --arg due "$due" '{operation:"create_future", project_id:$project_id, title:$title, status:$status, due:$due}')"
    add_affected_source "$future_source" "$(hash_file "$future_source")"
  done
  # Validate the final board state, not each status operation independently.
  # This catches two future tasks moved to Active in the same delta.
  for i in "${!KNOWN_PROJECTS[@]}"; do
    project="${KNOWN_PROJECTS[$i]}"; duplicate_project=0
    for j in "${!KNOWN_PROJECTS[@]}"; do
      [ "$j" -lt "$i" ] || continue
      if [ "${KNOWN_PROJECTS[$j]}" = "$project" ]; then duplicate_project=1; break; fi
    done
    [ "$duplicate_project" -eq 0 ] || continue
    active_count=0; future_active_count=0
    for j in "${!BOARD_IDS[@]}"; do
      [ "${BOARD_COLUMNS[$j]}" = Active ] || continue
      for k in "${!KNOWN_IDS[@]}"; do
        if [ "${BOARD_IDS[$j]}" = "${KNOWN_IDS[$k]}" ] && [ "${KNOWN_PROJECTS[$k]}" = "$project" ]; then
          active_count=$((active_count + 1))
          [ "$(basename "${KNOWN_SOURCES[$k]}")" = future-tasks.md ] && future_active_count=$((future_active_count + 1))
          break
        fi
      done
    done
    # One future task in Active is a promotion and replaces the project's
    # current task. Two future tasks cannot be promoted together.
    [ "$active_count" -le 1 ] || { [ "$active_count" -eq 2 ] && [ "$future_active_count" -eq 1 ]; } || BLOCK_REASONS+=("board would place more than one task in Active for project: $project ($active_count tasks)")
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

APPLY_TARGETS=() APPLY_TEMPS=() APPLY_BACKUPS=()
# Any exit after the canonical files were replaced must put them back, so a
# failed generated refresh never leaves ai/ half-applied.
cleanup_apply_state() { restore_replaced_source_files; local file; for file in "${APPLY_TEMPS[@]:-}"; do [ -z "$file" ] || rm -f -- "$file"; done; }

source_is_safe_task_file() {
  local source="$1" i
  for i in "${!PROJECT_IDS[@]}"; do
    source_is_registered_task_file "$source" "$i" && return 0
  done
  return 1
}

source_is_registered_task_file() {
  local source="$1" project_index="$2" base resolved expected
  base="$(basename "$source")"
  case "$base" in current-task.md|future-tasks.md|paused-tasks.md);; *) return 1;; esac
  [ -f "$source" ] && [ ! -L "$source" ] || return 1
  resolved="$(cd "$(dirname "$source")" && pwd -P)/$base" || return 1
  expected="${PROJECT_PATHS[$project_index]}/ai/$base"
  [ "$resolved" = "$expected" ] && [ -f "$expected" ] && [ ! -L "$expected" ]
}

verify_manifest_sources_are_registered() {
  local task_id project_id source i project_index
  while IFS=$'\t' read -r task_id project_id source; do
    project_index=''
    for i in "${!PROJECT_IDS[@]}"; do [ "${PROJECT_IDS[$i]}" = "$project_id" ] && project_index="$i"; done
    [ -n "$project_index" ] || die "manifest task has unknown project: $task_id"
    scope_contains "$project_id" || die "manifest task project is outside scope: $project_id"
    source_is_registered_task_file "$source" "$project_index" || die "manifest source is not a registered task file: $task_id"
  done < <(/usr/bin/jq -r '.tasks[] | [.task_id, .project_id, .source_file] | @tsv' "$MANIFEST")
}

stage_source() {
  local source="$1" i temp
  for i in "${!APPLY_TARGETS[@]}"; do [ "${APPLY_TARGETS[$i]}" = "$source" ] && return 0; done
  source_is_safe_task_file "$source" || die "unsafe proposal source: $source"
  temp="$(mktemp "$(dirname "$source")/.$(basename "$source").apply.XXXXXX")"
  cp "$source" "$temp"
  APPLY_TARGETS+=("$source"); APPLY_TEMPS+=("$temp")
}

temp_for_source() {
  local source="$1" i
  for i in "${!APPLY_TARGETS[@]}"; do [ "${APPLY_TARGETS[$i]}" = "$source" ] && { printf '%s' "${APPLY_TEMPS[$i]}"; return 0; }; done
  die "proposal source was not staged: $source"
}

proposal_payload() {
  /usr/bin/jq -n \
    --arg state "$(/usr/bin/jq -r '.state' "$PROPOSAL")" \
    --arg board_sha256 "$(/usr/bin/jq -r '.board_sha256' "$PROPOSAL")" \
    --arg manifest_sha256 "$(/usr/bin/jq -r '.manifest_sha256' "$PROPOSAL")" \
    --argjson affected_sources "$(/usr/bin/jq -c '.affected_sources' "$PROPOSAL")" \
    --argjson operations "$(/usr/bin/jq -c '.operations' "$PROPOSAL")" \
    --argjson blocked_reasons "$(/usr/bin/jq -c '.blocked_reasons' "$PROPOSAL")" \
    '{state:$state, board_sha256:$board_sha256, manifest_sha256:$manifest_sha256, affected_sources:$affected_sources, operations:$operations, blocked_reasons:$blocked_reasons}'
}

load_proposal() {
  [ -f "$PROPOSAL" ] || die 'no pending proposal'
  /usr/bin/jq -e '
    .state == "ready" and
    (.proposal_sha256 | type == "string" and test("^[0-9a-f]{64}$")) and
    (.board_sha256 | type == "string" and test("^[0-9a-f]{64}$")) and
    (.manifest_sha256 | type == "string" and test("^[0-9a-f]{64}$")) and
    (.affected_sources | type == "array") and
    (.operations | type == "array") and
    (.blocked_reasons | type == "array")' "$PROPOSAL" >/dev/null || die 'proposal is blocked or malformed'
  PROPOSAL_SHA="$(/usr/bin/jq -r '.proposal_sha256' "$PROPOSAL")"
  [ "$CONFIRM_PROPOSAL" = "$PROPOSAL_SHA" ] || die 'confirmation does not match proposal'
  [ "$(printf '%s' "$(proposal_payload)" | shasum -a 256 | awk '{print $1}')" = "$PROPOSAL_SHA" ] || die 'proposal hash is invalid'
}

verify_board_hash() { [ "$(hash_file "$TASKS")" = "$(/usr/bin/jq -r '.board_sha256' "$PROPOSAL")" ] || die 'proposal is stale: board changed'; }
verify_manifest_hash() { [ "$(hash_file "$MANIFEST")" = "$(/usr/bin/jq -r '.manifest_sha256' "$PROPOSAL")" ] || die 'proposal is stale: manifest changed'; }
verify_every_affected_source_hash() {
  local source expected
  while IFS=$'\t' read -r source expected; do
    source_is_safe_task_file "$source" || die "unsafe proposal source: $source"
    [ "$(hash_file "$source")" = "$expected" ] || die "proposal is stale: canonical source changed: $source"
    stage_source "$source"
  done < <(/usr/bin/jq -r '.affected_sources[] | [.source_file, .source_sha256] | @tsv' "$PROPOSAL")
}

known_source_for() {
  local task_id="$1" index
  index="$(known_index "$task_id")" || die "proposal has unknown task ID: $task_id"
  printf '%s' "${KNOWN_SOURCES[$index]}"
}

PROMOTED_TASK_IDS=() PROMOTED_CURRENT_SOURCES=()
promoted_current_source_for() {
  local task_id="$1" i
  for i in "${!PROMOTED_TASK_IDS[@]}"; do
    [ "${PROMOTED_TASK_IDS[$i]}" = "$task_id" ] || continue
    printf '%s' "${PROMOTED_CURRENT_SOURCES[$i]}"
    return 0
  done
  return 1
}

rename_record() {
  local source="$1" task_id="$2" title="$3" temp base
  temp="$(temp_for_source "$source")"; base="$(basename "$source")"
  # Every branch must rewrite exactly one record. A silent no-op would report a
  # successful apply and then let the rebuild discard the confirmed edit.
  case "$base" in
    current-task.md) NEW_TITLE="$title" perl -0pi -e 'die "rename matched no goal line\n" unless s{(^## Goal[^\S\r\n]*\n\n*)[^\n]*}{$1 . $ENV{NEW_TITLE}}me == 1' "$temp";;
    future-tasks.md) TASK_ID="$task_id" NEW_TITLE="$title" perl -0pi -e 'die "rename matched no future record\n" unless s{^### \Q$ENV{TASK_ID}\E [^\n]*}{"### $ENV{TASK_ID} — $ENV{NEW_TITLE}"}me == 1' "$temp";;
    paused-tasks.md) TASK_ID="$task_id" NEW_TITLE="$title" perl -0pi -e 'die "rename matched no paused record\n" unless s{(^### [0-9]{4}-[0-9]{2}-[0-9]{2} — )[^\n]*(\n(?:(?!^### ).)*?^Task ID: \Q$ENV{TASK_ID}\E$)}{$1 . $ENV{NEW_TITLE} . $2}mse == 1' "$temp";;
  esac || die "cannot rewrite the title of $task_id in $source"
}

set_due_record() {
  local source="$1" task_id="$2" due="$3" temp base
  temp="$(temp_for_source "$source")"; base="$(basename "$source")"
  case "$base" in
    current-task.md)
      DUE="$due" perl -0pi -e 's/^[ \t]*due:[^\n]*(?:\n|\z)//mg; $_ .= "\n" if $ENV{DUE} ne q{} && $_ !~ /\n\z/; $_ .= "due: $ENV{DUE}\n" if $ENV{DUE} ne q{}' "$temp";;
    future-tasks.md)
      TASK_ID="$task_id" DUE="$due" perl -0pi -e 's{(^### \Q$ENV{TASK_ID}\E [^\n]*\n)(.*?)(?=^### |\z)}{my ($head, $body) = ($1, $2); $body =~ s/^[ \t]*due:[^\n]*(?:\n|\z)//mg; $body .= "\n" if length($body) && $body !~ /\n\z/; $body .= "due: $ENV{DUE}\n" if $ENV{DUE} ne q{}; $head . $body}mges' "$temp";;
    paused-tasks.md) [ -z "$due" ] || die "due dates are not supported for paused task: $task_id";;
  esac
}

mark_record_promoted() {
  local source="$1" task_id="$2" temp base
  temp="$(temp_for_source "$source")"; base="$(basename "$source")"
  case "$base" in
    future-tasks.md) TASK_ID="$task_id" perl -0pi -e 's{(^### \Q$ENV{TASK_ID}\E [^\n]*\n.*?^Status: )[^\n]*}{$1 . "promoted"}mse' "$temp";;
    paused-tasks.md) die "cannot promote a paused task: $task_id";;
    *) die "cannot promote current task: $task_id";;
  esac
}

RESERVED_TASK_IDS=()
next_task_id() {
  local date_part max id temp
  date_part="$(date -u +%Y%m%d)"; max=0
  while IFS= read -r id; do [ "$id" -gt "$max" ] && max="$id"; done < <(grep -hE "^Task ID: TASK-${date_part}-[0-9]{3}$" "$HUB"/projects/*/ai/current-task.md "$HUB"/projects/*/ai/paused-tasks.md 2>/dev/null | sed "s/^Task ID: TASK-${date_part}-//")
  if [ "${#APPLY_TEMPS[@]}" -gt 0 ]; then
    for temp in "${APPLY_TEMPS[@]}"; do
      while IFS= read -r id; do [ "$id" -gt "$max" ] && max="$id"; done < <(grep -E "^Task ID: TASK-${date_part}-[0-9]{3}$" "$temp" 2>/dev/null | sed "s/^Task ID: TASK-${date_part}-//")
    done
  fi
  if [ "${#RESERVED_TASK_IDS[@]}" -gt 0 ]; then
    for id in "${RESERVED_TASK_IDS[@]}"; do
      id="${id##*-}"; [ "$id" -gt "$max" ] && max="$id"
    done
  fi
  printf -v id 'TASK-%s-%03d' "$date_part" "$((10#$max + 1))"
  RESERVED_TASK_IDS+=("$id")
  printf '%s' "$id"
}

preserve_replaced_current_record() {
  local current_temp="$1" paused_temp="$2" old_status="$3" old_id old_title preserved_status
  old_id="$(sed -n '/^## /q; /^Task ID: /s/^Task ID: //p' "$current_temp" | head -n 1)"
  old_title="$(awk '/^## Goal[[:space:]]*$/ {goal=1; next} goal && /^## / {exit} goal && NF {print; exit}' "$current_temp")"
  case "$old_status" in
    active|ready|in_progress|waiting|blocked|review|paused) preserved_status=paused;;
    done|completed) preserved_status="$old_status";;
    # An empty slot holds no task, so the shipped template needs no preserved
    # record even though it carries a placeholder ID and goal text.
    empty) return 0;;
    '') [ -n "$old_id$old_title" ] || return 0; preserved_status=paused;;
    *) die "unsupported current task status for promotion: $old_status";;
  esac
  [[ "$old_id" =~ ^TASK-[0-9]{8}-[0-9]{3}$ ]] && [ -n "$old_title" ] || die "invalid current task to preserve: $current_temp"
  printf '\n### %s — %s\n\nTask ID: %s\n\nStatus: %s\n' "$(date -u +%F)" "$old_title" "$old_id" "$preserved_status" >> "$paused_temp"
  # The replaced task's recorded working state would otherwise be lost. Keep the
  # body verbatim, but indent every line into a Markdown code block: a preserved
  # Status, Task ID, or heading line must never be read back as a record field.
  {
    printf '\nReplaced task record:\n\n'
    sed 's/^/    /' "$current_temp"
  } >> "$paused_temp"
}

promote_to_active() {
  local source="$1" task_id="$2" index project_id project_index current paused current_temp paused_temp old_id old_title old_status title due record new_task_id
  index="$(known_index "$task_id")" || die "proposal has unknown task ID: $task_id"
  project_id="${KNOWN_PROJECT_IDS[$index]}"; project_index=''
  for i in "${!PROJECT_IDS[@]}"; do [ "${PROJECT_IDS[$i]}" = "$project_id" ] && project_index="$i"; done
  [ -n "$project_index" ] || die "unknown project for task: $task_id"
  current="${PROJECT_PATHS[$project_index]}/ai/current-task.md"; paused="${PROJECT_PATHS[$project_index]}/ai/paused-tasks.md"
  stage_source "$current"; stage_source "$paused"
  current_temp="$(temp_for_source "$current")"; paused_temp="$(temp_for_source "$paused")"
  old_status="$(awk '/^## / {exit} /^Status: / {print substr($0, 9); exit}' "$current_temp")"
  preserve_replaced_current_record "$current_temp" "$paused_temp" "$old_status"
  record="$(source_record "$(temp_for_source "$source")" "$task_id" "$source")" || die "invalid promoted source record: $source"
  IFS=$'\t' read -r _ title due <<< "$record"
  new_task_id="$(next_task_id)"
  mark_record_promoted "$source" "$task_id"
  printf 'Status: active\nTask ID: %s\n\n## Goal\n\n%s\n' "$new_task_id" "$title" > "$current_temp"
  [ -z "$due" ] || printf '\ndue: %s\n' "$due" >> "$current_temp"
  PROMOTED_TASK_IDS+=("$task_id"); PROMOTED_CURRENT_SOURCES+=("$current")
}

set_status_record() {
  local source="$1" task_id="$2" status="$3" temp base
  status_to_column "$status" >/dev/null || die "unsupported status: $status"
  temp="$(temp_for_source "$source")"; base="$(basename "$source")"
  [ "$status" != active ] || { [ "$base" = current-task.md ] || { promote_to_active "$source" "$task_id"; return; }; }
  case "$base" in
    current-task.md) STATUS="$status" perl -0pi -e 's/^Status: [^\n]*/"Status: $ENV{STATUS}"/me' "$temp";;
    future-tasks.md)
      case "$status" in idea|ready|blocked) ;; *) die "unsupported status transition from future task: $status";; esac
      TASK_ID="$task_id" STATUS="$status" perl -0pi -e 's{(^### \Q$ENV{TASK_ID}\E [^\n]*\n.*?^Status: )[^\n]*}{$1 . $ENV{STATUS}}mse' "$temp";;
    paused-tasks.md) [ "$status" = paused ] || die "unsupported status transition from paused task: $status";;
  esac
}

create_future_record() {
  local project_id="$1" title="$2" status="$3" due="$4" i source temp date_part max next id staged
  case "$status" in idea|ready|blocked) ;; *) die "unsupported future status: $status";; esac
  source=''; for i in "${!PROJECT_IDS[@]}"; do [ "${PROJECT_IDS[$i]}" = "$project_id" ] && source="${PROJECT_PATHS[$i]}/ai/future-tasks.md"; done
  [ -n "$source" ] || die "unknown project ID in proposal: $project_id"
  temp="$(temp_for_source "$source")"
  date_part="$(date -u +%Y%m%d)"; max=0
  while IFS= read -r id; do [ "$id" -gt "$max" ] && max="$id"; done < <(grep -hEo "^### FT-${date_part}-[0-9]+" "$HUB"/projects/*/ai/future-tasks.md 2>/dev/null | sed "s/^### FT-${date_part}-//")
  # Earlier operations in this same proposal appended to staged copies, so the
  # unmodified sources alone would hand out one ID twice.
  if [ "${#APPLY_TEMPS[@]}" -gt 0 ]; then
    for staged in "${APPLY_TEMPS[@]}"; do
      [ -n "$staged" ] || continue
      while IFS= read -r id; do [ "$id" -gt "$max" ] && max="$id"; done < <(grep -hEo "^### FT-${date_part}-[0-9]+" "$staged" 2>/dev/null | sed "s/^### FT-${date_part}-//")
    done
  fi
  printf -v next '%03d' "$((10#$max + 1))"
  printf '\n### FT-%s-%s — %s\n\nStatus: %s\n' "$date_part" "$next" "$title" "$status" >> "$temp"
  [ -z "$due" ] || printf 'due: %s\n' "$due" >> "$temp"
}

apply_operations_to_temporary_files() {
  local operation type task_id source to project_id title due
  while IFS= read -r operation; do
    type="$(printf '%s' "$operation" | /usr/bin/jq -r '.operation')"
    case "$type" in
      rename) task_id="$(printf '%s' "$operation" | /usr/bin/jq -r '.task_id')"; to="$(printf '%s' "$operation" | /usr/bin/jq -r '.to')"; [ -n "$to" ] || die 'rename title is empty'; source="$(known_source_for "$task_id")"; rename_record "$source" "$task_id" "$to";;
      set_due) task_id="$(printf '%s' "$operation" | /usr/bin/jq -r '.task_id')"; due="$(printf '%s' "$operation" | /usr/bin/jq -r '.to')"; [ -z "$due" ] || [[ "$due" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die 'invalid due date'; if source="$(promoted_current_source_for "$task_id")"; then :; else source="$(known_source_for "$task_id")"; fi; set_due_record "$source" "$task_id" "$due";;
      set_status) task_id="$(printf '%s' "$operation" | /usr/bin/jq -r '.task_id')"; to="$(printf '%s' "$operation" | /usr/bin/jq -r '.to')"; source="$(known_source_for "$task_id")"; set_status_record "$source" "$task_id" "$to";;
      create_future) project_id="$(printf '%s' "$operation" | /usr/bin/jq -r '.project_id')"; title="$(printf '%s' "$operation" | /usr/bin/jq -r '.title')"; to="$(printf '%s' "$operation" | /usr/bin/jq -r '.status')"; due="$(printf '%s' "$operation" | /usr/bin/jq -r '.due')"; [ -n "$title" ] || die 'future task title is empty'; create_future_record "$project_id" "$title" "$to" "$due";;
      *) die "unsupported proposal operation: $type";;
    esac
  done < <(/usr/bin/jq -c '.operations[]' "$PROPOSAL")
}

validate_temporary_records() {
  local i target temp
  for i in "${!APPLY_TARGETS[@]}"; do
    target="${APPLY_TARGETS[$i]}"; temp="${APPLY_TEMPS[$i]}"
    case "$(basename "$target")" in
      current-task.md) grep -Eq '^Status: (active|ready|in_progress|waiting|blocked|review|paused|done|completed)$' "$temp" && grep -Eq '^Task ID: TASK-[0-9]{8}-[0-9]{3}$' "$temp" || die "invalid temporary current task: $target";;
      future-tasks.md) ! grep -Eq '^### FT-[^ ]+ — $' "$temp" || die "invalid temporary future task: $target";;
      paused-tasks.md) ! grep -Eq '^### [0-9]{4}-[0-9]{2}-[0-9]{2} — $' "$temp" || die "invalid temporary paused task: $target";;
    esac
  done
}

back_up_named_source_files() {
  local i backup
  for i in "${!APPLY_TARGETS[@]}"; do
    backup="$(mktemp "$(dirname "${APPLY_TARGETS[$i]}")/.$(basename "${APPLY_TARGETS[$i]}").backup.XXXXXX")"
    cp "${APPLY_TARGETS[$i]}" "$backup"
    APPLY_BACKUPS[$i]="$backup"
  done
}
restore_replaced_source_files() {
  local i
  [ "${#APPLY_BACKUPS[@]}" -gt 0 ] || return 0
  for i in "${!APPLY_BACKUPS[@]}"; do
    [ -n "${APPLY_BACKUPS[$i]}" ] || continue
    mv -f -- "${APPLY_BACKUPS[$i]}" "${APPLY_TARGETS[$i]}"
    APPLY_BACKUPS[$i]=''
  done
}
discard_source_backups() {
  local i
  [ "${#APPLY_BACKUPS[@]}" -gt 0 ] || return 0
  for i in "${!APPLY_BACKUPS[@]}"; do
    [ -n "${APPLY_BACKUPS[$i]}" ] || continue
    rm -f -- "${APPLY_BACKUPS[$i]}"
    APPLY_BACKUPS[$i]=''
  done
}
replace_named_source_files() {
  local i
  for i in "${!APPLY_TARGETS[@]}"; do mv -f -- "${APPLY_TEMPS[$i]}" "${APPLY_TARGETS[$i]}"; APPLY_TEMPS[$i]=''; done
}

apply() {
  trap cleanup_apply_state EXIT
  require_safe_paths; load_proposal; verify_board_hash; verify_manifest_hash; load_projects; load_scope_and_validate_vault; verify_manifest_sources_are_registered; verify_every_affected_source_hash; load_known_cards
  apply_operations_to_temporary_files; validate_temporary_records
  GENERATOR="$(cd "$(dirname "$0")" && pwd -P)/generate-obsidian-projects-kanban.sh"
  [ -f "$GENERATOR" ] && [ ! -L "$GENERATOR" ] || die 'missing or unsafe generator'
  back_up_named_source_files; replace_named_source_files
  if ! "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture --replace-confirmed-board --confirm-generated-write; then
    restore_replaced_source_files
    die 'generated view refresh failed; canonical records were rolled back and the proposal was kept'
  fi
  discard_source_backups
  rm -f -- "$PROPOSAL"; trap - EXIT
}

case "$COMMAND" in
  scan) scan;;
  apply) [ -n "$CONFIRM_PROPOSAL" ] || die 'apply requires --confirm-proposal'; apply;;
  status) [ -z "$HUB$SCOPE" ] || die 'status accepts only --vault'; status;;
  dismiss) [ -z "$HUB$SCOPE$CONFIRM_PROPOSAL" ] || die 'dismiss accepts only --vault'; dismiss;;
esac
