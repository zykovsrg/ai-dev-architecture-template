#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "${1:-$(dirname "$0")/..}" && pwd)"
cd "$ROOT"
fail=0
ok() { printf 'OK [%s] — %s\n' "$1" "$2"; }
bad() { printf 'MISMATCH [%s] — %s\n' "$1" "$2" >&2; fail=1; }
missing() { printf 'MISSING [%s] — %s\n' "$1" "$2" >&2; fail=1; }
normalize_hub_entry() { sed -E -e 's/Personal AI Hub — (Codex|Claude Code)/Personal AI Hub — TOOL/g' -e 's/(Codex|Claude Code)/TOOL/g' -e 's/(AGENTS|CLAUDE)\.md/ENTRY.md/g' "$1"; }

[ ! -d template ] && [ ! -d hub-template ] && [ -d modules ] && ok "hub-only distribution" "modules/ is the only distributable architecture tree" || bad "hub-only distribution" "retired template/ or hub-template/ exists, or modules/ is missing"
if [ -f ai/architecture.md ] || [ -d ai/skills ]; then
  bad "root project rules" "generic project-local architecture copies remain"
elif [ ! -f AGENTS.md ] || [ ! -f CLAUDE.md ] || ! cmp -s AGENTS.md CLAUDE.md || ! grep -Fq 'Hub-managed entry' AGENTS.md; then
  bad "root project rules" "minimal direct-open pointers are invalid"
else
  ok "root project rules" "project memory is local; shared rules are Hub-owned"
fi

if [ -f modules/core/data/AGENTS.md ] && [ -f modules/core/data/CLAUDE.md ] && cmp -s <(normalize_hub_entry modules/core/data/AGENTS.md) <(normalize_hub_entry modules/core/data/CLAUDE.md); then
  ok "hub entry parity" "equal after tool-name normalization"
else
  bad "hub entry parity" "Hub entry semantic content differs"
fi
architecture="modules/core/data/ai/architecture.md"
[ -f "$architecture" ] || missing "hub architecture" "$architecture"

source_section="$(awk '/^## Source Of Truth \/ Канонические источники$/ {p=1; next} /^## / && p {exit} p {print}' README.md)"
if [ -z "$source_section" ]; then
  bad "source of truth" "README lacks the explicit Source Of Truth section"
else
  for needle in 'modules/' 'ai/project-registry.md' 'ai/current-task.md' 'ai/paused-tasks.md' 'ai/future-tasks.md' 'ai/project-context.md' 'ai/decisions.md' 'ai/changelog.md' 'knowledge/' 'Git'; do
    grep -Fq "$needle" <<<"$source_section" || bad "source of truth" "missing $needle"
  done
  [ "$fail" -ne 0 ] || ok "source of truth" "shared workflows, registry, project memory, knowledge, and Git authorities are explicit"
fi

hub_rule_files="modules/core/data/AGENTS.md modules/core/data/CLAUDE.md modules/core/data/ai/architecture.md $(ls modules/*/rules.md 2>/dev/null | tr '\n' ' ')"
skill_count=0
find_skill_dirs() {
  find modules/*/skills -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort
}
skill_dir_for() {
  local skill="$1"
  for base in modules/*/skills; do
    [ -d "$base/$skill" ] && { printf '%s\n' "$base/$skill"; return 0; }
  done
  return 1
}
if compgen -G "modules/*/skills" > /dev/null; then
  while IFS= read -r skill_dir; do
    skill="$(basename "$skill_dir")"; skill_count=$((skill_count + 1))
    case "$skill" in hub-*) ;; *) bad "hub skill prefix" "$skill" ;; esac
    [ -f "$skill_dir/SKILL.md" ] || missing "hub skill references" "$skill/SKILL.md"
    grep -Fq "\`$skill\`" $hub_rule_files || bad "hub skill naming" "$skill is named in no active Hub rule"
  done < <(find_skill_dirs)
  ok "hub skill inventory" "$skill_count skill directories checked"
else
  missing "hub skill inventory" "modules/*/skills"
fi
referenced_skills="$(grep -hoE '\`hub-[a-z0-9-]+\`' $hub_rule_files 2>/dev/null | tr -d '\`' | sort -u || true)"
while IFS= read -r skill; do [ -z "$skill" ] || skill_dir_for "$skill" >/dev/null || missing "hub skill references" "$skill"; done <<EOF
$referenced_skills
EOF
[ "$fail" -ne 0 ] || ok "hub skill references" "active Hub workflow references resolve"

workflow_core="modules/planning/skills/hub-workflows/SKILL.md"
if [ ! -f "$workflow_core" ]; then
  missing "hub workflows" "$workflow_core"
else
  for resource in day-plan evening-review weekly-review; do
    file="modules/planning/skills/hub-workflows/resources/$resource.md"
    [ -f "$file" ] || missing "hub workflow resources" "$resource.md"
    grep -Fq "resources/$resource.md" "$workflow_core" || bad "hub workflow resources" "core does not dispatch $resource.md"
    [ ! -f "$file" ] || grep -Fq 'core `SKILL.md`' "$file" || bad "hub workflow resources" "$resource.md does not defer to core authority"
  done
  overview_core="modules/tasks/skills/hub-task-overview/SKILL.md"
  [ -f "modules/tasks/skills/hub-task-overview/resources/capture.md" ] || missing "hub workflow resources" "hub-task-overview/resources/capture.md"
  grep -Fq "resources/capture.md" "$overview_core" 2>/dev/null || bad "hub workflow resources" "hub-task-overview does not dispatch capture.md"
  [ "$fail" -ne 0 ] || ok "hub workflow resources" "all scenario resources exist and are core-dispatched"
fi

if [ -f "$workflow_core" ]; then
  declared_actions="$(sed -n -E 's/^action: <(.*)>$/\1/p' "modules/tasks/skills/hub-task-overview/SKILL.md" 2>/dev/null)"
  referenced_learning="$(grep -rhoE '\`(goal_progress|add_observation|promote_rule|retire_rule)\`' modules/planning/skills/hub-workflows 2>/dev/null | tr -d '\`' | sort -u || true)"
  while IFS= read -r action; do
    [ -z "$action" ] && continue
    case "|$declared_actions|" in *"|$action|"*) ;; *) bad "workflow action schema" "$action is referenced but not declared" ;; esac
  done <<EOF
$referenced_learning
EOF
  grep -Fq 'Proposal display leaves it pending' "$workflow_core" || bad "learning lifecycle" "proposal display must leave friction pending"
  [ "$fail" -ne 0 ] || ok "workflow action schema" "learning actions and proposal schema agree"
fi

if grep -Fq 'scripts/read-compact-task-index.py ->' modules/*/module.md && grep -Fq 'scripts/read-compact-task-index.py' "modules/tasks/skills/hub-task-overview/SKILL.md"; then
  ok "compact task index" "shipped via module passport and used for personal-assistant discovery"
else
  bad "compact task index" "module passport or workflow routing is missing"
fi

for skill in hub-knowledge-enable hub-knowledge-capture hub-knowledge-review; do [ -f "modules/knowledge/skills/$skill/SKILL.md" ] || missing "knowledge safeguards" "$skill"; done
if grep -Eqi 'optional .*knowledge|optional `knowledge/`|knowledge.*on-demand' $hub_rule_files; then ok "knowledge safeguards" "knowledge skills remain optional"; else bad "knowledge safeguards" "knowledge is not documented as optional/on-demand"; fi

assistant="scripts/assistant-workflows.sh"
if [ ! -x "$assistant" ]; then
  missing "assistant workflow guardrails" "$assistant"
else
  source_text="$(awk '/^[[:space:]]*#/ { next } { sub(/[[:space:]]+#.*/, ""); print }' "$assistant")"
  for needle in 'rar export --minutes' '--json' 'rar status' 'Read-only workflow: no changes were made.'; do grep -Fq -- "$needle" <<<"$source_text" || bad "assistant workflow guardrails" "missing $needle"; done
  if grep -E '(^|[[:space:]])(calendar[ -]?mcp|obsidian-vault|rar[[:space:]]+(pause|resume|install))([[:space:]]|$)' <<<"$source_text" >/dev/null; then bad "assistant workflow guardrails" "forbidden executable path"; fi
  [ "$fail" -ne 0 ] || ok "assistant workflow guardrails" "read-only executable boundary retained"
fi

if python3 - "$ROOT" <<'PY'
from pathlib import Path
import re, sys
root = Path(sys.argv[1])
paths = [root / "README.md"]
for base in (root / "docs", root / "getting-started"):
    if base.exists(): paths.extend(base.rglob("*.md"))
forbidden = [
    re.compile(r"--mode\s+standalone", re.I),
    re.compile(r"standalone architecture", re.I),
    re.compile(r"update-installed-architecture\.sh", re.I),
    re.compile(r"(?<!hub-)template/"),
    re.compile(r"(?m)^\s*\$?\s*curl\b[^\n|]*\|[^\n]*\bbash\b", re.I),
]
hits=[]
for path in paths:
    rel=path.relative_to(root).as_posix()
    if rel.startswith("docs/superpowers/") or rel.startswith("docs/audits/"): continue
    text=path.read_text(encoding="utf-8")
    for pattern in forbidden:
        if pattern.search(text): hits.append(f"{rel}: {pattern.pattern}")
if hits:
    print("\n".join(hits), file=sys.stderr); raise SystemExit(1)
PY
then
  ok "active docs" "Hub-only install/update guidance has no executable pipe-to-shell path"
else
  bad "active docs" "retired or executable pipe-to-shell update guidance remains"
fi

if [ "$fail" -ne 0 ]; then exit 1; fi
printf '\nAll Hub-only consistency checks passed.\n'
