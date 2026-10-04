#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
VALIDATOR="$ROOT/scripts/validate-day-plan-output.py"
printf '%s\n' '## Текущий календарь' '- Нет.' '## Синхронизация' '- Нет.' '## Просроченные задачи' '- Нет.' | python3 "$VALIDATOR"
for draft in freeform legacy reordered extra; do
  case "$draft" in
    freeform) text='Сейчас сделайте задачу.' ;;
    legacy) text=$'## Текущий календарь\n- Нет.\n## Задачи вне календаря\n- Нет.\n## Просроченные задачи\n- Нет.\n## Рекомендации\n- Нет.\n## Синхронизация\n- Нет.' ;;
    reordered) text=$'## Текущий календарь\n- Нет.\n## Просроченные задачи\n- Нет.\n## Синхронизация\n- Нет.' ;;
    extra) text=$'## Текущий календарь\n- Нет.\n## Синхронизация\n- Нет.\n## Просроченные задачи\n- Нет.\n## Рекомендации\n- Нет.' ;;
  esac
  if printf '%s\n' "$text" | python3 "$VALIDATOR" >/dev/null 2>&1; then
    echo "invalid day-plan accepted: $draft" >&2; exit 1
  fi
done
echo 'day-plan output tests passed'
