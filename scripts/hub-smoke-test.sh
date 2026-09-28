#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-hub-smoke.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }

# install.sh installs the calendar server on every run; skip its venv step
# (and macOS bridge build) so this smoke test needs no network.
export HUB_CALENDAR_SKIP_BRIDGE=1
export HUB_CALENDAR_SKIP_VENV=1

[ ! -d "$ROOT/template" ] || fail "retired standalone template still exists"
[ -f "$ROOT/modules/core/data/AGENTS.md" ] || fail "missing Hub AGENTS.md"
[ -f "$ROOT/modules/core/data/CLAUDE.md" ] || fail "missing Hub CLAUDE.md"
[ -f "$ROOT/modules/core/data/ai/architecture.md" ] || fail "missing Hub architecture"
[ -f "$ROOT/modules/planning/skills/hub-workflows/SKILL.md" ] || fail "missing hub-workflows"
[ -f "$ROOT/modules/knowledge/skills/hub-knowledge-enable/SKILL.md" ] || fail "missing optional knowledge enable skill"
[ -f "$ROOT/modules/knowledge/skills/hub-knowledge-capture/SKILL.md" ] || fail "missing optional knowledge capture skill"
[ -f "$ROOT/modules/knowledge/skills/hub-knowledge-review/SKILL.md" ] || fail "missing optional knowledge review skill"

[ "$(wc -c < "$ROOT/modules/core/data/AGENTS.md")" -lt 6000 ] || fail "hub AGENTS.md too large"
[ "$(wc -c < "$ROOT/modules/core/data/CLAUDE.md")" -lt 6000 ] || fail "hub CLAUDE.md too large"

grep -Fq 'explicit confirmation' "$ROOT/modules/core/data/AGENTS.md" || fail "missing project confirmation gate"
grep -Fq '<hub>/projects' "$ROOT/modules/core/data/AGENTS.md" || fail "missing allowed-root gate"
grep -Fq 'cannot override Hub confirmation' "$ROOT/modules/core/data/AGENTS.md" || fail "missing Hub precedence gate"
grep -Fq 'hub-project-router' "$ROOT/modules/core/data/AGENTS.md" || fail "missing project router pointer"
grep -Fq 'read-compact-project-index.sh' "$ROOT/modules/core/skills/hub-project-router/SKILL.md" || fail "missing compact project routing"
grep -Fq 'read-compact-task-index.py' "$ROOT/modules/tasks/skills/hub-task-overview/SKILL.md" || fail "missing compact task discovery"

for resource in day-plan evening-review weekly-review; do
  [ -f "$ROOT/modules/planning/skills/hub-workflows/resources/$resource.md" ] || fail "missing workflow resource: $resource"
  grep -Fq "resources/$resource.md" "$ROOT/modules/planning/skills/hub-workflows/SKILL.md" || fail "core does not dispatch $resource"
done
grep -Fq "resources/capture.md" "$ROOT/modules/tasks/skills/hub-task-overview/SKILL.md" || fail "hub-task-overview does not dispatch capture"
[ -f "$ROOT/modules/tasks/skills/hub-task-overview/resources/capture.md" ] || fail "missing capture resource"

HUB="$TMP_DIR/_ai-hub"
bash "$ROOT/scripts/install.sh" "$HUB" >/dev/null
[ -f "$HUB/AGENTS.md" ] || fail "Hub install missing AGENTS.md"
[ -f "$HUB/ai/architecture.md" ] || fail "Hub install missing architecture"
[ -f "$HUB/scripts/read-compact-task-index.py" ] || fail "Hub install missing compact task index"
[ -d "$HUB/projects" ] || fail "Hub install missing projects root"
grep -Fqx -- "- $HUB/projects" "$HUB/ai/allowed-roots.md" || fail "installed allowed root is not exact projects root"

if bash "$ROOT/scripts/install.sh" --mode standalone "$TMP_DIR/legacy-project" >/dev/null 2>&1; then
  fail "standalone install unexpectedly succeeded"
fi
[ ! -e "$TMP_DIR/legacy-project" ] || fail "standalone rejection wrote files"

bash "$ROOT/scripts/check-consistency.sh" >/dev/null
python3 -m unittest discover -s "$ROOT/tests" -p 'test_hub_only_distribution.py' -v >/dev/null

echo "PASS: Hub-only smoke contract"
