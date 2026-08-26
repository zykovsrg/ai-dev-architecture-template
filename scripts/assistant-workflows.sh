#!/usr/bin/env bash
# Proposal-only mechanical guardrail for hub workflows.
set -euo pipefail

readonly NO_CHANGES='Read-only workflow: no changes were made.'

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
[[ -d "$hub/projects" ]] || fail 'hub projects directory is missing'
[[ -f "$scope" && ! -L "$scope" ]] || fail '--scope must be a regular non-symlink file'

scope_ids=()
while IFS= read -r project_id || [[ -n "$project_id" ]]; do
  scope_ids+=("$project_id")
done < "$scope"
((${#scope_ids[@]} > 0)) || fail '--scope must name at least one project'
scope_summary=''
for project_id in "${scope_ids[@]}"; do
  [[ "$project_id" =~ ^[a-z0-9][a-z0-9-]*$ ]] || fail "invalid project id in --scope: $project_id"
  [[ -f "$hub/projects/$project_id/ai/project-card.md" ]] || fail "unregistered project in --scope: $project_id"
  [[ ",$scope_summary," != *",$project_id,"* ]] || fail "duplicate project id in --scope: $project_id"
  scope_summary+="${scope_summary:+,}$project_id"
done

print_summary() {
  printf 'workflow: %s\n' "$workflow"
  printf 'date: %s\n' "$date"
  printf 'scope: %s\n' "$scope_summary"
}

read_scoped_metadata() {
  local project_id file
  for project_id in "${scope_ids[@]}"; do
    for file in project-card.md current-task.md future-tasks.md paused-tasks.md; do
      [[ -f "$hub/projects/$project_id/ai/$file" ]] && sed -n '1p' "$hub/projects/$project_id/ai/$file" >/dev/null
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
    [[ -f "$capture_input" && ! -L "$capture_input" ]] || fail '--capture-input must be a regular non-symlink file'
    print_summary
    printf 'source_kind: capture-input\n'
    printf 'Semantic analysis: performed by hub-workflows.\n'
    printf '%s\n' "$NO_CHANGES"
    return
  fi
  [[ "$recorder_minutes" =~ ^[0-9]+$ ]] || fail '--recorder-minutes must be an integer from 1 through 120'
  ((recorder_minutes >= 1 && recorder_minutes <= 120)) || fail '--recorder-minutes must be from 1 through 120'

  local exported status job state transcript error_message
  exported=$(rar export --minutes "$recorder_minutes" --json) || fail 'rar export failed'
  validate_job_json "$exported"
  job=$(jq -er '.job' <<<"$exported")
  status=$(rar status "$job" --json) || fail 'rar status failed'
  validate_job_json "$status" "$job"
  state=$(jq -er '.state' <<<"$status")

  print_summary
  printf 'source_kind: recorder\n'
  printf 'job: %s\n' "$job"
  printf 'state: %s\n' "$state"
  case "$state" in
    pending)
      printf 'Pending recorder job: %s\n' "$job"
      ;;
    failed)
      error_message=$(jq -er '.error | strings | select(length > 0)' <<<"$status") || fail 'failed recorder job omitted error'
      printf 'Recorder job %s failed: %s\n' "$job" "$error_message" >&2
      exit 1
      ;;
    done)
      transcript=$(jq -er '.transcript_path | strings | select(length > 0)' <<<"$status") || fail 'done recorder job omitted transcript_path'
      validate_transcript "$transcript"
      printf 'transcript_path: %s\n' "$transcript"
      printf 'Semantic analysis: performed by hub-workflows.\n'
      ;;
  esac
  printf '%s\n' "$NO_CHANGES"
}

case "$workflow" in
  capture) capture ;;
  day-plan|evening-review|weekly-review)
    ((capture_source_count == 0)) || fail 'plan and review accept no capture source'
    read_scoped_metadata
    print_summary
    printf '%s\n' "$NO_CHANGES"
    ;;
esac
