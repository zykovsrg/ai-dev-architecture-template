#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="."
MAX_RULES=100

die() { echo "ERROR: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --hub) HUB_DIR="${2:?--hub needs a value}"; shift 2 ;;
    *) die "unknown option: $1" ;;
  esac
done

HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
OBS_FILE="$HUB_DIR/ai/workflow-observations.md"
CTX_FILE="$HUB_DIR/ai/workflow-context.md"

[ -f "$OBS_FILE" ] || die "missing file: ai/workflow-observations.md"
[ -f "$CTX_FILE" ] || die "missing file: ai/workflow-context.md"

OBS_RE='^- [0-9]{4}-[0-9]{2}-[0-9]{2} \| (day-plan|evening-review|weekly-review) \| (friction|calendar) \| .+$'
CTX_RE='^- [0-9]{4}-[0-9]{2}-[0-9]{2} \| .+ \| основание: .+$'

SECTION=""
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in "## "*) SECTION="${line#\#\# }"; continue ;; esac
  case "$line" in "- "*) ;; *) continue ;; esac
  [ "$SECTION" = "Схема" ] && continue
  printf '%s' "$line" | grep -Eq "$OBS_RE" || die "bad observation line: $line"
done <"$OBS_FILE"

RULES=0
SECTION=""
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in "## "*) SECTION="${line#\#\# }"; continue ;; esac
  case "$line" in "- "*) ;; *) continue ;; esac
  [ "$SECTION" = "Схема" ] && continue
  printf '%s' "$line" | grep -Eq "$CTX_RE" || die "bad rule line: $line"
  RULES=$((RULES + 1))
done <"$CTX_FILE"

[ "$RULES" -le "$MAX_RULES" ] || die "too many rules: $RULES > $MAX_RULES"
echo "ok: наблюдений и правил — формат корректен, правил: $RULES"
