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
Read-only workflow: no changes were made.

## Текущий календарь
- 09:00–10:00 — дела/работа

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
Read-only workflow: no changes were made.

## Текущий календарь
- 09:00–10:00 — дела/работа

## Синхронизация
- Нет.

## Просроченные задачи
- Нет.

Разбор сессий: последний — 2026-10-04; новых сессий: «Клод» 1, «Кодекс» 0; записей журнала: 0. Запустить разбор?
DRAFT
  scenario_accept_exit 1 'ERROR: expected exactly the three day-plan headings in order'$'\n'
  scenario_exec rc python3 "$VALIDATOR" <"$TMP/input" >"$TMP/output"
  scenario_assert_exit 0 "$rc"
  scenario_accept_exit 1 ''
  scenario_exec rc grep -Fxq 'day-plan structure valid' "$TMP/output"
  scenario_assert_exit 0 "$rc"
  scenario_pass
}

case_2() {
  local rc
  scenario_begin
  cat >"$TMP/input" <<'DRAFT'
Read-only workflow: no changes were made.

## Текущий календарь
- 09:00–10:00 — дела/работа

## Синхронизация
- Нет.

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
Read-only workflow: no changes were made.

## Текущий календарь
- 09:00–10:00 — дела/работа

## Конфликты
- Нет.

## Просроченные задачи
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
## Просроченные задачи
- Нет.

## Текущий календарь
- 09:00–10:00 — дела/работа

## Синхронизация
- Нет.
DRAFT
  scenario_accept_exit 1 'ERROR: expected exactly the three day-plan headings in order'$'\n'
  scenario_exec rc python3 "$VALIDATOR" <"$TMP/input" >"$TMP/output"
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

case_5() {
  local rc
  scenario_begin
  cat >"$TMP/input" <<'DRAFT'
Read-only workflow: no changes were made.

## Текущий календарь
- 09:00–10:00 — дела/работа

## Синхронизация

## Просроченные задачи
- Нет.
DRAFT
  scenario_accept_exit 1 'ERROR: empty day-plan section: ## Синхронизация'$'\n'
  scenario_exec rc python3 "$VALIDATOR" <"$TMP/input" >"$TMP/output"
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

case_6() {
  local rc
  scenario_begin
  cat >"$TMP/input" <<'DRAFT'
Read-only workflow: no changes were made.

## Текущий календарь
- 09:00–10:00 — дела/работа

- Нет.

## Просроченные задачи
- Нет.
DRAFT
  scenario_accept_exit 1 'ERROR: expected exactly the three day-plan headings in order'$'\n'
  scenario_exec rc python3 "$VALIDATOR" <"$TMP/input" >"$TMP/output"
  scenario_assert_exit 1 "$rc"
  scenario_pass
}

scenario_declare accepts-complete-structure case_0
scenario_declare accepts-session-review-tail case_1
scenario_declare rejects-missing-overdue-heading case_2
scenario_declare rejects-retired-conflicts-heading case_3
scenario_declare rejects-reordered-headings case_4
scenario_declare rejects-empty-section case_5
scenario_declare rejects-missing-sync-heading case_6
scenario_main "$@"
