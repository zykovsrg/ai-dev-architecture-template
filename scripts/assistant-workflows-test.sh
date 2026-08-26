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
  status) printf '%s\n' "${RAR_STATUS_JSON:?}" ;;
  *) exit 64 ;;
esac
MOCK
chmod +x "$mock_bin/rar"

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
pending_output=$(run_with_status "$pending_json" capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10)
grep -Fx 'Pending recorder job: job-1' <<<"$pending_output"
if grep -Fq 'transcript_path:' <<<"$pending_output"; then
  printf 'FAIL: pending job exposed a transcript\n' >&2
  exit 1
fi

failed_json='{"job":"job-1","state":"failed","audio_path":null,"transcript_path":null,"error":"recorder failed"}'
if run_with_status "$failed_json" capture --hub "$hub" --scope "$scope_file" --date 2026-08-26 --recorder-minutes 10 >/dev/null 2>&1; then
  printf 'FAIL: expected failed recorder job to fail\n' >&2
  exit 1
fi

printf 'PASS: assistant workflow guardrail contract\n'
