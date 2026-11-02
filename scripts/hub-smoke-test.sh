#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
source "$ROOT/tests/helpers/shell-scenarios.sh"
SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/ai-hub-smoke.XXXXXX")"
cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT

# Установка не собирает мост календаря и окружение, не обращается к сети.
export HUB_CALENDAR_SKIP_BRIDGE=1
export HUB_CALENDAR_SKIP_VENV=1
export GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=0
export GIT_TERMINAL_PROMPT=0
mkdir -p "$SANDBOX/git-template"
export GIT_TEMPLATE_DIR="$SANDBOX/git-template"
if [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  mkdir -p "$SANDBOX/git-bin"
  cat > "$SANDBOX/git-bin/git" <<'GIT_BINARY'
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
  mkdir -p "$CASE_DIR/home" "$CASE_DIR/tmp"
  export HOME="$CASE_DIR/home" TMPDIR="$CASE_DIR/tmp"
  HUB="$CASE_DIR/_ai-hub"
  OUTPUT="$CASE_DIR/output"
}

run_product() {
  local expected="$1" accepted="$2" diagnostic="$3" observed
  shift 3
  scenario_accept_exit "$accepted" "$diagnostic"
  scenario_exec observed "$@" > "$OUTPUT"
  scenario_assert_exit "$expected" "$observed"
}

# Код 1 без stderr — предметный false доверенных test/grep, а не авария.
assert_test() { run_product 0 1 '' test "$@"; }
assert_contains() { run_product 0 1 '' grep -Fq -- "$1" "$2"; }

hub_only_source_layout() {
  new_case
  scenario_begin
  assert_test ! -d "$ROOT/template"
  assert_test -f "$ROOT/modules/core/data/AGENTS.md"
  assert_test -f "$ROOT/modules/core/data/CLAUDE.md"
  assert_test -f "$ROOT/modules/core/data/ai/architecture.md"
  assert_test -f "$ROOT/modules/planning/skills/hub-workflows/SKILL.md"
  assert_test -f "$ROOT/modules/knowledge/skills/hub-knowledge-enable/SKILL.md"
  assert_test -f "$ROOT/modules/knowledge/skills/hub-knowledge-capture/SKILL.md"
  assert_test -f "$ROOT/modules/knowledge/skills/hub-knowledge-review/SKILL.md"
  scenario_pass
}

compact_entry_documents() {
  new_case
  scenario_begin
  # Явное чтение UTF-8 считает символы независимо от языковой настройки.
  local entry
  for entry in AGENTS CLAUDE; do
    run_product 0 0 '' python3 -c 'from pathlib import Path; import sys; print(len(Path(sys.argv[1]).read_text(encoding="utf-8")))' "$ROOT/modules/core/data/$entry.md"
    assert_test "$(< "$OUTPUT")" -lt 6000
  done
  scenario_pass
}

hub_routing_safety_documents() {
  new_case
  scenario_begin
  assert_contains 'без отдельного подтверждения' "$ROOT/modules/core/data/AGENTS.md"
  assert_contains '<hub>/projects' "$ROOT/modules/core/data/AGENTS.md"
  assert_contains 'Проект не может отменять правила Хаба о подтверждении' "$ROOT/modules/core/data/AGENTS.md"
  assert_contains 'hub-project-router' "$ROOT/modules/core/data/AGENTS.md"
  assert_contains 'read-compact-project-index.sh' "$ROOT/modules/core/skills/hub-project-router/SKILL.md"
  assert_contains 'read-compact-task-index.py' "$ROOT/modules/tasks/skills/hub-task-overview/SKILL.md"
  scenario_pass
}

workflow_resource() {
  local resource="$1"
  new_case
  scenario_begin
  assert_test -f "$ROOT/modules/planning/skills/hub-workflows/resources/$resource.md"
  assert_contains "resources/$resource.md" "$ROOT/modules/planning/skills/hub-workflows/SKILL.md"
  scenario_pass
}
workflow_resource_day_plan() { workflow_resource day-plan; }
workflow_resource_evening_review() { workflow_resource evening-review; }
workflow_resource_weekly_review() { workflow_resource weekly-review; }

task_capture_resource() {
  new_case
  scenario_begin
  assert_contains 'resources/capture.md' "$ROOT/modules/tasks/skills/hub-task-overview/SKILL.md"
  assert_test -f "$ROOT/modules/tasks/skills/hub-task-overview/resources/capture.md"
  scenario_pass
}

installs_exact_projects_root() {
  new_case
  scenario_begin
  run_product 0 0 '' bash "$ROOT/scripts/install.sh" "$HUB"
  assert_test -f "$HUB/AGENTS.md"
  assert_test -f "$HUB/ai/architecture.md"
  assert_test -f "$HUB/scripts/read-compact-task-index.py"
  assert_test -d "$HUB/projects"
  run_product 0 1 '' grep -Fqx -- "- $HUB/projects" "$HUB/ai/allowed-roots.md"
  scenario_pass
}

rejects_standalone_install_without_writes() {
  new_case
  scenario_begin
  run_product 2 2 $'Standalone installation is retired. Install the Personal AI Hub, then register/create/migrate the project through Hub workflows.\n' bash "$ROOT/scripts/install.sh" --mode standalone "$CASE_DIR/legacy-project"
  assert_test ! -e "$CASE_DIR/legacy-project"
  scenario_pass
}

repository_consistency_check() {
  new_case
  scenario_begin
  # Снимок поставляемых файлов не включает локальную память открытого проекта.
  # Согласованность проверяем в собственной копии с валидными указателями:
  # содержимое modules/, scripts/, tests/ и README остаётся продуктовым входом.
  local view="$CASE_DIR/source"
  run_product 0 0 '' python3 -B - "$ROOT" "$view" <<'PY_VIEW'
import importlib.util
from pathlib import Path
import sys
root, destination = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('smoke_snapshot', root / 'scripts/mutation-filesystem.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.snapshot(root, destination)
for name in ('AGENTS.md', 'CLAUDE.md'):
    (destination / name).write_text('# Hub-managed entry\n', encoding='utf-8')
PY_VIEW
  run_product 0 1 $'MISMATCH [source of truth] — README lacks the explicit Source Of Truth section\n' bash "$ROOT/scripts/check-consistency.sh" "$view"
  # Сохраняем прежнюю делегацию девяти тестов поставки. Её ненулевой результат
  # не даёт own-credit этому ID: внутренние дочерние исходы здесь не проверены.
  run_product 0 0 '' python3 -B - "$view/tests" <<'PY_SUITE'
import sys
import unittest
suite = unittest.defaultTestLoader.discover(sys.argv[1], pattern='test_hub_only_distribution.py')
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
if result.errors:
    print('Hub-only distribution infrastructure failure.', file=sys.stderr)
    raise SystemExit(3)
if not result.wasSuccessful():
    print('Hub-only distribution assertion failure.', file=sys.stderr)
    raise SystemExit(1)
PY_SUITE
  scenario_pass
}

scenario_declare hub-only-source-layout hub_only_source_layout
scenario_declare compact-entry-documents compact_entry_documents
scenario_declare hub-routing-safety-documents hub_routing_safety_documents
scenario_declare workflow-resource-day-plan workflow_resource_day_plan
scenario_declare workflow-resource-evening-review workflow_resource_evening_review
scenario_declare workflow-resource-weekly-review workflow_resource_weekly_review
scenario_declare task-capture-resource task_capture_resource
scenario_declare installs-exact-projects-root installs_exact_projects_root
scenario_declare rejects-standalone-install-without-writes rejects_standalone_install_without_writes
scenario_declare repository-consistency-check repository_consistency_check
scenario_main "$@"
