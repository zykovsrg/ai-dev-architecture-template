#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$ROOT/scripts/refresh-session-inventory.sh"
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT

transcripts="$fixture/transcripts"
output="$fixture/session-inventory.md"
mkdir -p "$transcripts"
touch "$transcripts/first-session.jsonl"
printf '%s' 'private transcript text' > "$transcripts/second-session.jsonl"

SESSION_AUDIT_TRANSCRIPT_DIR="$transcripts" \
SESSION_AUDIT_OUTPUT_PATH="$output" \
SESSION_AUDIT_NOW='2026-08-28T00:00:00Z' \
"$SCRIPT"

grep -Fqx 'Всего сессий: 2' "$output"
grep -Fq '| `first-session` | 0 |' "$output"
grep -Fq '| `second-session` | 23 |' "$output"
grep -Fqx 'Generated: 2026-08-28T00:00:00Z' "$output"
if grep -Fq 'private transcript text' "$output"; then
  printf 'FAIL: inventory contains transcript text\n' >&2
  exit 1
fi

printf 'PASS: refresh-session-inventory\n'
