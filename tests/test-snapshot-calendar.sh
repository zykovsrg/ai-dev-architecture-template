#!/usr/bin/env bash
set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")/.." && pwd -P)/scripts/snapshot-calendar.sh"
FAILED=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass() { echo "ok   - $1"; }
fail() { echo "FAIL - $1"; [ -n "${2:-}" ] && echo "       $2"; FAILED=1; }

make_hub() {
  local dir
  dir="$(mktemp -d "$TMP/hub.XXXXXX")"
  dir="$(cd "$dir" && pwd -P)"
  mkdir -p "$dir/ai/tmp"
  echo "$dir"
}

# 1. снимок пишется и путь печатается
HUB="$(make_hub)"
OUT="$(printf '%s\n' '09:00|10:00|Редактура|Личный' | bash "$SCRIPT" --hub "$HUB" --at 2026-09-08-0930 2>&1)"
if [[ "$OUT" =~ ^"$HUB/ai/tmp/calendar-snapshots/2026-09-08-0930--captured-"[0-9]+--[0-9]+-[0-9]+\.txt$ ]] && [ -f "$OUT" ]; then
  pass "снимок создан и путь напечатан"
else
  fail "снимок создан и путь напечатан" "$OUT"
fi

# 2. содержимое снимка совпадает со входом
CONTENT="$(cat "$OUT" 2>/dev/null)"
if [ "$CONTENT" = "09:00|10:00|Редактура|Личный" ]; then
  pass "содержимое снимка сохранено дословно"
else
  fail "содержимое снимка сохранено дословно" "$CONTENT"
fi

# 3. битая строка отвергается
HUB2="$(make_hub)"
if printf '%s\n' 'мусор' | bash "$SCRIPT" --hub "$HUB2" --at 2026-09-08-0930 >/dev/null 2>&1; then
  fail "битая строка отвергается" "скрипт завершился успешно"
else
  pass "битая строка отвергается"
fi

# 4. чистка удаляет снимки старше 14 дней по времени съёмки, свежие остаются
# (кэш наблюдений workflow-friction чистит scripts/workflow_friction.py, не этот скрипт)
HUB3="$(make_hub)"
mkdir -p "$HUB3/ai/tmp/calendar-snapshots"
NOW="$(date +%s)"
OLD="$HUB3/ai/tmp/calendar-snapshots/2026-08-01-0900--captured-$((NOW - 15 * 86400))--1-1.txt"
FRESH="$HUB3/ai/tmp/calendar-snapshots/2026-09-05-0900--captured-$((NOW - 86400))--2-2.txt"
: >"$OLD"
: >"$FRESH"
bash "$SCRIPT" --hub "$HUB3" --prune-only >/dev/null 2>&1
if [ ! -f "$OLD" ] && [ -f "$FRESH" ]; then
  pass "чистка удаляет только снимки старше 14 дней"
else
  fail "чистка удаляет только снимки старше 14 дней"
fi

# 5. список снимков за день находит новый формат имени
HUB4="$(make_hub)"
SNAP="$(printf '%s\n' '09:00|10:00|Редактура|Личный' | bash "$SCRIPT" --hub "$HUB4" --at 2026-09-08-0930 2>/dev/null)"
LIST="$(bash "$SCRIPT" --hub "$HUB4" --list --day 2026-09-08 2>&1)"
if [ -n "$SNAP" ] && [ "$LIST" = "$SNAP" ]; then
  pass "список снимков за день находит снимок"
else
  fail "список снимков за день находит снимок" "$LIST"
fi

# 6. невозможная дата в --at отвергается
HUB5="$(make_hub)"
OUT="$(printf '%s\n' '09:00|10:00|Редактура|Личный' | bash "$SCRIPT" --hub "$HUB5" --at 2026-13-45-0930 2>&1)" && RC=0 || RC=1
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'impossible'; then
  pass "невозможная дата в --at отвергается"
else
  fail "невозможная дата в --at отвергается" "$OUT"
fi

# 7. неизвестный флаг отвергается
HUB6="$(make_hub)"
OUT="$(bash "$SCRIPT" --hub "$HUB6" --nope 2>&1)" && RC=0 || RC=1
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'unknown option'; then
  pass "неизвестный флаг отвергается"
else
  fail "неизвестный флаг отвергается" "$OUT"
fi

# 8. строка события с лишним полем отвергается
HUB7="$(make_hub)"
if printf '%s\n' '09:00|10:00|Редактура|Личный|лишнее' | bash "$SCRIPT" --hub "$HUB7" --at 2026-09-08-0930 >/dev/null 2>&1; then
  fail "строка события с лишним полем отвергается" "скрипт завершился успешно"
else
  pass "строка события с лишним полем отвергается"
fi

# 9. невозможный месяц в --at отвергается (локальный кейс до слияния)
HUB8="$(make_hub)"
if printf '%s\n' '09:00|10:00|Редактура|Личный' | bash "$SCRIPT" --hub "$HUB8" --at 2026-99-99-0900 >/dev/null 2>&1; then
  fail "невозможный месяц в --at отвергается" "скрипт завершился успешно"
else
  pass "невозможный месяц в --at отвергается"
fi

# 10. два снимка на один --at не перезаписывают друг друга (локальный кейс до слияния)
HUB9="$(make_hub)"
FIRST="$(printf '%s\n' '09:00|10:00|First|Calendar' | bash "$SCRIPT" --hub "$HUB9" --at 2026-09-09-0900 2>/dev/null)"
SECOND="$(printf '%s\n' '10:00|11:00|Second|Calendar' | bash "$SCRIPT" --hub "$HUB9" --at 2026-09-09-0900 2>/dev/null)"
if [ "$FIRST" != "$SECOND" ] && grep -Fqx '09:00|10:00|First|Calendar' "$FIRST" 2>/dev/null && grep -Fqx '10:00|11:00|Second|Calendar' "$SECOND" 2>/dev/null; then
  pass "два снимка на один момент времени не перезаписывают друг друга"
else
  fail "два снимка на один момент времени не перезаписывают друг друга" "first=$FIRST second=$SECOND"
fi

exit "$FAILED"
