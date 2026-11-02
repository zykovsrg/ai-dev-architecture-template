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

SCRIPT="$ROOT/modules/learning/scripts/check-workflow-memory.sh"

make_hub() {
  local dir
  dir="$(mktemp -d "$SANDBOX/hub.XXXXXX")"
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
  HUB="$(cd "$dir" && pwd -P)"
  OUTPUT="$HUB/output"
  FIELD="$HUB/field"
}


accepts_valid_memory() {
  make_hub
  scenario_begin
  run_product 0 1 $'ERROR: bad observation line: - 2026-09-08 | day-plan | friction | пришлось спрашивать про длительность редактуры\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

allows_absent_planning_context() {
  make_hub
  rm "$HUB/ai/workflow-context.md"
  scenario_begin
  run_product 0 1 $'ERROR: missing file: ai/workflow-context.md\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

rejects_malformed_observation() {
  make_hub
  printf '%s\n' '- мусор без полей' >> "$HUB/ai/workflow-observations.md"
  scenario_begin
  run_product 1 1 $'ERROR: bad observation line: - мусор без полей\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

rejects_context_without_basis() {
  make_hub
  printf '%s\n' '- 2026-09-08 | правило без основания' >> "$HUB/ai/workflow-context.md"
  scenario_begin
  run_product 1 1 $'ERROR: bad rule line: - 2026-09-08 | правило без основания\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

rejects_over_100_rules() {
  make_hub
  i=0
  while [ "$i" -lt 100 ]; do
    printf '%s\n' "- 2026-09-08 | правило номер $i | основание: 3 повтора за 2 недели" >> "$HUB/ai/workflow-context.md"
    i=$((i + 1))
  done
  scenario_begin
  run_product 1 1 $'ERROR: too many rules: 101 > 100\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

skips_observation_schema_example() {
  make_hub
  cat > "$HUB/ai/workflow-observations.md" <<'OBS'
# Журнал наблюдений

## Схема

- YYYY-MM-DD | day-plan|evening-review|weekly-review | friction|calendar | суть

## Записи

- 2026-09-08 | day-plan | friction | пришлось спрашивать про длительность редактуры
OBS
  scenario_begin
  run_product 0 1 $'ERROR: bad observation line: - YYYY-MM-DD | day-plan|evening-review|weekly-review | friction|calendar | суть\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

skips_context_schema_example() {
  make_hub
  cat > "$HUB/ai/workflow-context.md" <<'CTX'
# Усвоенный контекст

## Схема

- YYYY-MM-DD | day-plan|evening-review|weekly-review | friction|calendar | суть

## Правила

- 2026-09-08 | редактура занимает около часа, а не 30 минут | основание: 3 повтора за 2 недели
CTX
  scenario_begin
  run_product 0 1 $'ERROR: bad rule line: - YYYY-MM-DD | day-plan|evening-review|weekly-review | friction|calendar | суть\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

rejects_missing_observation_file() {
  make_hub
  rm "$HUB/ai/workflow-observations.md"
  scenario_begin
  run_product 1 1 $'ERROR: missing file: ai/workflow-observations.md\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

accepts_exactly_100_rules() {
  make_hub
  i=0
  while [ "$i" -lt 99 ]; do
    printf '%s\n' "- 2026-09-08 | правило номер $i | основание: 3 повтора за 2 недели" >> "$HUB/ai/workflow-context.md"
    i=$((i + 1))
  done
  scenario_begin
  run_product 0 1 $'ERROR: too many rules: 100 > 99\n' bash "$SCRIPT" --hub "$HUB"
  assert_value "$(< "$OUTPUT")" 'ok: наблюдений и правил — формат корректен, правил: 100'
  scenario_pass
}

rejects_final_malformed_observation_no_newline() {
  make_hub
  printf '%s' '- мусор без полей' >> "$HUB/ai/workflow-observations.md"
  scenario_begin
  run_product 1 1 $'ERROR: bad observation line: - мусор без полей\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

rejects_final_malformed_context_no_newline() {
  make_hub
  printf '%s' '- 2026-09-08 | правило без основания' >> "$HUB/ai/workflow-context.md"
  scenario_begin
  run_product 1 1 $'ERROR: bad rule line: - 2026-09-08 | правило без основания\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

rejects_impossible_observation_date() {
  make_hub
  printf '%s\n' '- 2026-02-30 | day-plan | friction | invalid leap day' >> "$HUB/ai/workflow-observations.md"
  scenario_begin
  run_product 1 1 $'ERROR: impossible observation date: - 2026-02-30 | day-plan | friction | invalid leap day\n' bash "$SCRIPT" --hub "$HUB"
  scenario_pass
}

scenario_declare accepts-valid-memory accepts_valid_memory
scenario_declare allows-absent-planning-context allows_absent_planning_context
scenario_declare rejects-malformed-observation rejects_malformed_observation
scenario_declare rejects-context-without-basis rejects_context_without_basis
scenario_declare rejects-over-100-rules rejects_over_100_rules
scenario_declare skips-observation-schema-example skips_observation_schema_example
scenario_declare skips-context-schema-example skips_context_schema_example
scenario_declare rejects-missing-observation-file rejects_missing_observation_file
scenario_declare accepts-exactly-100-rules accepts_exactly_100_rules
scenario_declare rejects-final-malformed-observation-no-newline rejects_final_malformed_observation_no_newline
scenario_declare rejects-final-malformed-context-no-newline rejects_final_malformed_context_no_newline
scenario_declare rejects-impossible-observation-date rejects_impossible_observation_date
scenario_main "$@"
