#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HUB_DIR=""

usage() {
  echo "Usage: $0 --hub HUB_DIRECTORY" >&2
  exit 64
}

[ "$#" -eq 2 ] || usage
[ "$1" = "--hub" ] || usage
HUB_DIR="$(cd "$2" && pwd -P)"
REGISTRY="$HUB_DIR/ai/project-registry.md"
[ -f "$REGISTRY" ] || { echo "ERROR: missing project registry" >&2; exit 2; }

failed=0
while IFS=$'\t' read -r project_id project_path; do
  for kind in current future paused; do
    case "$kind" in
      current) filename="current-task.md" ;;
      future) filename="future-tasks.md" ;;
      paused) filename="paused-tasks.md" ;;
    esac
    task_file="$project_path/ai/$filename"
    if [ ! -f "$task_file" ]; then
      echo "ERROR: $project_id: missing ai/$filename" >&2
      failed=1
      continue
    fi
    if ! python3 "$SCRIPT_DIR/task_records.py" read --file "$task_file" --project-id "$project_id" --kind "$kind" >/dev/null; then
      echo "ERROR: $project_id: invalid $kind task records" >&2
      failed=1
    fi
  done
done < <(awk '/^## / {id=$2} /^Path: / {print id "\t" substr($0, 7)}' "$REGISTRY")

[ "$failed" -eq 0 ] || exit 1
echo "OK: all registered project task records are canonical"
