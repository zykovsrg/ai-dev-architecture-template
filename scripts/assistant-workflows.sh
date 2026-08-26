#!/usr/bin/env bash
# Proposal-only mechanical guardrail for hub workflows.
set -euo pipefail

readonly NO_CHANGES='Read-only workflow: no changes were made.'
# A recorder can still be transcribing after export.  Three status checks with a
# one-second delay bound this read-only command and prevent a tight polling loop.
readonly MAX_STATUS_POLLS=3

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_absolute_path() {
  [[ "$2" == /* ]] || fail "$1 must be an absolute path"
}

require_value() {
  [[ -n "$2" ]] || fail "$1 requires a value"
}

require_directory_not_symlink() {
  [[ -d "$2" && ! -L "$2" ]] || fail "$1 must be a directory, not a symlink"
}

require_regular_not_symlink() {
  [[ -f "$2" && ! -L "$2" ]] || fail "$1 must be a regular non-symlink file"
}

valid_date() {
  local year=${1:0:4} month=${1:5:2} day=${1:8:2} month_number day_number days_in_month leap_year=0
  month_number=$((10#$month))
  day_number=$((10#$day))
  ((month_number >= 1 && month_number <= 12 && day_number >= 1)) || return 1
  if (( (10#$year % 4 == 0 && 10#$year % 100 != 0) || 10#$year % 400 == 0 )); then
    leap_year=1
  fi
  case "$month_number" in
    1|3|5|7|8|10|12) days_in_month=31 ;;
    4|6|9|11) days_in_month=30 ;;
    2) days_in_month=$((28 + leap_year)) ;;
  esac
  ((day_number <= days_in_month))
}

workflow=''
hub=''
scope=''
date=''
recorder_minutes=''
capture_input=''
capture_source_count=0

while (($#)); do
  case "$1" in
    capture|day-plan|evening-review|weekly-review)
      [[ -z "$workflow" ]] || fail 'exactly one workflow is required'
      workflow="$1"
      ;;
    --hub|--scope|--date|--recorder-minutes|--capture-input)
      (($# >= 2)) || fail "$1 requires a value"
      case "$1" in
        --hub) hub="$2" ;;
        --scope) scope="$2" ;;
        --date) date="$2" ;;
        --recorder-minutes)
          capture_source_count=$((capture_source_count + 1))
          recorder_minutes="$2"
          ;;
        --capture-input)
          capture_source_count=$((capture_source_count + 1))
          capture_input="$2"
          ;;
      esac
      shift
      ;;
    --write|--apply|--calendar|--obsidian)
      fail "$1 is not permitted by this read-only workflow"
      ;;
    *) fail "unrecognized argument: $1" ;;
  esac
  shift
done

[[ -n "$workflow" ]] || fail 'exactly one workflow is required'
require_value '--hub' "$hub"
require_absolute_path '--hub' "$hub"
require_value '--scope' "$scope"
require_absolute_path '--scope' "$scope"
require_value '--date' "$date"
[[ "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || fail '--date must be YYYY-MM-DD'
valid_date "$date" || fail '--date must be a real YYYY-MM-DD date'
require_directory_not_symlink '--hub' "$hub"
require_directory_not_symlink 'hub projects directory' "$hub/projects"
require_regular_not_symlink '--scope' "$scope"
registry="$hub/ai/project-registry.md"
require_regular_not_symlink 'project registry' "$registry"

registered_project_path() {
  local project_id=$1
  awk -v id="$project_id" '
    $0 == "## " id { in_project=1; found=1; next }
    in_project && /^## / { exit }
    in_project && /^Path: / { sub(/^Path: /, ""); print; exit }
    END { if (!found) exit 1 }
  ' "$registry"
}

scope_ids=()
while IFS= read -r project_id || [[ -n "$project_id" ]]; do
  scope_ids+=("$project_id")
done < "$scope"
((${#scope_ids[@]} > 0)) || fail '--scope must name at least one project'
scope_summary=''
for project_id in "${scope_ids[@]}"; do
  [[ "$project_id" =~ ^[a-z0-9][a-z0-9-]*$ ]] || fail "invalid project id in --scope: $project_id"
  registered_path=$(registered_project_path "$project_id") || fail "project is not registered: $project_id"
  [[ "$registered_path" == "$hub/projects/$project_id" ]] ||
    fail "registered path for $project_id must equal $hub/projects/$project_id"
  require_directory_not_symlink "project entry for $project_id" "$hub/projects/$project_id"
  require_directory_not_symlink "project ai directory for $project_id" "$hub/projects/$project_id/ai"
  require_regular_not_symlink "project card for $project_id" "$hub/projects/$project_id/ai/project-card.md"
  [[ ",$scope_summary," != *",$project_id,"* ]] || fail "duplicate project id in --scope: $project_id"
  scope_summary+="${scope_summary:+,}$project_id"
done

print_summary() {
  printf '%s\n' "$NO_CHANGES"
  printf 'workflow: %s\n' "$workflow"
  printf 'date: %s\n' "$date"
  printf 'scope: %s\n' "$scope_summary"
}

read_scoped_metadata() {
  local project_id file
  for project_id in "${scope_ids[@]}"; do
    for file in project-card.md current-task.md future-tasks.md paused-tasks.md; do
      if [[ -e "$hub/projects/$project_id/ai/$file" || -L "$hub/projects/$project_id/ai/$file" ]]; then
        require_regular_not_symlink "$file for $project_id" "$hub/projects/$project_id/ai/$file"
        sed -n '1p' "$hub/projects/$project_id/ai/$file" >/dev/null
      fi
    done
  done
}

validate_job_json() {
  local json=$1 expected_job=${2:-}
  jq -er '
    type == "object" and
    (.job | type == "string" and length > 0) and
    (.state | IN("pending", "done", "failed"))
  ' >/dev/null <<<"$json" || fail 'recorder returned invalid JSON'
  if [[ -n "$expected_job" ]]; then
    [[ "$(jq -er '.job' <<<"$json")" == "$expected_job" ]] || fail 'recorder status job does not match export job'
  fi
}

validate_transcript() {
  local transcript=$1 exports_root parent resolved_parent resolved_exports resolved_file
  [[ "$transcript" == /* ]] || fail 'transcript_path must be absolute'
  [[ "$transcript" == *.txt ]] || fail 'transcript_path must end in .txt'
  [[ ! -L "$transcript" && -f "$transcript" ]] || fail 'transcript_path must be a regular non-symlink file'
  exports_root="$HOME/Library/Application Support/rolling-audio-recorder/exports"
  [[ -d "$exports_root" ]] || fail 'recorder exports directory is missing'
  resolved_exports=$(cd "$exports_root" && pwd -P) || fail 'cannot resolve recorder exports directory'
  parent=$(dirname "$transcript")
  resolved_parent=$(cd "$parent" && pwd -P) || fail 'cannot resolve transcript parent'
  resolved_file="$resolved_parent/$(basename "$transcript")"
  [[ "$resolved_file" == "$resolved_exports"/* ]] || fail 'transcript_path is outside recorder exports'
  [[ ! -L "$resolved_file" && -f "$resolved_file" ]] || fail 'transcript_path must remain a regular non-symlink file'
}

capture() {
  ((capture_source_count == 1)) || fail 'capture requires exactly one source: --recorder-minutes N'
  if [[ -n "$capture_input" ]]; then
    require_absolute_path '--capture-input' "$capture_input"
    require_regular_not_symlink '--capture-input' "$capture_input"
    print_summary
    printf 'source_kind: capture-input\n'
    printf 'Semantic analysis: performed by hub-workflows.\n'
    return
  fi
  [[ "$recorder_minutes" =~ ^[0-9]+$ ]] || fail '--recorder-minutes must be an integer from 1 through 120'
  ((recorder_minutes >= 1 && recorder_minutes <= 120)) || fail '--recorder-minutes must be from 1 through 120'

  local exported status job state transcript error_message poll_count=0
  exported=$(rar export --minutes "$recorder_minutes" --json) || fail 'rar export failed'
  validate_job_json "$exported"
  job=$(jq -er '.job' <<<"$exported")
  while :; do
    poll_count=$((poll_count + 1))
    status=$(rar status "$job" --json) || fail 'rar status failed'
    validate_job_json "$status" "$job"
    state=$(jq -er '.state' <<<"$status")
    [[ "$state" != pending ]] && break
    ((poll_count < MAX_STATUS_POLLS)) || fail "recorder job $job remained pending after $MAX_STATUS_POLLS status checks"
    sleep 1
  done

  case "$state" in
    failed)
      error_message=$(jq -er '.error | strings | select(length > 0)' <<<"$status") || fail 'failed recorder job omitted error'
      printf 'Recorder job %s failed: %s\n' "$job" "$error_message" >&2
      exit 1
      ;;
    done)
      transcript=$(jq -er '.transcript_path | strings | select(length > 0)' <<<"$status") || fail 'done recorder job omitted transcript_path'
      validate_transcript "$transcript"
      ;;
  esac
  print_summary
  printf 'source_kind: recorder\n'
  printf 'job: %s\n' "$job"
  printf 'state: %s\n' "$state"
  [[ "$state" == done ]] || fail "unexpected recorder state: $state"
  printf 'transcript_path: %s\n' "$transcript"
  printf 'Semantic analysis: performed by hub-workflows.\n'
}

case "$workflow" in
  capture) capture ;;
  day-plan|evening-review|weekly-review)
    ((capture_source_count == 0)) || fail 'plan and review accept no capture source'
    read_scoped_metadata
    print_summary
    ;;
esac
