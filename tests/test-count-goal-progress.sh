#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$ROOT/tests/helpers/shell-scenarios.sh"
SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/shell-memory-goals.XXXXXX")"
cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT

# Каждый продуктовый запуск сохраняет stdout отдельно, а stderr проверяет сборщик.
run_product() {
  local expected="$1" accepted="$2" diagnostic="$3" observed
  shift 3
  scenario_accept_exit "$accepted" "$diagnostic"
  scenario_exec observed "$@" > "$OUTPUT"
  scenario_assert_exit "$expected" "$observed"
}

# Нормальный false доверенного oracle: код 1 и пустой stderr. Сбой test/grep/awk
# остаётся инфраструктурой; он не превращается в собственное утверждение.
assert_value() {
  local observed
  scenario_accept_exit 1 ''
  scenario_exec observed test "$1" = "$2"
  scenario_assert_exit 0 "$observed"
}
assert_contains() {
  local observed
  scenario_accept_exit 1 ''
  scenario_exec observed grep -Fq -- "$1" "$OUTPUT"
  scenario_assert_exit 0 "$observed"
}
assert_absent() {
  local observed
  scenario_accept_exit 1 ''
  scenario_exec observed grep -Fiq -- "$1" "$OUTPUT"
  scenario_assert_exit 1 "$observed"
}
assert_fields() {
  local observed
  scenario_accept_exit 0 ''
  scenario_exec observed awk -F'\t' "$1" "$OUTPUT" > "$FIELD"
  scenario_assert_exit 0 "$observed"
  assert_value "$(< "$FIELD")" "$2"
}

SCRIPT="$ROOT/modules/goals/scripts/count-goal-progress.sh"

make_hub() {
  local dir
  dir="$(mktemp -d "$SANDBOX/hub.XXXXXX")"
  mkdir -p "$dir/ai"
  cat >"$dir/ai/archiprojects.md" <<'ARCHI'
# Archiprojects

## Schema

## <archiproject-id>

```yaml
id: <archiproject-id>
name: <human name>
status: <status>
kind: group
```

## hadassah

```yaml
id: hadassah
name: Хадасса
status: active
kind: group
```
ARCHI
  cat >"$dir/ai/goals.md" <<'GOALS'
# Goals

## Schema

## <goal-id>

```yaml
id: <goal-id>
name: <human name>
status: <status>
group: <archiproject-group-id>
target: <target>
unit: <unit>
due: YYYY-MM-DD or none
```

## promo-32

```yaml
id: promo-32
name: 32 промо-страницы
status: active
group: hadassah
target: 32
unit: pages
due: 2026-09-30
```
GOALS
  cat >"$dir/ai/goal-log.md" <<'LOG'
# Goal Log

| дата | goal_id | сколько | проект | заметка |
| --- | --- | --- | --- | --- |
| 2026-08-20 | promo-32 | 9 | — | задел на старте счётчика |
| 2026-09-05 | promo-32 | 2 | release-page-endoscopy-center | эндоскопия |
| 2026-09-06 | promo-32 | 1 | release-page-stroke-center | инсульт |
LOG
  HUB="$(cd "$dir" && pwd -P)"
  OUTPUT="$HUB/output"
  FIELD="$HUB/field"
}


make_pace_hub() {
  local due="$1"
  local dir
  dir="$(mktemp -d "$SANDBOX/hub.XXXXXX")"
  mkdir -p "$dir/ai"
  cat >"$dir/ai/archiprojects.md" <<'ARCHI'
# Archiprojects

## pace-group

```yaml
id: pace-group
name: Pace group
status: active
kind: group
```
ARCHI
  cat >"$dir/ai/goals.md" <<GOALS
# Goals

## pace-test

\`\`\`yaml
id: pace-test
name: Pace test
status: active
group: pace-group
target: 100
unit: units
due: $due
\`\`\`
GOALS
  cat >"$dir/ai/goal-log.md" <<'LOG'
# Goal Log

| дата | goal_id | сколько | проект | заметка |
| --- | --- | --- | --- | --- |
LOG
  HUB="$(cd "$dir" && pwd -P)"
  OUTPUT="$HUB/output"
  FIELD="$HUB/field"
}


reads_goals_and_skips_schema_placeholder() {
  make_hub
  scenario_begin
  run_product 0 1 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --format tsv
  assert_fields 'END{print NR}' '1'
  assert_fields '{print $1"/"$3"/"$4"/"$6}' 'promo-32/32/pages/2026-09-30'
  scenario_pass
}

does_not_read_goals_from_group_registry() {
  make_hub
  cat >> "$HUB/ai/archiprojects.md" <<'ARCHI'

## legacy-goal

```yaml
id: legacy-goal
name: Legacy goal left in the group registry
status: active
kind: group
```
ARCHI
  scenario_begin
  run_product 1 1 "ERROR: unknown goal: legacy-goal"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal legacy-goal
  scenario_pass
}

rejects_unknown_goal_group() {
  make_hub
  cat >> "$HUB/ai/goals.md" <<'GOALS'

## bad-group-goal

```yaml
id: bad-group-goal
name: Goal with unknown group
status: active
group: no-such-group
target: 10
unit: pages
due: 2026-09-30
```
GOALS
  scenario_begin
  run_product 1 1 "ERROR: unknown archiproject group for goal bad-group-goal in $HUB/ai/goals.md: no-such-group"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07
  scenario_pass
}

distinguishes_invalid_group_registry() {
  make_hub
  cat > "$HUB/ai/archiprojects.md" <<'ARCHI'
# Archiprojects

## hadassah

```yaml
id: hadassah
name: Хадасса
status: active
```
ARCHI
  scenario_begin
  run_product 1 1 "ERROR: group registry invalid: ERROR: missing kind in archiproject entry: hadassah"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07
  scenario_pass
}

renders_group_in_text_and_tsv() {
  make_hub
  scenario_begin
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal promo-32
  assert_contains 'группа: hadassah'
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal promo-32 --format tsv
  assert_fields '{print $13}' 'hadassah'
  scenario_pass
}

counts_progress_remaining_and_pace() {
  make_hub
  scenario_begin
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal promo-32
  assert_contains 'выпущено 12 / 32 pages'
  assert_contains 'осталось 20'
  assert_contains 'темпа не хватает'
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-04 --goal promo-32
  assert_contains 'выпущено 9 / 32 pages'
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal promo-32 --format tsv
  assert_fields '{print $2"/"$5"/"$12}' '12/20/slow'
  scenario_pass
}

rate7_window_boundary() {
  make_pace_hub "2099-01-01"
  printf '%s\n' '| 2026-09-01 | pace-test | 5 | — | inside |' >> "$HUB/ai/goal-log.md"
  printf '%s\n' '| 2026-08-31 | pace-test | 100 | — | outside |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal pace-test --format tsv
  assert_fields '{print $8}' '5'
  scenario_pass
}

rate28_window_and_weekly_average() {
  make_pace_hub "2099-01-01"
  printf '%s\n' '| 2026-08-11 | pace-test | 8 | — | inside |' >> "$HUB/ai/goal-log.md"
  printf '%s\n' '| 2026-08-10 | pace-test | 100 | — | outside |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal pace-test --format tsv
  assert_fields '{print $9}' '2'
  scenario_pass
}

pace_equality_is_ok() {
  make_pace_hub "2026-09-14"
  printf '%s\n' '| 2026-08-01 | pace-test | 80 | — | outside |' >> "$HUB/ai/goal-log.md"
  printf '%s\n' '| 2026-09-05 | pace-test | 10 | — | inside |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal pace-test --format tsv
  assert_fields '{print $2"/"$5"/"$8"/"$10"/"$12}' '90/10/10/10/ok'
  scenario_pass
}

pace_below_boundary_is_slow() {
  make_pace_hub "2026-09-14"
  printf '%s\n' '| 2026-08-01 | pace-test | 80 | — | outside |' >> "$HUB/ai/goal-log.md"
  printf '%s\n' '| 2026-09-05 | pace-test | 9 | — | inside |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal pace-test --format tsv
  assert_fields '{print $2"/"$5"/"$8"/"$10"/"$12}' '89/11/9/11/slow'
  scenario_pass
}

counts_final_row_without_newline() {
  make_hub
  printf '%s' '| 2026-09-02 | promo-32 | 7 | p | b |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal promo-32
  assert_contains 'выпущено 19 / 32 pages'
  scenario_pass
}

parses_indented_row() {
  make_hub
  printf '%s\n' '  | 2026-09-06 | promo-32 | 5 | p | b |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 0 0 '' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal promo-32
  assert_contains 'выпущено 17 / 32 pages'
  scenario_pass
}

header_values_not_skipped_in_data() {
  make_hub
  printf '%s\n' '| notadate | goal_id | -3 | p | b |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 1 1 "ERROR: bad date in $HUB/ai/goal-log.md: notadate"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal promo-32
  scenario_pass
}

rejects_duplicate_goal_id() {
  make_hub
  cat >> "$HUB/ai/goals.md" <<'GOALS'

## promo-32-dup

```yaml
id: promo-32
name: Duplicate
status: active
group: hadassah
target: 10
unit: pages
due: 2026-09-30
```
GOALS
  scenario_begin
  run_product 1 1 "ERROR: duplicate goal_id in $HUB/ai/goals.md: promo-32"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal promo-32
  scenario_pass
}

tsv_decimal_dot_under_comma_locale() {
  make_pace_hub "2099-01-01"
  printf '%s\n' '| 2026-09-01 | pace-test | 34 | — | fractional |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 0 0 '' env LC_ALL=de_DE.UTF-8 bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal pace-test --format tsv
  assert_fields '{print $9}' '8.5'
  scenario_pass
}

text_decimal_comma_under_comma_locale() {
  make_pace_hub "2099-01-01"
  printf '%s\n' '| 2026-09-01 | pace-test | 34 | — | fractional |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 0 0 '' env LC_ALL=de_DE.UTF-8 bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --goal pace-test
  assert_contains '8,5/нед за 28 дней'
  assert_absent 'invalid number'
  scenario_pass
}

rate_window_stable_across_dst() {
  make_pace_hub "2099-01-01"
  printf '%s\n' '| 2026-10-22 | pace-test | 7 | — | across DST |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 0 0 '' env TZ=UTC bash "$SCRIPT" --hub "$HUB" --as-of 2026-10-28 --goal pace-test --format tsv
  assert_fields '{print $8}' '7'
  run_product 0 0 '' env TZ=Europe/Berlin bash "$SCRIPT" --hub "$HUB" --as-of 2026-10-28 --goal pace-test --format tsv
  assert_fields '{print $8}' '7'
  scenario_pass
}

rejects_unknown_goal_in_log() {
  make_hub
  printf '%s\n' '| 2026-09-06 | no-such-goal | 1 | — | — |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 1 1 "ERROR: unknown goal_id in $HUB/ai/goal-log.md: no-such-goal"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07
  scenario_pass
}

rejects_group_id_is_not_goal() {
  make_hub
  printf '%s\n' '| 2026-09-06 | hadassah | 1 | — | — |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 1 1 "ERROR: unknown goal_id in $HUB/ai/goal-log.md: hadassah"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07
  scenario_pass
}

rejects_malformed_log_date() {
  make_hub
  printf '%s\n' '| 06.09.2026 | promo-32 | 1 | — | — |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 1 1 "ERROR: bad date in $HUB/ai/goal-log.md: 06.09.2026"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07
  scenario_pass
}

rejects_nonpositive_amount() {
  make_hub
  printf '%s\n' '| 2026-09-06 | promo-32 | 0 | — | — |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 1 1 "ERROR: amount must be a positive integer in $HUB/ai/goal-log.md: 0"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07
  scenario_pass
}

rejects_short_log_row() {
  make_hub
  printf '%s\n' '| 2026-09-06 | promo-32 |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 1 1 "ERROR: malformed row in $HUB/ai/goal-log.md:  2026-09-06 | promo-32 |"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07
  scenario_pass
}

rejects_empty_log_date() {
  make_hub
  printf '%s\n' '| | promo-32 | 1 | — | — |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 1 1 "ERROR: bad date in $HUB/ai/goal-log.md: "$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07
  scenario_pass
}

rejects_four_column_log_row() {
  make_hub
  printf '%s\n' '| 2026-09-06 | promo-32 | 5 | p' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 1 1 "ERROR: malformed row in $HUB/ai/goal-log.md:  2026-09-06 | promo-32 | 5 | p"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07
  scenario_pass
}

rejects_oversized_amount() {
  make_hub
  printf '%s\n' '| 2026-09-06 | promo-32 | 99999999999999999999 | p | b |' >> "$HUB/ai/goal-log.md"
  scenario_begin
  run_product 1 1 "ERROR: amount too large in $HUB/ai/goal-log.md: 99999999999999999999"$'\n' bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07
  scenario_pass
}

scenario_declare reads-goals-and-skips-schema-placeholder reads_goals_and_skips_schema_placeholder
scenario_declare does-not-read-goals-from-group-registry does_not_read_goals_from_group_registry
scenario_declare rejects-unknown-goal-group rejects_unknown_goal_group
scenario_declare distinguishes-invalid-group-registry distinguishes_invalid_group_registry
scenario_declare renders-group-in-text-and-tsv renders_group_in_text_and_tsv
scenario_declare counts-progress-remaining-and-pace counts_progress_remaining_and_pace
scenario_declare rate7-window-boundary rate7_window_boundary
scenario_declare rate28-window-and-weekly-average rate28_window_and_weekly_average
scenario_declare pace-equality-is-ok pace_equality_is_ok
scenario_declare pace-below-boundary-is-slow pace_below_boundary_is_slow
scenario_declare counts-final-row-without-newline counts_final_row_without_newline
scenario_declare parses-indented-row parses_indented_row
scenario_declare header-values-not-skipped-in-data header_values_not_skipped_in_data
scenario_declare rejects-duplicate-goal-id rejects_duplicate_goal_id
scenario_declare tsv-decimal-dot-under-comma-locale tsv_decimal_dot_under_comma_locale
scenario_declare text-decimal-comma-under-comma-locale text_decimal_comma_under_comma_locale
scenario_declare rate-window-stable-across-dst rate_window_stable_across_dst
scenario_declare rejects-unknown-goal-in-log rejects_unknown_goal_in_log
scenario_declare rejects-group-id-is-not-goal rejects_group_id_is_not_goal
scenario_declare rejects-malformed-log-date rejects_malformed_log_date
scenario_declare rejects-nonpositive-amount rejects_nonpositive_amount
scenario_declare rejects-short-log-row rejects_short_log_row
scenario_declare rejects-empty-log-date rejects_empty_log_date
scenario_declare rejects-four-column-log-row rejects_four_column_log_row
scenario_declare rejects-oversized-amount rejects_oversized_amount
scenario_main "$@"
