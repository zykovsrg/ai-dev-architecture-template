#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "${1:-$(dirname "$0")/..}" && pwd)"
cd "$ROOT"
fail=0
ok() { printf 'OK [%s] — %s\n' "$1" "$2"; }
bad() { printf 'MISMATCH [%s] — %s\n' "$1" "$2" >&2; fail=1; }
missing() { printf 'MISSING [%s] — %s\n' "$1" "$2" >&2; fail=1; }
normalize_hub_entry() { sed -E -e 's/Personal AI Hub — (Codex|Claude Code)/Personal AI Hub — TOOL/g' -e 's/(Codex|Claude Code)/TOOL/g' -e 's/(AGENTS|CLAUDE)\.md/ENTRY.md/g' "$1"; }

[ ! -d template ] && [ -d hub-template ] && ok "hub-only distribution" "hub-template/ is the only distributable architecture tree" || bad "hub-only distribution" "retired template/ exists or hub-template/ is missing"
if [ -f ai/architecture.md ] || [ -d ai/skills ]; then
  bad "root project rules" "generic project-local architecture copies remain"
elif [ ! -f AGENTS.md ] || [ ! -f CLAUDE.md ] || ! cmp -s AGENTS.md CLAUDE.md || ! grep -Fq 'Hub-managed entry' AGENTS.md; then
  bad "root project rules" "minimal direct-open pointers are invalid"
else
  ok "root project rules" "project memory is local; shared rules are Hub-owned"
fi

if [ -f hub-template/AGENTS.md ] && [ -f hub-template/CLAUDE.md ] && cmp -s <(normalize_hub_entry hub-template/AGENTS.md) <(normalize_hub_entry hub-template/CLAUDE.md); then
  ok "hub entry parity" "equal after tool-name normalization"
else
  bad "hub entry parity" "Hub entry semantic content differs"
fi
[ -f hub-template/ai/architecture.md ] || missing "hub architecture" "hub-template/ai/architecture.md"

hub_rule_files="hub-template/AGENTS.md hub-template/CLAUDE.md hub-template/ai/architecture.md"
skill_count=0
if [ -d hub-template/ai/skills ]; then
  while IFS= read -r skill_dir; do
    skill="$(basename "$skill_dir")"; skill_count=$((skill_count + 1))
    case "$skill" in hub-*) ;; *) bad "hub skill prefix" "$skill" ;; esac
    [ -f "$skill_dir/SKILL.md" ] || missing "hub skill references" "$skill/SKILL.md"
    grep -Fq "\`$skill\`" $hub_rule_files || bad "hub skill naming" "$skill is named in no active Hub rule"
  done < <(find hub-template/ai/skills -mindepth 1 -maxdepth 1 -type d | sort)
  ok "hub skill inventory" "$skill_count skill directories checked"
else
  missing "hub skill inventory" "hub-template/ai/skills"
fi
referenced_skills="$(grep -hoE '\`hub-[a-z0-9-]+\`' $hub_rule_files 2>/dev/null | tr -d '\`' | sort -u || true)"
while IFS= read -r skill; do [ -z "$skill" ] || [ -f "hub-template/ai/skills/$skill/SKILL.md" ] || missing "hub skill references" "$skill"; done <<EOF
$referenced_skills
EOF
[ "$fail" -ne 0 ] || ok "hub skill references" "active Hub workflow references resolve"

workflow_core="hub-template/ai/skills/hub-workflows/SKILL.md"
if [ ! -f "$workflow_core" ]; then
  missing "hub workflows" "$workflow_core"
else
  for resource in day-plan evening-review weekly-review capture; do
    file="hub-template/ai/skills/hub-workflows/resources/$resource.md"
    [ -f "$file" ] || missing "hub workflow resources" "$resource.md"
    grep -Fq "resources/$resource.md" "$workflow_core" || bad "hub workflow resources" "core does not dispatch $resource.md"
    [ ! -f "$file" ] || grep -Fq 'core `SKILL.md`' "$file" || bad "hub workflow resources" "$resource.md does not defer to core authority"
  done
  [ "$fail" -ne 0 ] || ok "hub workflow resources" "all scenario resources exist and are core-dispatched"
fi

if [ -f "$workflow_core" ]; then
  declared_actions="$(sed -n -E 's/^action: <(.*)>$/\1/p' "$workflow_core")"
  referenced_learning="$(grep -rhoE '\`(goal_progress|add_observation|promote_rule|retire_rule)\`' hub-template/ai/skills/hub-workflows 2>/dev/null | tr -d '\`' | sort -u || true)"
  while IFS= read -r action; do
    [ -z "$action" ] && continue
    case "|$declared_actions|" in *"|$action|"*) ;; *) bad "workflow action schema" "$action is referenced but not declared" ;; esac
  done <<EOF
$referenced_learning
EOF
  grep -Fq 'Proposal display leaves it pending' "$workflow_core" || bad "learning lifecycle" "proposal display must leave friction pending"
  [ "$fail" -ne 0 ] || ok "workflow action schema" "learning actions and proposal schema agree"
fi

if grep -Fq '"scripts/read-compact-task-index.py"' scripts/hub_release.py && grep -Fq 'scripts/read-compact-task-index.py' "$workflow_core"; then
  ok "compact task index" "shipped and used for personal-assistant discovery"
else
  bad "compact task index" "release manifest or workflow routing is missing"
fi

for skill in hub-knowledge-enable hub-knowledge-capture hub-knowledge-review; do [ -f "hub-template/ai/skills/$skill/SKILL.md" ] || missing "knowledge safeguards" "$skill"; done
if grep -Eqi 'optional .*knowledge|optional `knowledge/`|knowledge.*on-demand' hub-template/ai/architecture.md; then ok "knowledge safeguards" "knowledge skills remain optional"; else bad "knowledge safeguards" "knowledge is not documented as optional/on-demand"; fi

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
    re.compile(r"curl[^\n|]*\|[^\n]*\bbash\b", re.I),
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
  ok "active docs" "Hub-only install/update guidance has no pipe-to-shell path"
else
  bad "active docs" "retired or pipe-to-shell update guidance remains"
fi

if [ "$fail" -ne 0 ]; then exit 1; fi
printf '\nAll Hub-only consistency checks passed.\n'
