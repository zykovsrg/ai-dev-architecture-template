#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
transcript_dir=${SESSION_AUDIT_TRANSCRIPT_DIR:-/Users/zykovsrg/.claude/projects/-Users-zykovsrg-Documents-vibecode--ai-hub}
output_path=${SESSION_AUDIT_OUTPUT_PATH:-$project_root/knowledge/session-audit/session-inventory.md}
generated_at=${SESSION_AUDIT_NOW:-$(date -u '+%Y-%m-%dT%H:%M:%SZ')}

if [ ! -d "$transcript_dir" ]; then
  printf 'Transcript directory does not exist: %s\n' "$transcript_dir" >&2
  exit 1
fi

output_dir=$(dirname -- "$output_path")
mkdir -p "$output_dir"
rows_path="$output_path.rows.$$"
temp_path="$output_path.tmp.$$"
trap 'rm -f "$rows_path" "$temp_path"' EXIT HUP INT TERM

find "$transcript_dir" -maxdepth 1 -type f -name '*.jsonl' -print |
  while IFS= read -r transcript_path; do
    filename=$(basename -- "$transcript_path")
    session_id=${filename%.jsonl}
    bytes=$(stat -f '%z' "$transcript_path")
    modified_epoch=$(stat -f '%m' "$transcript_path")
    modified_at=$(date -r "$modified_epoch" -u '+%Y-%m-%dT%H:%M:%SZ')
    printf '| `%s` | %s | %s |\n' "$session_id" "$bytes" "$modified_at"
  done | sort > "$rows_path"

session_count=$(wc -l < "$rows_path" | tr -d ' ')
{
  printf '%s\n' '---'
  printf '%s\n' 'type: generated-inventory'
  printf '%s\n' '---'
  printf '%s\n\n' '# Индекс metadata сессий хаба'
  printf 'Generated: %s\n' "$generated_at"
  printf 'Всего сессий: %s\n\n' "$session_count"
  printf '%s\n' 'Этот файл содержит только metadata файлов транскриптов. Содержимое сессий не читалось.'
  printf '%s\n\n' 'Для чтения транскрипта пользователь должен отдельно подтвердить точный ID.'
  printf '%s\n' '| ID | Байт | Изменён |'
  printf '%s\n' '|---|---:|---|'
  cat "$rows_path"
} > "$temp_path"

mv "$temp_path" "$output_path"
