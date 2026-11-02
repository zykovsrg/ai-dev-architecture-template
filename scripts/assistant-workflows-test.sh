#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$ROOT/scripts/assistant-workflows.sh"
source "$ROOT/tests/helpers/shell-scenarios.sh"
fixture="$(mktemp -d "${TMPDIR:-/private/tmp}/assistant-scenarios.XXXXXX")"
trap 'rm -rf "$fixture"' EXIT

setup_case() {
  WORK_CASE="$fixture/$SCENARIO_CURRENT"
  mkdir -p "$WORK_CASE"
  WORK_CASE="$(cd "$WORK_CASE" && pwd -P)"
  mock_bin="$WORK_CASE/bin"; hub="$WORK_CASE/hub"
  exports="$WORK_CASE/home/Library/Application Support/rolling-audio-recorder/exports"
  scope_file="$WORK_CASE/scope.txt"
  mkdir -p "$mock_bin" "$hub/ai" "$hub/projects/fixture-a/ai" "$hub/projects/fixture-b/ai" "$hub/projects/unregistered/ai" "$exports"
  cat >"$hub/ai/project-registry.md" <<REGISTRY
# Реестр искусственных проектов

## fixture-a
Path: $hub/projects/fixture-a

## fixture-b
Path: $hub/projects/fixture-b
REGISTRY
  printf '%s\n' fixture-a >"$hub/projects/fixture-a/ai/project-card.md"
  printf '%s\n' fixture-b >"$hub/projects/fixture-b/ai/project-card.md"
  printf '%s\n' fixture-a fixture-b >"$scope_file"
  printf '%s\n' transcript >"$exports/done.txt"
  printf '%s\n' 'Kind: task' >"$WORK_CASE/capture.txt"
  cat >"$mock_bin/rar" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
 export) printf '%s\n' "$RAR_EXPORT_JSON" ;;
 status)
  if [ -n "${RAR_STATUS_SEQUENCE_FILE:-}" ]; then
   count=0
   [ ! -f "$RAR_STATUS_COUNTER" ] || count="$(< "$RAR_STATUS_COUNTER")"
   count=$((count+1)); printf '%s\n' "$count" >"$RAR_STATUS_COUNTER"
   sed -n "${count}p" "$RAR_STATUS_SEQUENCE_FILE"
  else printf '%s\n' "$RAR_STATUS_JSON"; fi ;;
 *) exit 64 ;;
esac
MOCK
  cat >"$mock_bin/sleep" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
[ "${1:-}" = 1 ] || exit 64
printf '%s\n' "$1" >>"$RAR_SLEEP_LOG"
MOCK
  chmod +x "$mock_bin/rar" "$mock_bin/sleep"
  EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"requested_minutes":10,"exported_seconds":0,"warnings":[]}'
  STATUS_JSON="{\"job\":\"job-1\",\"state\":\"done\",\"audio_path\":null,\"transcript_path\":\"$exports/done.txt\",\"error\":null}"
  SEQUENCE_FILE=''; EXPECT=0; DIAGNOSTIC=''
  args=(capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10)
}

run_subject() {
  local rc
  scenario_accept_exit "$EXPECT" "$DIAGNOSTIC"
  scenario_exec rc bash -c 'set -e; cd "$1"; shift; exec "$@"' _ "$WORK_CASE" env HOME="$WORK_CASE/home" PATH="$mock_bin:/usr/bin:/bin:/usr/sbin:/sbin" RAR_EXPORT_JSON="$EXPORT_JSON" RAR_STATUS_JSON="$STATUS_JSON" RAR_STATUS_SEQUENCE_FILE="$SEQUENCE_FILE" RAR_STATUS_COUNTER="$WORK_CASE/status-count" RAR_SLEEP_LOG="$WORK_CASE/sleep-log" "$SCRIPT" "${args[@]}" >"$WORK_CASE/output"
  scenario_assert_exit "$EXPECT" "$rc"
}
check_equal() {
  local rc
  scenario_accept_exit 1 ''
  scenario_exec rc /bin/test "$1" = "$2"
  scenario_assert_exit 0 "$rc"
}
check_line() {
  local rc
  scenario_accept_exit 1 ''
  scenario_exec rc grep -Fxq "$1" "$WORK_CASE/output"
  scenario_assert_exit 0 "$rc"
}
check_absent() {
  local rc
  scenario_accept_exit 1 ''
  scenario_exec rc grep -Fq "$1" "$WORK_CASE/output"
  scenario_assert_exit 1 "$rc"
}
# Внешнее чтение выполняется в родительском протоколе. Ненулевой код либо
# неожиданный stderr запрещает credit, прежде чем значение попадёт в сравнение.
read_oracle() {
  local destination="$1" rc
  shift
  scenario_accept_exit 0 ''
  scenario_exec rc "$@" >"$destination"
  scenario_assert_exit 0 "$rc"
}
check_header() {
  read_oracle "$WORK_CASE/header" head -n 1 "$WORK_CASE/output"
  check_equal "$(< "$WORK_CASE/header")" 'Read-only workflow: no changes were made.'
}
read_card_hashes() {
  read_oracle "$1" shasum "$hub/projects/fixture-a/ai/project-card.md" "$hub/projects/fixture-b/ai/project-card.md"
}
check_polls() {
  local rc
  scenario_accept_exit 1 ''
  scenario_exec rc /bin/test -f "$WORK_CASE/status-count"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc /bin/test -f "$WORK_CASE/sleep-log"
  scenario_assert_exit 0 "$rc"
  read_oracle "$WORK_CASE/read-status-count" cat "$WORK_CASE/status-count"
  read_oracle "$WORK_CASE/read-sleep-count" wc -l <"$WORK_CASE/sleep-log"
  read_oracle "$WORK_CASE/normalized-sleep-count" tr -d ' ' <"$WORK_CASE/read-sleep-count"
  check_equal "$(< "$WORK_CASE/read-status-count")" "$1"
  check_equal "$(< "$WORK_CASE/normalized-sleep-count")" "$2"
}

case_0() {
  scenario_begin
  setup_case
  read_card_hashes "$WORK_CASE/card-hashes-before"
  run_subject
  check_header
  check_line 'source_kind: recorder'
  check_line 'state: done'
  check_line 'scope: fixture-a,fixture-b'
  read_card_hashes "$WORK_CASE/card-hashes-after"
  check_equal "$(< "$WORK_CASE/card-hashes-after")" "$(< "$WORK_CASE/card-hashes-before")"
  scenario_pass
}

case_1() {
  scenario_begin
  setup_case
  sed 's@Path: .*/hub/projects/@Path: hub/projects/@' "$hub/ai/project-registry.md" >"$WORK_CASE/registry"
  mv "$WORK_CASE/registry" "$hub/ai/project-registry.md"
  args=(capture --hub hub --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10)
  EXPECT=1
  DIAGNOSTIC='ERROR: --hub must be an absolute path
'
  run_subject

  scenario_pass
}

case_2() {
  scenario_begin
  setup_case
  cp "$scope_file" "$WORK_CASE/fixture-a"
  args=(capture --hub "$hub" --scope fixture-a --date 2026-08-26 --recorder-minutes 10)
  EXPECT=1
  DIAGNOSTIC='ERROR: --scope must be an absolute path
'
  run_subject

  scenario_pass
}

case_3() {
  scenario_begin
  setup_case
  EXPORT_JSON="${EXPORT_JSON/\"requested_minutes\":10/\"requested_minutes\":0}"
  args=(capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 0)
  EXPECT=1
  DIAGNOSTIC='ERROR: --recorder-minutes must be from 1 through 120
'
  run_subject

  scenario_pass
}

case_4() {
  scenario_begin
  setup_case
  EXPORT_JSON="${EXPORT_JSON/\"requested_minutes\":10/\"requested_minutes\":121}"
  args=(capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 121)
  EXPECT=1
  DIAGNOSTIC='ERROR: --recorder-minutes must be from 1 through 120
'
  run_subject

  scenario_pass
}

case_5() {
  scenario_begin
  setup_case
  args+=(--write)
  EXPECT=1
  DIAGNOSTIC='ERROR: --write is not permitted by this read-only workflow
'
  run_subject

  scenario_pass
}

case_6() {
  scenario_begin
  setup_case
  args+=(--apply)
  EXPECT=1
  DIAGNOSTIC='ERROR: --apply is not permitted by this read-only workflow
'
  run_subject

  scenario_pass
}

case_7() {
  scenario_begin
  setup_case
  args+=(--calendar)
  EXPECT=1
  DIAGNOSTIC='ERROR: --calendar is not permitted by this read-only workflow
'
  run_subject

  scenario_pass
}

case_8() {
  scenario_begin
  setup_case
  args+=(--obsidian)
  EXPECT=1
  DIAGNOSTIC='ERROR: --obsidian is not permitted by this read-only workflow
'
  run_subject

  scenario_pass
}

case_9() {
  scenario_begin
  setup_case
  args+=(--recorder-minutes 10)
  EXPECT=1
  DIAGNOSTIC='ERROR: capture requires exactly one source: --recorder-minutes N
'
  run_subject

  scenario_pass
}

case_10() {
  scenario_begin
  setup_case
  args+=(--capture-input "$WORK_CASE/capture.txt")
  EXPECT=1
  DIAGNOSTIC='ERROR: capture requires exactly one source: --recorder-minutes N
'
  run_subject

  scenario_pass
}

case_11() {
  scenario_begin
  setup_case
  args=(capture --hub "$hub" --scope "$scope_file" --date 2026-02-29 --recorder-minutes 10)
  EXPECT=1
  DIAGNOSTIC='ERROR: --date must be a real YYYY-MM-DD date
'
  run_subject

  scenario_pass
}

case_12() {
  scenario_begin
  setup_case
  printf '%s\n' unregistered >"$scope_file"
  args=(day-plan --hub "$hub" --scope "$scope_file" --date 2026-08-26)
  EXPECT=1
  DIAGNOSTIC='ERROR: project is not registered: unregistered
'
  run_subject

  scenario_pass
}

case_13() {
  scenario_begin
  setup_case
  args=(capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --capture-input "$WORK_CASE/capture.txt")
  run_subject
  check_header
  scenario_pass
}

case_14() {
  scenario_begin
  setup_case
  args=(day-plan --hub "$hub" --scope "$scope_file" --date 2026-08-26)
  run_subject
  check_header
  scenario_pass
}

case_15() {
  scenario_begin
  setup_case
  args=(evening-review --hub "$hub" --scope "$scope_file" --date 2026-08-26)
  run_subject
  check_header
  scenario_pass
}

case_16() {
  scenario_begin
  setup_case
  args=(weekly-review --hub "$hub" --scope "$scope_file" --date 2026-08-26)
  run_subject
  check_header
  scenario_pass
}

case_17() {
  scenario_begin
  setup_case
  rm "$hub/projects/fixture-a/ai/project-card.md" "$hub/projects/fixture-b/ai/project-card.md"
  args=(day-plan --hub "$hub" --scope "$scope_file" --date 2026-08-26)
  run_subject
  check_header
  scenario_pass
}

case_18() {
  scenario_begin
  setup_case
  EXPORT_JSON='{not-json'
  EXPECT=1
  DIAGNOSTIC='jq: parse error: Invalid numeric literal at line 2, column 0
ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_19() {
  scenario_begin
  setup_case
  STATUS_JSON='{not-json'
  EXPECT=1
  DIAGNOSTIC='jq: parse error: Invalid numeric literal at line 2, column 0
ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_20() {
  scenario_begin
  setup_case
  EXPORT_JSON='{"job":"job-1","state":"pending","transcript_path":null,"requested_minutes":10,"exported_seconds":0,"warnings":[]}'
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_21() {
  scenario_begin
  setup_case
  EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"requested_minutes":10,"exported_seconds":0,"warnings":[],"extra":true}'
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_22() {
  scenario_begin
  setup_case
  EXPORT_JSON='{"job":"job-1","state":"failed","audio_path":null,"transcript_path":null,"requested_minutes":10,"exported_seconds":0,"warnings":[]}'
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_23() {
  scenario_begin
  setup_case
  EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":{},"transcript_path":null,"requested_minutes":10,"exported_seconds":0,"warnings":[]}'
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_24() {
  scenario_begin
  setup_case
  EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":false,"requested_minutes":10,"exported_seconds":0,"warnings":[]}'
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_25() {
  scenario_begin
  setup_case
  EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"requested_minutes":"10","exported_seconds":0,"warnings":[]}'
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_26() {
  scenario_begin
  setup_case
  EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"requested_minutes":9,"exported_seconds":0,"warnings":[]}'
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_27() {
  scenario_begin
  setup_case
  EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"requested_minutes":10,"exported_seconds":"0","warnings":[]}'
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_28() {
  scenario_begin
  setup_case
  EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"requested_minutes":10,"exported_seconds":0,"warnings":[1]}'
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_29() {
  scenario_begin
  setup_case
  STATUS_JSON="$(printf '%s' "$STATUS_JSON" | /usr/bin/jq -c 'del(.audio_path)')"
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_30() {
  scenario_begin
  setup_case
  STATUS_JSON="$(printf '%s' "$STATUS_JSON" | /usr/bin/jq -c 'del(.error)')"
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_31() {
  scenario_begin
  setup_case
  STATUS_JSON="$(printf '%s' "$STATUS_JSON" | /usr/bin/jq -c .extra=true)"
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_32() {
  scenario_begin
  setup_case
  STATUS_JSON="$(printf '%s' "$STATUS_JSON" | /usr/bin/jq -c .audio_path=1)"
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_33() {
  scenario_begin
  setup_case
  STATUS_JSON="$(printf '%s' "$STATUS_JSON" | /usr/bin/jq -c '.error=[]')"
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_34() {
  scenario_begin
  setup_case
  STATUS_JSON="$(printf '%s' "$STATUS_JSON" | /usr/bin/jq -c .transcript_path=false)"
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_35() {
  scenario_begin
  setup_case
  printf '%s\n' external >"$WORK_CASE/external.txt"
  STATUS_JSON="$(printf '%s' "$STATUS_JSON" | /usr/bin/jq -c --arg p "$WORK_CASE/external.txt" '.transcript_path=$p')"
  EXPECT=1
  DIAGNOSTIC='ERROR: transcript_path is outside recorder exports
'
  run_subject

  scenario_pass
}

case_36() {
  scenario_begin
  setup_case
  ln -s "$exports/done.txt" "$exports/linked.txt"
  STATUS_JSON="$(printf '%s' "$STATUS_JSON" | /usr/bin/jq -c --arg p "$exports/linked.txt" '.transcript_path=$p')"
  EXPECT=1
  DIAGNOSTIC='ERROR: transcript_path must be a regular non-symlink file
'
  run_subject

  scenario_pass
}

case_37() {
  scenario_begin
  setup_case
  SEQUENCE_FILE="$WORK_CASE/sequence"
  printf '%s\n' '{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"error":null}' "$STATUS_JSON" >"$SEQUENCE_FILE"
  run_subject
  check_line 'state: done'
  check_polls 2 1
  scenario_pass
}

case_38() {
  scenario_begin
  setup_case
  SEQUENCE_FILE="$WORK_CASE/sequence"
  printf '%s\n' '{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"error":null}' '{"job":"job-1","state":"failed","audio_path":null,"transcript_path":null,"error":"recorder failed"}' >"$SEQUENCE_FILE"
  EXPECT=1
  DIAGNOSTIC='Recorder job job-1 failed: recorder failed
'
  run_subject
  check_polls 2 1
  scenario_pass
}

case_39() {
  scenario_begin
  setup_case
  SEQUENCE_FILE="$WORK_CASE/sequence"
  printf '%s\n' '{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"error":null}' '{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"error":null}' '{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"error":null}' >"$SEQUENCE_FILE"
  run_subject
  check_header
  check_line 'source_kind: recorder'
  check_line 'job: job-1'
  check_line 'state: pending'
  check_absent 'transcript_path:'
  check_absent 'Semantic analysis:'
  check_polls 3 2
  scenario_pass
}

case_40() {
  scenario_begin
  setup_case
  STATUS_JSON="$(printf '%s' "$STATUS_JSON" | /usr/bin/jq -c '.state="pending"|.transcript_path="unexpected.txt"')"
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_41() {
  scenario_begin
  setup_case
  STATUS_JSON="$(printf '%s' "$STATUS_JSON" | /usr/bin/jq -c '.state="pending"|.transcript_path=null|.error="unexpected"')"
  EXPECT=1
  DIAGNOSTIC='ERROR: recorder returned invalid JSON
'
  run_subject

  scenario_pass
}

case_42() {
  scenario_begin
  setup_case
  ln -s "$hub" "$WORK_CASE/linked-hub"
  sed "s@$hub/projects/@$WORK_CASE/linked-hub/projects/@" "$hub/ai/project-registry.md" >"$WORK_CASE/registry"
  mv "$WORK_CASE/registry" "$hub/ai/project-registry.md"
  args=(day-plan --hub "$WORK_CASE/linked-hub" --scope "$scope_file" --date 2026-08-26)
  EXPECT=1
  DIAGNOSTIC='ERROR: --hub must be a directory, not a symlink
'
  run_subject

  scenario_pass
}

case_43() {
  scenario_begin
  setup_case
  ln -s "$hub/projects/fixture-a" "$hub/projects/linked-project"
  printf '\n## linked-project\nPath: %s/projects/linked-project\n' "$hub" >>"$hub/ai/project-registry.md"
  printf '%s\n' linked-project >"$scope_file"
  args=(day-plan --hub "$hub" --scope "$scope_file" --date 2026-08-26)
  EXPECT=1
  DIAGNOSTIC='ERROR: project entry for linked-project must be a directory, not a symlink
'
  run_subject

  scenario_pass
}

case_44() {
  scenario_begin
  setup_case
  printf '%s\n' 'Task: fixture' >"$WORK_CASE/current-task.md"
  ln -s "$WORK_CASE/current-task.md" "$hub/projects/fixture-a/ai/current-task.md"
  args=(day-plan --hub "$hub" --scope "$scope_file" --date 2026-08-26)
  EXPECT=1
  DIAGNOSTIC='ERROR: current-task.md for fixture-a must be a regular non-symlink file
'
  run_subject

  scenario_pass
}

case_45() {
  scenario_begin
  setup_case
  STATUS_JSON='{"job":"job-1","state":"failed","audio_path":null,"transcript_path":null,"error":"recorder failed"}'
  EXPECT=1
  DIAGNOSTIC='Recorder job job-1 failed: recorder failed
'
  run_subject

  scenario_pass
}
scenario_declare recorder-capture-read-only case_0
scenario_declare rejects-relative-hub case_1
scenario_declare rejects-inline-scope case_2
scenario_declare rejects-zero-recorder-minutes case_3
scenario_declare rejects-overlong-recorder-minutes case_4
scenario_declare rejects-write-flag case_5
scenario_declare rejects-apply-flag case_6
scenario_declare rejects-calendar-flag case_7
scenario_declare rejects-obsidian-flag case_8
scenario_declare rejects-duplicate-recorder-option case_9
scenario_declare rejects-mixed-capture-sources case_10
scenario_declare rejects-impossible-date case_11
scenario_declare rejects-unregistered-scope-project case_12
scenario_declare capture-input-read-only-header case_13
scenario_declare day-plan-read-only-header case_14
scenario_declare evening-review-read-only-header case_15
scenario_declare weekly-review-read-only-header case_16
scenario_declare planning-without-legacy-project-cards case_17
scenario_declare rejects-malformed-export-json case_18
scenario_declare rejects-malformed-status-json case_19
scenario_declare rejects-export-missing-audio-path case_20
scenario_declare rejects-export-extra-key case_21
scenario_declare rejects-export-unsupported-state case_22
scenario_declare rejects-export-audio-path-type case_23
scenario_declare rejects-export-transcript-path-type case_24
scenario_declare rejects-export-requested-minutes-type case_25
scenario_declare rejects-export-requested-minutes-mismatch case_26
scenario_declare rejects-export-exported-seconds-type case_27
scenario_declare rejects-export-warning-item-type case_28
scenario_declare rejects-status-missing-audio-path case_29
scenario_declare rejects-status-missing-error case_30
scenario_declare rejects-status-extra-key case_31
scenario_declare rejects-status-audio-path-type case_32
scenario_declare rejects-status-error-type case_33
scenario_declare rejects-status-transcript-path-type case_34
scenario_declare rejects-external-transcript case_35
scenario_declare rejects-symlink-transcript case_36
scenario_declare polls-pending-until-done case_37
scenario_declare polls-pending-until-failed case_38
scenario_declare bounded-pending-timeout case_39
scenario_declare rejects-pending-transcript case_40
scenario_declare rejects-pending-error case_41
scenario_declare rejects-symlink-hub case_42
scenario_declare rejects-symlink-project case_43
scenario_declare rejects-symlink-current-task case_44
scenario_declare rejects-failed-recorder-job case_45
scenario_main "$@"
