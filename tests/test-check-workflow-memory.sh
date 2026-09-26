#!/usr/bin/env bash
set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")/.." && pwd -P)/scripts/check-workflow-memory.sh"
FAILED=0

pass() { echo "ok   - $1"; }
fail() { echo "FAIL - $1"; [ -n "${2:-}" ] && echo "       $2"; FAILED=1; }

make_hub() {
  local dir
  dir="$(mktemp -d)"
  mkdir -p "$dir/ai"
  cat >"$dir/ai/workflow-observations.md" <<'OBS'
# Журнал наблюдений

## Записи

- 2026-09-08 | day-plan | friction | пришлось спрашивать про длительность редактуры
OBS
  cat >"$dir/ai/workflow-context.md" <<'CTX'
# Усвоенный контекст

## Правила

- 2026-09-08 | редактура занимает около часа, а не 30 минут | основание: 3 повтора за 2 недели
CTX
  echo "$dir"
}

# 1. корректные файлы проходят
HUB="$(make_hub)"
if bash "$SCRIPT" --hub "$HUB" >/dev/null 2>&1; then
  pass "корректные файлы проходят проверку"
else
  fail "корректные файлы проходят проверку"
fi

# 2. битая строка журнала отвергается
HUB2="$(make_hub)"
echo '- мусор без полей' >>"$HUB2/ai/workflow-observations.md"
if bash "$SCRIPT" --hub "$HUB2" >/dev/null 2>&1; then
  fail "битая строка журнала отвергается" "скрипт завершился успешно"
else
  pass "битая строка журнала отвергается"
fi

# 3. битая строка правила отвергается
HUB3="$(make_hub)"
echo '- 2026-09-08 | правило без основания' >>"$HUB3/ai/workflow-context.md"
if bash "$SCRIPT" --hub "$HUB3" >/dev/null 2>&1; then
  fail "битая строка правила отвергается" "скрипт завершился успешно"
else
  pass "битая строка правила отвергается"
fi

# 4. превышение лимита в 100 правил отвергается
HUB4="$(make_hub)"
i=0
while [ "$i" -lt 100 ]; do
  echo "- 2026-09-08 | правило номер $i | основание: 3 повтора за 2 недели" >>"$HUB4/ai/workflow-context.md"
  i=$((i + 1))
done
OUT="$(bash "$SCRIPT" --hub "$HUB4" 2>&1)" && RC=0 || RC=1
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'too many rules'; then
  pass "лимит в 100 правил проверяется"
else
  fail "лимит в 100 правил проверяется" "$OUT"
fi

# 6. невалидная строка под заголовком "## Схема" в workflow-observations.md не мешает проверке
HUB6="$(make_hub)"
cat >"$HUB6/ai/workflow-observations.md" <<'OBS'
# Журнал наблюдений

## Схема

- YYYY-MM-DD | day-plan|evening-review|weekly-review | friction|calendar | суть

## Записи

- 2026-09-08 | day-plan | friction | пришлось спрашивать про длительность редактуры
OBS
if bash "$SCRIPT" --hub "$HUB6" >/dev/null 2>&1; then
  pass "строка-образец под «## Схема» в workflow-observations.md не мешает проверке"
else
  fail "строка-образец под «## Схема» в workflow-observations.md не мешает проверке"
fi

# 7. невалидная строка под заголовком "## Схема" в workflow-context.md не мешает проверке
HUB7="$(make_hub)"
cat >"$HUB7/ai/workflow-context.md" <<'CTX'
# Усвоенный контекст

## Схема

- YYYY-MM-DD | day-plan|evening-review|weekly-review | friction|calendar | суть

## Правила

- 2026-09-08 | редактура занимает около часа, а не 30 минут | основание: 3 повтора за 2 недели
CTX
if bash "$SCRIPT" --hub "$HUB7" >/dev/null 2>&1; then
  pass "строка-образец под «## Схема» в workflow-context.md не мешает проверке"
else
  fail "строка-образец под «## Схема» в workflow-context.md не мешает проверке"
fi

# 5. отсутствующий файл отвергается
HUB5="$(make_hub)"
rm "$HUB5/ai/workflow-context.md"
if bash "$SCRIPT" --hub "$HUB5" >/dev/null 2>&1; then
  fail "отсутствующий файл отвергается" "скрипт завершился успешно"
else
  pass "отсутствующий файл отвергается"
fi

# 8. ровно 100 правил проходят проверку
HUB8="$(make_hub)"
i=1
while [ "$i" -lt 100 ]; do
  echo "- 2026-09-08 | правило номер $i | основание: 3 повтора за 2 недели" >>"$HUB8/ai/workflow-context.md"
  i=$((i + 1))
done
OUT="$(bash "$SCRIPT" --hub "$HUB8" 2>&1)" && RC=0 || RC=1
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q 'правил: 100'; then
  pass "ровно 100 правил проходят проверку"
else
  fail "ровно 100 правил проходят проверку" "$OUT"
fi

# 9. битая последняя строка без перевода строки отвергается
HUB9="$(make_hub)"
printf '%s' '- мусор без полей' >>"$HUB9/ai/workflow-observations.md"
if bash "$SCRIPT" --hub "$HUB9" >/dev/null 2>&1; then
  fail "битая последняя строка без перевода строки отвергается" "скрипт завершился успешно"
else
  pass "битая последняя строка без перевода строки отвергается"
fi

# 10. битая последняя строка правил без перевода строки отвергается
HUB10="$(make_hub)"
printf '%s' '- 2026-09-08 | правило без основания' >>"$HUB10/ai/workflow-context.md"
if bash "$SCRIPT" --hub "$HUB10" >/dev/null 2>&1; then
  fail "битая последняя строка правил без перевода строки отвергается" "скрипт завершился успешно"
else
  pass "битая последняя строка правил без перевода строки отвергается"
fi

# 11. невозможная дата наблюдения отвергается (локальный кейс до слияния)
HUB11="$(make_hub)"
echo '- 2026-02-30 | day-plan | friction | invalid leap day' >>"$HUB11/ai/workflow-observations.md"
if bash "$SCRIPT" --hub "$HUB11" >/dev/null 2>&1; then
  fail "невозможная дата наблюдения отвергается" "скрипт завершился успешно"
else
  pass "невозможная дата наблюдения отвергается"
fi

exit "$FAILED"
