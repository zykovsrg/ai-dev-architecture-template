#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SOURCE="$(cd "$ROOT/../.." && pwd -P)"
VALIDATOR="$ROOT/scripts/validate-day-plan-output.py"
source "$SOURCE/tests/helpers/shell-scenarios.sh"
TMP="$(mktemp -d "${TMPDIR:-/private/tmp}/day-plan-scenarios.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# Каждый случай получает независимый вход и точный договор предметного отказа.
case_0() {
  local rc
  scenario_begin
  cat >"$TMP/input" <<'DRAFT'
## Текущий календарь
- Нет.
## Синхронизация
- Нет.
## Просроченные задачи
- Нет.
DRAFT
  scenario_accept_exit 1 'ERROR: expected exactly the three day-plan headings in order'$'\n'
  scenario_exec rc python3 "$VALIDATOR" <"$TMP/input" >"$TMP/output"
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 1 ''
  scenario_exec rc grep -Fxq 'day-plan structure valid' "$TMP/output"
  scenario_assert_exit 0 "$rc"
  scenario_pass
}

case_1() {
  local rc
  scenario_begin
  cat >"$TMP/input" <<'DRAFT'
Сейчас сделайте задачу.
DRAFT
  scenario_accept_exit 1 'ERROR: expected exactly the three day-plan headings in order'$'\n'
  scenario_exec rc python3 "$VALIDATOR" <"$TMP/input" >"$TMP/output"
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

case_2() {
  local rc
  scenario_begin
  cat >"$TMP/input" <<'DRAFT'
## Текущий календарь
- Нет.
## Задачи вне календаря
- Нет.
## Просроченные задачи
- Нет.
## Рекомендации
- Нет.
## Синхронизация
- Нет.
DRAFT
  scenario_accept_exit 1 'ERROR: expected exactly the three day-plan headings in order'$'\n'
  scenario_exec rc python3 "$VALIDATOR" <"$TMP/input" >"$TMP/output"
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

case_3() {
  local rc
  scenario_begin
  cat >"$TMP/input" <<'DRAFT'
## Текущий календарь
- Нет.
## Просроченные задачи
- Нет.
## Синхронизация
- Нет.
DRAFT
  scenario_accept_exit 1 'ERROR: expected exactly the three day-plan headings in order'$'\n'
  scenario_exec rc python3 "$VALIDATOR" <"$TMP/input" >"$TMP/output"
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

case_4() {
  local rc
  scenario_begin
  cat >"$TMP/input" <<'DRAFT'
## Текущий календарь
- Нет.
## Синхронизация
- Нет.
## Просроченные задачи
- Нет.
## Рекомендации
- Нет.
DRAFT
  scenario_accept_exit 1 'ERROR: expected exactly the three day-plan headings in order'$'\n'
  scenario_exec rc python3 "$VALIDATOR" <"$TMP/input" >"$TMP/output"
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

scenario_declare accepts-three-headings case_0
scenario_declare rejects-freeform case_1
scenario_declare rejects-legacy-sections case_2
scenario_declare rejects-reordered-sections case_3
scenario_declare rejects-extra-section case_4
scenario_main "$@"
