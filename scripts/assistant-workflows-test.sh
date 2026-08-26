#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$ROOT/scripts/assistant-workflows.sh"

if [[ ! -x "$SCRIPT" ]]; then
  printf 'FAIL: guardrail script is missing or not executable: %s\n' "$SCRIPT" >&2
  exit 1
fi

fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT
mock_bin="$fixture/bin"
hub="$fixture/hub"
exports="$fixture/home/Library/Application Support/rolling-audio-recorder/exports"
scope_file="$fixture/scope.txt"
mkdir -p "$mock_bin" "$hub/projects/fixture-a/ai" "$hub/projects/fixture-b/ai" "$exports"
printf '%s\n' 'fixture-a' > "$hub/projects/fixture-a/ai/project-card.md"
printf '%s\n' 'fixture-b' > "$hub/projects/fixture-b/ai/project-card.md"
printf '%s\n' fixture-a fixture-b > "$scope_file"
printf '%s\n' 'transcript' > "$exports/done.txt"
printf '%s\n' 'Kind: task' > "$fixture/capture.txt"

cat > "$mock_bin/rar" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  export) printf '%s\n' "${RAR_EXPORT_JSON:?}" ;;
  status)
    if [[ -n "${RAR_STATUS_SEQUENCE_FILE:-}" ]]; then
      count_file="${RAR_STATUS_COUNTER:?}"
      count=0
      [[ -f "$count_file" ]] && count=$(<"$count_file")
      count=$((count + 1))
      printf '%s\n' "$count" > "$count_file"
      sed -n "${count}p" "$RAR_STATUS_SEQUENCE_FILE"
    else
      printf '%s\n' "${RAR_STATUS_JSON:?}"
    fi
    ;;
  *) exit 64 ;;
esac
MOCK
chmod +x "$mock_bin/rar"

cat > "$mock_bin/sleep" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
[[ "${1:-}" == 1 ]] || exit 64
printf '%s\n' "$1" >> "${RAR_SLEEP_LOG:?}"
MOCK
chmod +x "$mock_bin/sleep"

run() {
  HOME="$fixture/home" PATH="$mock_bin:$PATH" \
    RAR_EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"requested_minutes":10,"exported_seconds":0,"warnings":[]}' \
    RAR_STATUS_JSON="{\"job\":\"job-1\",\"state\":\"done\",\"audio_path\":null,\"transcript_path\":\"$exports/done.txt\",\"error\":null}" \
    "$SCRIPT" "$@"
}

run_with_status() {
  local status_json=$1
  shift
  HOME="$fixture/home" PATH="$mock_bin:$PATH" \
    RAR_EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"requested_minutes":10,"exported_seconds":0,"warnings":[]}' \
    RAR_STATUS_JSON="$status_json" \
    "$SCRIPT" "$@"
}

run_with_export() {
  local export_json=$1
  shift
  HOME="$fixture/home" PATH="$mock_bin:$PATH" \
    RAR_EXPORT_JSON="$export_json" \
    RAR_STATUS_JSON="{\"job\":\"job-1\",\"state\":\"done\",\"audio_path\":null,\"transcript_path\":\"$exports/done.txt\",\"error\":null}" \
    "$SCRIPT" "$@"
}

run_with_status_sequence() {
  local sequence_file=$1
  shift
  local counter_file="$fixture/status-count"
  local sleep_log="$fixture/sleep-log"
  rm -f "$counter_file" "$sleep_log"
  HOME="$fixture/home" PATH="$mock_bin:$PATH" \
    RAR_EXPORT_JSON='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"requested_minutes":10,"exported_seconds":0,"warnings":[]}' \
    RAR_STATUS_SEQUENCE_FILE="$sequence_file" RAR_STATUS_COUNTER="$counter_file" RAR_SLEEP_LOG="$sleep_log" \
    "$SCRIPT" "$@"
}

before=$(shasum "$hub/projects/fixture-a/ai/project-card.md" "$hub/projects/fixture-b/ai/project-card.md")
output=$(run capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10)
after=$(shasum "$hub/projects/fixture-a/ai/project-card.md" "$hub/projects/fixture-b/ai/project-card.md")
[[ "$before" == "$after" ]] || { printf 'FAIL: fixture was modified\n' >&2; exit 1; }
grep -Fx 'Read-only workflow: no changes were made.' <<<"$output"
grep -Fx 'source_kind: recorder' <<<"$output"
grep -Fx 'state: done' <<<"$output"
grep -Fx 'scope: fixture-a,fixture-b' <<<"$output"

expect_fail() {
  if run "$@" >/dev/null 2>&1; then
    printf 'FAIL: expected command failure: %s\n' "$*" >&2
    exit 1
  fi
}

expect_read_only_header() {
  local output=$1
  [[ "${output%%$'\n'*}" == 'Read-only workflow: no changes were made.' ]] || {
    printf 'FAIL: successful output must begin with read-only notice\n' >&2
    exit 1
  }
}

expect_read_only_header "$output"

expect_fail capture --hub relative --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10
expect_fail capture --hub "$hub" --scope fixture-a --date 2026-08-26 --recorder-minutes 10
expect_fail capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 0
expect_fail capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 121
expect_fail capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 --write
expect_fail capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 --apply
expect_fail capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 --calendar
expect_fail capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 --obsidian
expect_fail capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 --recorder-minutes 10
expect_fail capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 --capture-input "$fixture/capture.txt"
expect_fail capture --hub "$hub" --scope "$scope_file" --date 2026-02-29 --recorder-minutes 10

capture_input_output=$(run capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --capture-input "$fixture/capture.txt")
expect_read_only_header "$capture_input_output"
for workflow in day-plan evening-review weekly-review; do
  workflow_output=$(run "$workflow" --hub "$hub" --scope "$scope_file" --date 2026-08-26)
  expect_read_only_header "$workflow_output"
done

if run_with_export '{not-json' capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 >/dev/null 2>&1; then
  printf 'FAIL: expected malformed export JSON to fail\n' >&2
  exit 1
fi

if run_with_status '{not-json' capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 >/dev/null 2>&1; then
  printf 'FAIL: expected malformed recorder JSON to fail\n' >&2
  exit 1
fi

printf '%s\n' 'external' > "$fixture/external.txt"
external_json="{\"job\":\"job-1\",\"state\":\"done\",\"audio_path\":null,\"transcript_path\":\"$fixture/external.txt\",\"error\":null}"
if run_with_status "$external_json" capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 >/dev/null 2>&1; then
  printf 'FAIL: expected external transcript to fail\n' >&2
  exit 1
fi

ln -s "$fixture/external.txt" "$exports/linked.txt"
symlink_json="{\"job\":\"job-1\",\"state\":\"done\",\"audio_path\":null,\"transcript_path\":\"$exports/linked.txt\",\"error\":null}"
if run_with_status "$symlink_json" capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 >/dev/null 2>&1; then
  printf 'FAIL: expected symlink transcript to fail\n' >&2
  exit 1
fi

pending_json='{"job":"job-1","state":"pending","audio_path":null,"transcript_path":null,"error":null}'
printf '%s\n%s\n' \
  "$pending_json" \
  "{\"job\":\"job-1\",\"state\":\"done\",\"audio_path\":null,\"transcript_path\":\"$exports/done.txt\",\"error\":null}" > "$fixture/pending-done.jsonl"
poll_done_output=$(run_with_status_sequence "$fixture/pending-done.jsonl" capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10)
grep -Fx 'state: done' <<<"$poll_done_output"
[[ $(<"$fixture/status-count") == 2 ]] || { printf 'FAIL: expected two status polls before done\n' >&2; exit 1; }
[[ $(wc -l < "$fixture/sleep-log" | tr -d ' ') == 1 ]] || { printf 'FAIL: expected one bounded polling delay\n' >&2; exit 1; }

printf '%s\n%s\n' \
  "$pending_json" \
  '{"job":"job-1","state":"failed","audio_path":null,"transcript_path":null,"error":"recorder failed"}' > "$fixture/pending-failed.jsonl"
if run_with_status_sequence "$fixture/pending-failed.jsonl" capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 >/dev/null 2>&1; then
  printf 'FAIL: expected pending then failed recorder job to fail\n' >&2
  exit 1
fi
[[ $(<"$fixture/status-count") == 2 ]] || { printf 'FAIL: expected two status polls before failed\n' >&2; exit 1; }
[[ $(wc -l < "$fixture/sleep-log" | tr -d ' ') == 1 ]] || { printf 'FAIL: expected one bounded polling delay before failed\n' >&2; exit 1; }

printf '%s\n%s\n%s\n' "$pending_json" "$pending_json" "$pending_json" > "$fixture/pending-timeout.jsonl"
if run_with_status_sequence "$fixture/pending-timeout.jsonl" capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 >/dev/null 2>&1; then
  printf 'FAIL: expected permanently pending recorder job to time out\n' >&2
  exit 1
fi
[[ $(<"$fixture/status-count") == 3 ]] || { printf 'FAIL: expected bounded status polling\n' >&2; exit 1; }

ln -s "$hub" "$fixture/linked-hub"
expect_fail day-plan --hub "$fixture/linked-hub" --scope "$scope_file" --date 2026-08-26
rm "$fixture/linked-hub"

ln -s "$hub/projects/fixture-a" "$hub/projects/linked-project"
printf '%s\n' linked-project > "$fixture/symlink-project-scope.txt"
expect_fail day-plan --hub "$hub" --scope "$fixture/symlink-project-scope.txt" --date 2026-08-26
rm "$hub/projects/linked-project"

mv "$hub/projects/fixture-a/ai/project-card.md" "$fixture/project-card.md"
ln -s "$fixture/project-card.md" "$hub/projects/fixture-a/ai/project-card.md"
expect_fail day-plan --hub "$hub" --scope "$scope_file" --date 2026-08-26
rm "$hub/projects/fixture-a/ai/project-card.md"
mv "$fixture/project-card.md" "$hub/projects/fixture-a/ai/project-card.md"

printf '%s\n' 'Task: fixture' > "$fixture/current-task.md"
ln -s "$fixture/current-task.md" "$hub/projects/fixture-a/ai/current-task.md"
expect_fail day-plan --hub "$hub" --scope "$scope_file" --date 2026-08-26
rm "$hub/projects/fixture-a/ai/current-task.md"

failed_json='{"job":"job-1","state":"failed","audio_path":null,"transcript_path":null,"error":"recorder failed"}'
if run_with_status "$failed_json" capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 >/dev/null 2>&1; then
  printf 'FAIL: expected failed recorder job to fail\n' >&2
  exit 1
fi

printf 'PASS: assistant workflow guardrail contract\n'
