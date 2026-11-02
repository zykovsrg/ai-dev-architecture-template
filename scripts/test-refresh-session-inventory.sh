#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$ROOT/tests/helpers/shell-scenarios.sh"
SCRIPT="$ROOT/scripts/refresh-session-inventory.sh"
fixture="$(mktemp -d "${TMPDIR:-/private/tmp}/inventory-scenario.XXXXXX")"
trap 'rm -rf "$fixture"' EXIT

metadata_without_private_text() {
  local rc transcripts output
  scenario_begin
  transcripts="$fixture/transcripts"
  output="$fixture/session-inventory.md"
  mkdir -p "$transcripts"
  touch "$transcripts/first-session.jsonl"
  printf '%s' 'private transcript text' >"$transcripts/second-session.jsonl"
  scenario_exec rc env SESSION_AUDIT_TRANSCRIPT_DIR="$transcripts" SESSION_AUDIT_OUTPUT_PATH="$output" SESSION_AUDIT_NOW='2026-08-28T00:00:00Z' "$SCRIPT"
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 1 ''
  scenario_exec rc grep -Fxq 'Всего сессий: 2' "$output"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc grep -Fq '| `first-session` | 0 |' "$output"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc grep -Fq '| `second-session` | 23 |' "$output"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc grep -Fxq 'Generated: 2026-08-28T00:00:00Z' "$output"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc grep -Fq 'private transcript text' "$output"
  scenario_assert_exit 1 "$rc"
  scenario_pass
}
scenario_declare metadata-without-private-text metadata_without_private_text
scenario_main "$@"
