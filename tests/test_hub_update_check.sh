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

# Только локальные фикстуры и файловый протокол Гита; пользовательские настройки
# не влияют на временную историю. Установка не собирает календарь и окружение.
export HUB_CALENDAR_SKIP_BRIDGE=1
export HUB_CALENDAR_SKIP_VENV=1
export GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=0
export GIT_AUTHOR_NAME=test
export GIT_AUTHOR_EMAIL=test@example.com
export GIT_COMMITTER_NAME=test
export GIT_COMMITTER_EMAIL=test@example.com
export GIT_AUTHOR_DATE='2026-10-17T00:00:00Z'
export GIT_COMMITTER_DATE='2026-10-17T00:00:00Z'
mkdir -p "$SANDBOX/git-template"
export GIT_TEMPLATE_DIR="$SANDBOX/git-template"
export GIT_ALLOW_PROTOCOL=file
export GIT_TERMINAL_PROMPT=0

# На macOS /usr/bin/git — системный посредник, который может запустить
# xcodebuild и напечатать диагностику настройки Xcode. Фикстура использует
# установленный исполняемый git напрямую; диагностика продукта не подавляется.
if [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  mkdir -p "$SANDBOX/git-bin"
  cat >"$SANDBOX/git-bin/git" <<'GIT_BINARY'
#!/bin/sh
exec /Library/Developer/CommandLineTools/usr/bin/git "$@"
GIT_BINARY
  chmod +x "$SANDBOX/git-bin/git"
  export PATH="$SANDBOX/git-bin:$PATH"
  export GIT_EXEC_PATH=/Library/Developer/CommandLineTools/usr/libexec/git-core
fi

new_case() {
  CASE_DIR="$(mktemp -d "$SANDBOX/case.XXXXXX")"
  CASE_DIR="$(cd "$CASE_DIR" && pwd -P)"
  WORK="$CASE_DIR/source"
  HUB="$CASE_DIR/_ai-hub"
  REMOTE="$CASE_DIR/remote.git"
  OUTPUT="$CASE_DIR/output"
  FIELD="$CASE_DIR/field"
}

snapshot_source() {
  # Снимок нынешних разрешённых входов: без .git, .venv, секретных скрытых
  # деревьев и аудитов. Старые сохранённые исходники не используются.
  run_product 0 0 '' python3 -B - "$ROOT" "$WORK" <<'PY_SNAPSHOT'
import importlib.util
from pathlib import Path
import sys
root, destination = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('fixture_snapshot', root / 'scripts/mutation-filesystem.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.snapshot(root, destination)
PY_SNAPSHOT
}

check_reports_managed_file_drift() {
  new_case
  scenario_begin
  snapshot_source
  mkdir -p "$HUB"
  run_product 0 0 '' bash "$WORK/scripts/install.sh" --mode hub "$HUB"
  printf '\n<!-- local drift -->\n' >> "$HUB/AGENTS.md"
  # Предметный --check сообщает расхождение в stdout и возвращает 1 без stderr.
  run_product 1 1 '' bash "$WORK/scripts/update-installed-hub.sh" --hub "$HUB" --source "$WORK" --check
  assert_contains 'Managed files differ'
  assert_contains 'AGENTS.md'
  scenario_pass
}

updater_delegation_and_pinning_contract() {
  new_case
  scenario_begin
  snapshot_source
  OUTPUT="$WORK/scripts/update-installed-hub.sh"
  assert_contains 'hub_release.py'
  assert_contains 'ls-remote'
  assert_contains 'RESOLVED_SHA'
  scenario_pass
}

remote_preview_stays_pinned_after_branch_move() {
  new_case
  scenario_begin
  snapshot_source
  run_product 0 0 '' git -C "$WORK" init -q
  run_product 0 0 '' git -C "$WORK" config user.name test
  run_product 0 0 '' git -C "$WORK" config user.email test@example.com
  run_product 0 0 '' git -C "$WORK" add -A -f
  run_product 0 0 '' git -C "$WORK" commit -q -m 'fixture: current source A'
  run_product 0 0 '' git init -q --bare "$REMOTE"
  run_product 0 0 '' git -C "$WORK" remote add fixture "$REMOTE"
  run_product 0 0 '' git -C "$WORK" push -q fixture HEAD:refs/heads/moving-source
  run_product 0 0 '' git -C "$WORK" rev-parse HEAD
  SHA_A="$(< "$OUTPUT")"

  mkdir -p "$HUB"
  run_product 0 0 '' bash "$WORK/scripts/install.sh" --mode hub "$HUB"
  # Установка добавляет исключения среды после записи выпуска. Этот файл
  # выравнивается с A, чтобы проверять перемещение ветки независимо от исключений.
  cp "$WORK/modules/core/data/.gitignore" "$HUB/.gitignore"
  run_product 0 0 '' env HUB_RELEASE_REPO_URL="$REMOTE" bash "$WORK/scripts/update-installed-hub.sh" --hub "$HUB" --ref moving-source --dry-run
  assert_fields '/Resolved revision:/ {sub(/^Resolved revision: /,""); print; exit}' "$SHA_A"
  scenario_accept_exit 0 ''
  scenario_exec code awk '/Plan SHA256:/ {print $3; exit}' "$OUTPUT" > "$FIELD"
  scenario_assert_exit 0 "$code"
  PLAN_SHA="$(< "$FIELD")"
  scenario_accept_exit 1 ''
  scenario_exec code test -n "$PLAN_SHA"
  scenario_assert_exit 0 "$code"

  printf '\n<!-- branch moved to B -->\n' >> "$WORK/modules/core/data/AGENTS.md"
  run_product 0 0 '' git -C "$WORK" add modules/core/data/AGENTS.md
  run_product 0 0 '' git -C "$WORK" commit -q -m 'fixture: move source branch'
  run_product 0 0 '' git -C "$WORK" rev-parse HEAD
  SHA_B="$(< "$OUTPUT")"
  scenario_accept_exit 1 ''
  scenario_exec code test "$SHA_A" != "$SHA_B"
  scenario_assert_exit 0 "$code"
  run_product 0 0 '' git -C "$WORK" push -q fixture HEAD:refs/heads/moving-source

  run_product 0 1 $'ERROR: confirmed plan differs from current preview\n' env HUB_RELEASE_REPO_URL="$REMOTE" bash "$WORK/scripts/update-installed-hub.sh" --hub "$HUB" --ref moving-source --apply --allow-dirty --confirm-plan "$PLAN_SHA" --confirm-source-sha "$SHA_A"
  OUTPUT="$HUB/AGENTS.md"
  assert_absent 'branch moved to B'
  scenario_pass
}

scenario_declare check-reports-managed-file-drift check_reports_managed_file_drift
scenario_declare updater-delegation-and-pinning-contract updater_delegation_and_pinning_contract
scenario_declare remote-preview-stays-pinned-after-branch-move remote_preview_stays_pinned_after_branch_move
scenario_main "$@"
