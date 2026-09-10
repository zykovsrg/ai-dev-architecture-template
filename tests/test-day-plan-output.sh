#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"

printf '%s\n' \
  '## Текущий календарь' '- Нет.' \
  '## Конфликты' '- Нет.' \
  '## Задачи вне календаря' '- Нет.' \
  '## Просроченные задачи' '- Нет.' \
  '## Предлагаемый календарь' '- Нет.' \
  '## Рекомендации' '- Нет обоснованных рекомендаций.' \
  | "$ROOT/scripts/validate-day-plan-output.py"

if printf '%s\n' 'Сейчас сделайте задачу, затем идите на поезд.' | "$ROOT/scripts/validate-day-plan-output.py" >/dev/null 2>&1; then
  echo 'free-form day plan was accepted' >&2
  exit 1
fi

if printf '%s\n' '## Рекомендации' '## Текущий календарь' '## Конфликты' '## Задачи вне календаря' '## Просроченные задачи' '## Предлагаемый календарь' | "$ROOT/scripts/validate-day-plan-output.py" >/dev/null 2>&1; then
  echo 'wrong heading order was accepted' >&2
  exit 1
fi

echo 'day-plan output tests passed'
