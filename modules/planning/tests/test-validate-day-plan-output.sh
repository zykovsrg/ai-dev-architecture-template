#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
VALIDATOR="$ROOT/scripts/validate-day-plan-output.py"
FAILED=0

pass() { echo "ok   - $1"; }
fail() { echo "FAIL - $1"; [ -n "${2:-}" ] && echo "       $2"; FAILED=1; }

valid_draft() {
  cat <<'DRAFT'
Read-only workflow: no changes were made.

## Текущий календарь
- 09:00–10:00 — дела/работа

## Синхронизация
- Нет.

## Просроченные задачи
- Нет.
DRAFT
}

OUT="$(valid_draft | python3 "$VALIDATOR" 2>&1)"
if [ $? -eq 0 ] && [ "$OUT" = "day-plan structure valid" ]; then
  pass "полная структура из трёх разделов принимается"
else
  fail "полная структура из трёх разделов принимается" "$OUT"
fi

OUT="$(valid_draft | grep -v '^## Просроченные задачи$' | python3 "$VALIDATOR" 2>&1)"
if [ $? -ne 0 ]; then
  pass "пропущенный раздел отклоняется"
else
  fail "пропущенный раздел отклоняется" "$OUT"
fi

OUT="$(valid_draft | sed 's/^## Синхронизация$/## Конфликты/' | python3 "$VALIDATOR" 2>&1)"
if [ $? -ne 0 ]; then
  pass "удалённый раздел «Конфликты» больше не является частью структуры"
else
  fail "удалённый раздел «Конфликты» больше не является частью структуры" "$OUT"
fi

REORDERED="$(printf '## Просроченные задачи\n- Нет.\n\n## Текущий календарь\n- 09:00–10:00 — дела/работа\n\n## Задачи вне календаря\n- Нет.\n\n## Рекомендации\n- Нет.\n\n## Синхронизация\n- Нет.\n')"
OUT="$(printf '%s' "$REORDERED" | python3 "$VALIDATOR" 2>&1)"
if [ $? -ne 0 ]; then
  pass "нарушенный порядок разделов отклоняется"
else
  fail "нарушенный порядок разделов отклоняется" "$OUT"
fi

OUT="$(valid_draft | sed '/^## Синхронизация$/{n;d;}' | python3 "$VALIDATOR" 2>&1)"
if [ $? -ne 0 ]; then
  pass "пустой раздел отклоняется"
else
  fail "пустой раздел отклоняется" "$OUT"
fi

OUT="$(valid_draft | grep -v '^## Синхронизация$' | python3 "$VALIDATOR" 2>&1)"
if [ $? -ne 0 ]; then
  pass "план без раздела «Синхронизация» отклоняется"
else
  fail "план без раздела «Синхронизация» отклоняется" "$OUT"
fi

exit "$FAILED"
