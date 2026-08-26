#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d /private/tmp/ai-hub-smoke.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_contains() { grep -Fq -- "$2" "$1" || fail "expected '$2' in $1"; }
assert_not_contains() { ! grep -Fq -- "$2" "$1" || fail "did not expect '$2' in $1"; }
assert_file() { [ -f "$1" ] || fail "missing file: $1"; }
assert_not_exists() { [ ! -e "$1" ] || fail "expected path to be absent: $1"; }
assert_forbidden_reads_absent() {
  local trace="$1" forbidden_path
  shift
  for forbidden_path in "$@"; do
    ! grep -Fq -- "$forbidden_path" "$trace" \
      || fail "trace entered forbidden project content: $forbidden_path"
  done
}

# The proposal-only assistant entrypoint is executable policy, not prose. Keep
# this check deliberately narrow: inspect only non-comment source lines so
# examples/documentation mentioning unsafe operations do not trigger it.
assistant_workflow_source_valid() {
  local file="$1" source
  assert_file "$file"
  source="$(awk ' /^[[:space:]]*#/ { next } { sub(/[[:space:]]+#.*/, ""); print } ' "$file")"
  grep -Fq 'rar export --minutes' <<<"$source" || fail 'assistant workflow must call rar export --minutes'
  grep -Fq -- '--json' <<<"$source" || fail 'assistant workflow must request JSON output'
  grep -Fq 'rar status' <<<"$source" || fail 'assistant workflow must call rar status'
  grep -Fq "Read-only workflow: no changes were made." <<<"$source" || fail 'assistant workflow must preserve exact no-changes line'

  # The only allowed mentions of write/apply are the argument guard itself.
  if grep -E '(^|[[:space:]])(calendar[ -]?mcp|obsidian-vault|rar[[:space:]]+(pause|resume|install))([[:space:]]|$)' \
      <<<"$source" >/dev/null; then
    fail 'assistant workflow contains a forbidden executable path'
  fi
  while IFS= read -r line; do
    [[ "$line" == *'--write|--apply)'* ]] || fail 'assistant workflow contains an executable --write/--apply path'
  done < <(grep -E '(^|[[:space:]])(--write|--apply)([[:space:]]|$)' <<<"$source" || true)
}

hub_workflows_rule_valid() {
  local found=0 rule
  for rule in "$ROOT/hub-template/AGENTS.md" "$ROOT/hub-template/CLAUDE.md" "$ROOT/hub-template/ai/architecture.md"; do
    if grep -Fq '`hub-workflows`' "$rule"; then found=1; break; fi
  done
  [ "$found" -eq 1 ] || fail 'hub rule must name literal `hub-workflows`'
}
# Registered active projects must carry the full memory scaffold; fixtures too.
scaffold_project_memory() {
  local project_path="$1" memory_file
  mkdir -p "$project_path/ai"
  for memory_file in current-task paused-tasks future-tasks project-context decisions changelog; do
    printf '# %s\n' "$memory_file" > "$project_path/ai/$memory_file.md"
  done
}
archiproject_template_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *'canonical hub-owned archiproject registry'* ]] &&
    [[ "$text" == *'not a parallel task store'* ]] &&
    [[ "$text" == *'id:'*'name:'*'status:'*'target:'*'unit:'*'due:'* ]] &&
    [[ "$text" == *'due: YYYY-MM-DD or none'* ]] &&
    [[ "$text" == *'## <archiproject-id>'*'```yaml'* ]]
}
archiproject_card_fields_valid() {
  local file="$1" primary contribution related
  primary="$(sed -n 's/^primary_archiproject: //p' "$file")"
  contribution="$(sed -n 's/^archiproject_contribution: //p' "$file")"
  related="$(sed -n 's/^related_archiprojects: //p' "$file")"

  [ "$(printf '%s\n' "$primary" | wc -l | tr -d ' ')" -eq 1 ] &&
    [ "$(printf '%s\n' "$contribution" | wc -l | tr -d ' ')" -eq 1 ] &&
    [ "$(printf '%s\n' "$related" | wc -l | tr -d ' ')" -eq 1 ] &&
    [ -n "$primary" ] && [ -n "$contribution" ] && [ -n "$related" ]
}
hub_work_model_contract_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *'Project/task files remain canonical'* ]] &&
    [[ "$text" == *'project cards are metadata only'* ]] &&
    [[ "$text" == *'link never grants a project read'* ]] &&
    [[ "$text" == *'Waiting is task/subtask-only'* ]] &&
    [[ "$text" == *'other work is actionable'* ]]
}
generate_registry() {
  local hub="$1" root="$2" count="$3" i id
  printf '%s\n' '# Project Registry' > "$hub/ai/project-registry.md"
  printf '%s\n' '# Archiprojects' > "$hub/ai/archiprojects.md"
  i=1
  while [ "$i" -le "$count" ]; do
    id="fixture-project-$i"
    mkdir -p "$root/$id"
    scaffold_project_memory "$root/$id"
    printf '\n## %s\nName: Fixture %s\nType: work\nStatus: active\nPath: %s/%s\nTags: fixture, area-%s\nCard: ai/project-cards/%s.md\n' \
      "$id" "$i" "$root" "$id" "$i" "$id" >> "$hub/ai/project-registry.md"
    printf '# Project Card\n\nProject ID: %s\nName: Fixture %s\nType: work\nStatus: active\nLast updated: 2026-08-12\nPurpose: Synthetic test project.\nTypical tasks: Exercise registry validation.\nMemory entry point: %s/%s/ai/current-task.md\n' \
      "$id" "$i" "$root" "$id" > "$hub/ai/project-cards/$id.md"
    i=$((i + 1))
  done
}
info_update_confidence_schema_valid() {
  grep -Fq 'For every item, name its source and confidence (`verified`, `stated`,' "$1" &&
    grep -Fq '`inferred`, or `uncertain`)' "$1" &&
    ! grep -Fq 'or `unknown`' "$1"
}
info_update_affected_projects_order_valid() {
  local summary affected proposal
  summary="$(grep -n '^1\. Краткое резюме встречи$' "$1" | cut -d: -f1)"
  affected="$(grep -n '^2\. Affected projects$' "$1" | cut -d: -f1)"
  proposal="$(grep -n '^3\. Предложения по проектам\.$' "$1" | cut -d: -f1)"

  [ -n "$summary" ] && [ -n "$affected" ] && [ -n "$proposal" ] &&
    [ "$summary" -lt "$affected" ] && [ "$affected" -lt "$proposal" ] &&
    sed -n "$((affected + 1)),$((proposal - 1))p" "$1" | grep -Fq '<project-id> — <exact-registered-path>'
}
info_update_current_task_source_confidence_valid() {
  awk '
    /^#### Изменения текущей задачи$/ { in_section = 1; next }
    in_section && /^#### / { exit 1 }
    in_section && /^Source: <\.\.\.> — confidence: <verified\|stated\|inferred\|uncertain>\.$/ {
      found = 1
      exit 0
    }
    END { if (!found) exit 1 }
  ' "$1"
}
section_text() {
  local file="$1"
  local start="$2"
  local end="$3"

  awk -v start="$start" -v end="$end" '
    $0 == start { in_section = 1; next }
    in_section && $0 == end { exit }
    in_section { print }
  ' "$file"
}
router_read_boundary_valid() {
  local section
  section="$(section_text "$1" '## Read allowlist and phases' '## Required response shape' | tr '\n' ' ' | tr -s ' ')"

  [[ "$section" == *'scripts/read-compact-project-index.sh'* ]] &&
    [[ "$section" == *'project_id'*'name'*'tags'*'status'*'purpose_brief'* ]] &&
    [[ "$section" == *'Do not read candidate cards, signals, project memory, knowledge, source code'* ]] &&
    [[ "$section" == *'exact registered path only'* ]]
}
router_compact_index_reads_valid() {
  local section step_one step_two step_four
  section="$(section_text "$1" '## Read allowlist and phases' '## Required response shape')"
  step_one="$(printf '%s\n' "$section" | awk '/^1\. /{in_step=1} in_step && /^2\. /{exit} in_step{print}' | tr '\n' ' ' | tr -s ' ')"
  step_two="$(printf '%s\n' "$section" | awk '/^2\. /{in_step=1} in_step && /^3\. /{exit} in_step{print}' | tr '\n' ' ' | tr -s ' ')"
  step_four="$(printf '%s\n' "$section" | awk '/^4\. /{in_step=1} in_step && /^5\. /{exit} in_step{print}' | tr '\n' ' ' | tr -s ' ')"

  [[ "$step_one" == *'read-compact-project-index.sh'* ]] &&
    [[ "$step_one" == *'project_id'*'name'*'tags'*'status'*'purpose_brief'* ]] &&
    [[ "$step_two" == *'maximum of three candidates'* ]] &&
    [[ "$step_four" == *'exact registered path only'* ]] &&
    [[ "$step_four" == *'explicit confirmation'* ]]
}
router_multiple_candidates_template_valid() {
  local section
  section="$(section_text "$1" '### Two or three candidates' '### No candidate' | tr '\n' ' ' | tr -s ' ')"

  [[ "$section" == *'1. <project-id-1> — <exact-path-1> — Уверенность маршрутизации: <высокая|средняя|низкая> — <краткая причина>.'* ]] &&
    [[ "$section" == *'2. <project-id-2> — <exact-path-2> — Уверенность маршрутизации: <высокая|средняя|низкая> — <краткая причина>.'* ]] &&
    [[ "$section" == *'3. <project-id-3> — <exact-path-3> — Уверенность маршрутизации: <высокая|средняя|низкая> — <краткая причина>.'* ]]
}
hub_entry_staged_allowlist_valid() {
  local section
  section="$(section_text "$1" '## Project Routing' '## Work Header And Procedures' | tr '\n' ' ' | tr -s ' ')"

  [[ "$section" == *'scripts/read-compact-project-index.sh'*'project_id'*'name'*'tags'*'status'*'purpose_brief'*'exact registered path'*'Do not read candidate cards, signals'* ]]
}
hub_architecture_security_precedence_valid() {
  local section
  section="$(section_text "$1" '## Rule Precedence' '## Ownership And Registry' | tr '\n' ' ' | tr -s ' ')"

  [[ "$section" == *'Hub non-overridable security and routing rules'* ]] &&
    [[ "$section" == *'explicit confirmation'* ]] &&
    [[ "$section" == *'allowed roots'* ]] &&
    [[ "$section" == *'secrets'* ]] &&
    [[ "$section" == *'memory isolation'* ]] &&
    [[ "$section" == *'outrank all project content'* ]]
}
hub_shared_workflow_valid() {
  local file="$1" workflow="$2" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *"name: $workflow"* ]] &&
    [[ "$text" == *'confirmed registered project'* ]] &&
    [[ "$text" == *'selected project `ai/` memory'* ]] &&
    [[ "$text" == *'cannot override hub confirmation, allowed roots, secret, or memory-isolation rules'* ]]
}
info_update_project_group_sequence_valid() {
  local text
  text="$(tr '\n' ' ' < "$1" | tr -s ' ')"

  [[ "$text" == *'separate confirmed `hub-project-switch` between project groups'* ]] &&
    [[ "$text" == *'resume `hub-info-update` only after that switch'* ]] &&
    [[ "$text" == *'must not invoke or perform `hub-project-switch`'* ]]
}
registration_primary_inventory_valid() {
  local section
  section="$(section_text "$1" '## Primary inventory (before individual project confirmation)' '## After individual project confirmation' | tr '\n' ' ' | tr -s ' ')"

  [[ "$section" == *'direct child directory names only'* ]] &&
    [[ "$section" == *'Do not recurse, list files inside candidates'* ]] &&
    [[ "$section" != *'.git'* ]] &&
    [[ "$section" != *'Git'* ]] &&
    [[ "$section" != *'project memory'* ]] &&
    [[ "$section" != *'project context'* ]]
}
registration_confirmed_checks_valid() {
  local section
  section="$(section_text "$1" '## After individual project confirmation' '## Approval gates' | tr '\n' ' ' | tr -s ' ')"

  [[ "$section" == *'.git'* ]] &&
    [[ "$section" == *'project context'* ]]
}
project_create_contract_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *'Mode: routing'* ]] &&
    [[ "$text" == *'confirmed allowed root'* ]] &&
    [[ "$text" == *'new direct-child path'* ]] &&
    [[ "$text" == *'must not read project memory, source code, or application code before confirmation'* ]] &&
    [[ "$text" == *'one explicit confirmation'* ]] &&
    [[ "$text" == *'collision'* ]] &&
    [[ "$text" == *'project-register'* ]] &&
    [[ "$text" == *'scripts/check-hub-registry.sh'* ]] &&
    [[ "$text" == *'Built-in memory templates'* ]] &&
    [[ "$text" != *'from `template/ai/`'* ]] &&
    [[ "$text" == *'ai/allowed-roots.md'* ]] &&
    [[ "$text" == *'ai/active-project.md'* ]] &&
    [[ "$text" == *'ai/project-registry.md'* ]] &&
    [[ "$text" == *'ai/project-cards/'* ]] &&
    [[ "$text" == *'ai/cross-project-signals.md'* ]] &&
    [[ "$text" == *'ai/archive/'* ]] &&
    [[ "$text" == *'active-project.md only after successful validation'* ]] &&
    [[ "$text" == *'hub-owned `hub-environment-check`'* ]] &&
    [[ "$text" == *'hub-owned `hub-task-intake`'* ]] &&
    [[ "$text" == *'unsafe project names'* ]] &&
    [[ "$text" == *'Initialize a local Git repository and commit only the approved scaffold'* ]] &&
    [[ "$text" == *'create a private repository with that exact name'* ]] &&
    [[ "$text" == *'report `pending-sync`'* ]] &&
    [[ "$text" == *'never attach or overwrite an existing remote'* ]] &&
    [[ "$text" == *'primary_archiproject: <archiproject-id|none>'* ]] &&
    [[ "$text" == *'archiproject_contribution: <contribution|none>'* ]] &&
    [[ "$text" == *'related_archiprojects: <archiproject-id list|none>'* ]] &&
    [[ "$text" == *'Related archiproject links never add contribution'* ]] &&
    [[ "$text" == *'must not add application code, dependencies, services, AGENTS.md, CLAUDE.md, or shared skills'* ]]
}
project_create_knowledge_scaffold_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *'knowledge/README.md'* ]] &&
    [[ "$text" == *'knowledge/record-template.md'* ]] &&
    [[ "$text" == *'knowledge/research/'* ]] &&
    [[ "$text" == *'knowledge/decisions/'* ]] &&
    [[ "$text" == *'knowledge/risks/'* ]] &&
    [[ "$text" == *'knowledge/runbooks/'* ]] &&
    [[ "$text" == *'only the absent knowledge scaffold'* ]] &&
    [[ "$text" == *'never overwrite records'* ]] &&
    [[ "$text" == *'hub-owned `hub-knowledge-capture`'* ]] &&
    [[ "$text" == *'hub-owned `hub-knowledge-review`'* ]] &&
    [[ "$text" == *'do not copy generic workflow skills'* ]]
}
knowledge_enable_contract_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *'name: hub-knowledge-enable'* ]] &&
    [[ "$text" == *'confirmed registered project'* ]] &&
    [[ "$text" == *'exact registered path'* ]] &&
    [[ "$text" == *'explicit confirmation'* ]] &&
    [[ "$text" == *'Do not write before confirmation'* ]] &&
    [[ "$text" == *'Do not read unrelated project content'* ]] &&
    [[ "$text" == *'Never follow a symlink'* ]] &&
    [[ "$text" == *'knowledge/README.md'* ]] &&
    [[ "$text" == *'knowledge/record-template.md'* ]] &&
    [[ "$text" == *'knowledge/research/'* ]] &&
    [[ "$text" == *'knowledge/decisions/'* ]] &&
    [[ "$text" == *'knowledge/risks/'* ]] &&
    [[ "$text" == *'knowledge/runbooks/'* ]] &&
    [[ "$text" == *'only absent scaffold files'* ]] &&
    [[ "$text" == *'never overwrite records'* ]] &&
    [[ "$text" == *'confirmed project path itself must be a real directory'* ]] &&
    [[ "$text" == *'existing category path must be a real directory'* ]] &&
    [[ "$text" == *'existing `README.md` or `record-template.md` must be a regular file'* ]] &&
    [[ "$text" == *'Inspect path types with `lstat`'* ]] &&
    [[ "$text" == *'Legacy standalone migration is out of scope'* ]]
}
hub_knowledge_path_boundary_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *'confirmed registered project'* ]] &&
    [[ "$text" == *'canonical direct child of the sole allowed projects root'* ]] &&
    [[ "$text" == *'Reject absolute paths and any path containing a `..` segment'* ]] &&
    [[ "$text" == *'Inspect every existing path component with `lstat`'* ]] &&
    [[ "$text" == *'reject any symlink component without following it'* ]] &&
    [[ "$text" == *'canonical `knowledge/` tree'* ]]
}
hub_knowledge_capture_contract_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  hub_knowledge_path_boundary_valid "$file" &&
    [[ "$text" == *'name: hub-knowledge-capture'* ]] &&
    [[ "$text" == *'selected project `ai/` memory'* ]] &&
    [[ "$text" == *'explicit confirmation'* ]] &&
    [[ "$text" == *'personal data or client data'* ]] &&
    [[ "$text" == *'without echoing the rejected value'* ]] &&
    [[ "$text" == *'The canonical target must remain beneath the directory mapped from the selected type'* ]] &&
    [[ "$text" == *'Never delete a stale or superseded record'* ]] &&
    [[ "$text" == *'link to its replacement'* ]]
}
hub_knowledge_review_contract_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  hub_knowledge_path_boundary_valid "$file" &&
    [[ "$text" == *'name: hub-knowledge-review'* ]] &&
    [[ "$text" == *'selected project `ai/` memory'* ]] &&
    [[ "$text" == *'explicit confirmation'* ]] &&
    [[ "$text" == *'required frontmatter keys: `type`, `status`, `created`, `reviewed`, and `sources`'* ]] &&
    [[ "$text" == *'exactly `research`, `decision`, `risk`, or `runbook`'* ]] &&
    [[ "$text" == *'type must match its category directory'* ]] &&
    [[ "$text" == *'exactly `draft`, `verified`, `needs-review`, `stale`, or `superseded`'* ]] &&
    [[ "$text" == *'Validate `created` and `reviewed` as real `YYYY-MM-DD` dates'* ]] &&
    [[ "$text" == *'publication or update date of each cited source separately'* ]] &&
    [[ "$text" == *'personal data or client data'* ]] &&
    [[ "$text" == *'without echoing the rejected value'* ]] &&
    [[ "$text" == *'Never delete a stale or superseded record'* ]] &&
    [[ "$text" == *'link to its replacement'* ]]
}
hub_task_finish_knowledge_offer_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *'After the normal completion check'* ]] &&
    [[ "$text" == *'may offer the hub-owned `hub-knowledge-review`'* ]] &&
    [[ "$text" == *'never start it automatically'* ]] &&
    [[ "$text" == *'Declining the offer has no effect on task closure'* ]]
}
project_migrate_contract_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *'separately confirmed temporary migration source'* ]] &&
    [[ "$text" == *'never write'*'ai/allowed-roots.md'* ]] &&
    [[ "$text" == *'expires when this workflow ends'* ]] &&
    [[ "$text" == *'Reject `/`, the canonical home directory, the hub directory, and `<canonical-hub>/projects`'* ]] &&
    [[ "$text" == *'direct-child directory names only'* ]] &&
    [[ "$text" == *'exclude the target `_ai-hub`'* ]] &&
    [[ "$text" == *'Do not recurse or read candidate content'* ]] &&
    [[ "$text" == *'preflight confirmation'* ]] &&
    [[ "$text" == *'source-to-destination mapping'* ]] &&
    [[ "$text" == *'Git metadata'* ]] &&
    [[ "$text" == *'collision'* ]] &&
    [[ "$text" == *'explicit move confirmation'* ]] &&
    [[ "$text" == *'Move, never copy'* ]] &&
    [[ "$text" == *'preserve the existing `.git/` directory'* ]] &&
    [[ "$text" == *'Stop on the first failure'* ]] &&
    [[ "$text" == *'do not continue automatically'* ]] &&
    [[ "$text" == *'separate card and registry confirmation'* ]] &&
    [[ "$text" == *'scripts/check-hub-registry.sh'* ]] &&
    [[ "$text" == *'Never move backups, archives, symlinks, unknown folders, or unsafe candidates'* ]]
}
legacy_cleanup_contract_valid() {
  local file="$1" section candidates protected_paths expected lower
  section="$(cleanup_section_text "$file")"
  candidates="$(printf '%s\n' "$section" | awk '
    /^Candidate allowlist:$/ { collect = 1; next }
    collect && /^Preserve / { exit }
    collect && /^- `/ { print }
  ')"
  expected=$'- `AGENTS.md`\n- `CLAUDE.md`\n- `ai/architecture.md`\n- `ai/external-tools.md`'
  protected_paths="$(printf '%s\n' "$section" | awk '
    /^Preserve these project-memory paths unchanged:$/ { collect = 1; next }
    collect && /^Do not delete / { exit }
    collect && /^- `/ { print }
  ')"
  lower="$(printf '%s' "$section" | tr '[:upper:]' '[:lower:]')"

  [[ -n "$section" ]] &&
    [[ "$candidates" == "$expected" ]] &&
    [[ "$protected_paths" == $'- `ai/current-task.md`\n- `ai/paused-tasks.md`\n- `ai/future-tasks.md`\n- `ai/project-context.md`\n- `ai/decisions.md`\n- `ai/changelog.md`' ]] &&
    [[ "$section" == *'Cleanup confirmation is separate from move, preflight, and registration confirmation.'* ]] &&
    [[ "$section" == *'A previous move, preflight, or registration confirmation never authorizes cleanup.'* ]] &&
    [[ "$section" == *'Preserve `ai/skills/`, `.claude/`, and `.codex/` unchanged.'* ]] &&
    [[ "$section" == *'- `ai/current-task.md`'* ]] &&
    [[ "$section" == *'- `ai/paused-tasks.md`'* ]] &&
    [[ "$section" == *'- `ai/future-tasks.md`'* ]] &&
    [[ "$section" == *'- `ai/project-context.md`'* ]] &&
    [[ "$section" == *'- `ai/decisions.md`'* ]] &&
    [[ "$section" == *'- `ai/changelog.md`'* ]] &&
    [[ "$section" == *'Do not delete `ai/` as a directory.'* ]] &&
    [[ "$section" == *'revalidate the canonical direct-child project location'* ]] &&
    [[ "$section" == *'current registry validation result'* ]] &&
    [[ "$section" == *'unchanged allowlisted candidate list'* ]] &&
    [[ "$section" == *'absence of symlinks'* ]] &&
    [[ "$section" == *'Do not archive, back up, copy, replace, or follow symlinks.'* ]] &&
    [[ "$lower" != *'automatic cleanup'* ]] &&
    [[ "$lower" != *'cleanup may proceed without explicit confirmation'* ]] &&
    [[ "$lower" != *'delete the entire project'* ]] &&
    [[ "$lower" != *'recursively delete'* ]] &&
    [[ "$lower" != *'rm -rf'* ]] &&
    [[ "$lower" != *'package.json'* ]]
}
cleanup_section_text() {
  awk '
    /^## Optional legacy standalone cleanup$/ { collect = 1; next }
    collect && /^## / { exit }
    collect { print }
  ' "$1"
}
legacy_cleanup_mutations_rejected() {
  local file="$1" fixture phrase

  fixture="$TMP_DIR/migrate-extra-cleanup-candidate.md"
  awk '{ print; if ($0 == "- `ai/external-tools.md`") print "- `package.json`" }' "$file" > "$fixture"
  assert_rejected legacy_cleanup_contract_valid "$fixture"

  fixture="$TMP_DIR/migrate-cleanup-directory-candidate.md"
  awk '{ print; if ($0 == "- `ai/external-tools.md`") print "- `ai/`" }' "$file" > "$fixture"
  assert_rejected legacy_cleanup_contract_valid "$fixture"

  fixture="$TMP_DIR/migrate-extra-cleanup-instruction.md"
  awk '{ print; if ($0 == "Do not delete `ai/` as a directory. Do not delete `ai/skills/`, `.claude/`,") print "Remove package.json after cleanup." }' "$file" > "$fixture"
  assert_rejected legacy_cleanup_contract_valid "$fixture"

  fixture="$TMP_DIR/migrate-cleanup-without-confirmation.md"
  awk '{ print; if ($0 == "Cleanup confirmation is separate from move, preflight, and registration confirmation.") print "Cleanup may proceed without explicit confirmation." }' "$file" > "$fixture"
  assert_rejected legacy_cleanup_contract_valid "$fixture"

  for phrase in \
    'revalidate the canonical direct-child project location' \
    'current registry validation result' \
    'unchanged allowlisted candidate list' \
    'absence of symlinks'; do
    fixture="$TMP_DIR/migrate-missing-${phrase// /-}.md"
    sed "s|$phrase|omitted validation|" "$file" > "$fixture"
    assert_rejected legacy_cleanup_contract_valid "$fixture"
  done
}
legacy_cleanup_order_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *'project-migrate'*'project-register'*'scripts/check-hub-registry.sh'*'optional legacy cleanup'* ]]
}
assert_rejected() {
  if "$@"; then
    fail "boundary validator accepted an intentionally unsafe fixture"
  fi
}
normalize_entry() {
  sed \
    -e '1{/^# Personal AI Hub — Codex$/d;}' \
    -e '1{/^# Personal AI Hub — Claude Code$/d;}' \
    -e '/^<!-- Tool-specific activation: Codex reads AGENTS\.md as its project entry file\. -->$/d' \
    -e '/^<!-- Tool-specific activation: Claude Code reads CLAUDE\.md as its project entry file\. -->$/d' \
    "$1"
}

portable_hub_install_contract() {
  local portable_hub="$TMP_DIR/portable-install/_ai-hub"
  local install_out="$TMP_DIR/portable-install.out"
  local status_out="$TMP_DIR/portable-install-status.out"
  local custom_root="$TMP_DIR/custom-root"
  local wrong_name="$TMP_DIR/not-a-hub"
  local non_hub_target="$TMP_DIR/non-hub-target/_ai-hub"
  local marker_target="$TMP_DIR/marker-target/_ai-hub"
  local symlink_parent="$TMP_DIR/symlink-parent"
  local symlink_destination="$TMP_DIR/symlink-destination"

  if ! bash "$ROOT/scripts/install.sh" --mode hub "$portable_hub" > "$install_out" 2>&1; then
    fail 'portable hub install without --root was rejected'
  fi
  assert_file "$portable_hub/projects/.gitkeep"
  assert_file "$portable_hub/scripts/read-compact-project-index.sh"
  assert_contains "$portable_hub/.gitignore" '/projects/'
  portable_projects_root="$(cd "$portable_hub/projects" && pwd -P)"
  [ "$(grep -Fxc -- "- $portable_projects_root" "$portable_hub/ai/allowed-roots.md")" -eq 1 ] \
    || fail 'portable hub must record exactly its derived projects root'
  [ "$(grep -Ec '^- ' "$portable_hub/ai/allowed-roots.md")" -eq 1 ] \
    || fail 'portable hub must record no additional permanent roots'

  mkdir -p "$portable_hub/projects/fixture/.git"
  printf '%s\n' 'fixture repository metadata' > "$portable_hub/projects/fixture/.git/HEAD"
  git -C "$portable_hub" status --short > "$status_out"
  assert_not_contains "$status_out" 'projects/fixture'

  mkdir -p "$custom_root"
  if bash "$ROOT/scripts/install.sh" --mode hub --root "$custom_root" \
    "$TMP_DIR/rejected-root/_ai-hub" > "$TMP_DIR/rejected-root.out" 2>&1; then
    fail 'portable hub installer accepted a custom --root'
  fi

  if bash "$ROOT/scripts/install.sh" --mode hub "$wrong_name" > "$TMP_DIR/wrong-name.out" 2>&1; then
    fail 'portable hub installer accepted a target with the wrong basename'
  fi

  mkdir -p "$non_hub_target"
  printf '%s\n' 'do not overwrite' > "$non_hub_target/existing.txt"
  if bash "$ROOT/scripts/install.sh" --mode hub "$non_hub_target" > "$TMP_DIR/non-hub.out" 2>&1; then
    fail 'portable hub installer accepted a non-hub nonempty target'
  fi

  mkdir -p "$marker_target/ai"
  printf '%s\n' 'foreign instructions' > "$marker_target/AGENTS.md"
  printf '%s\n' 'foreign architecture' > "$marker_target/ai/architecture.md"
  printf '%s\n' 'foreign roots' > "$marker_target/ai/allowed-roots.md"
  printf '%s\n' 'foreign registry' > "$marker_target/ai/project-registry.md"
  if bash "$ROOT/scripts/install.sh" --mode hub "$marker_target" > "$TMP_DIR/marker-target.out" 2>&1; then
    fail 'portable hub installer accepted a non-hub target with architecture-like files'
  fi
  assert_contains "$marker_target/AGENTS.md" 'foreign instructions'
  assert_contains "$marker_target/ai/architecture.md" 'foreign architecture'
  assert_not_exists "$marker_target/.git"

  mkdir -p "$symlink_destination"
  ln -s "$symlink_destination" "$symlink_parent"
  if bash "$ROOT/scripts/install.sh" --mode hub "$symlink_parent/_ai-hub" > "$TMP_DIR/symlink-parent.out" 2>&1; then
    fail 'portable hub installer accepted a destination path through a symlink'
  fi
  assert_not_exists "$symlink_destination/_ai-hub"
}

HUB_AGENTS="$ROOT/hub-template/AGENTS.md"
HUB_CLAUDE="$ROOT/hub-template/CLAUDE.md"
assert_file "$HUB_AGENTS"
assert_file "$HUB_CLAUDE"
[ "$(wc -l < "$HUB_AGENTS")" -le 120 ] || fail 'hub AGENTS.md too long'
[ "$(wc -c < "$HUB_AGENTS")" -le 6000 ] || fail 'hub AGENTS.md too large'
[ "$(wc -l < "$HUB_CLAUDE")" -le 120 ] || fail 'hub CLAUDE.md too long'
[ "$(wc -c < "$HUB_CLAUDE")" -le 6000 ] || fail 'hub CLAUDE.md too large'
grep -Fq 'explicit confirmation' "$HUB_AGENTS" || fail 'missing confirmation gate'
grep -Fq 'sole allowed root' "$HUB_AGENTS" || fail 'missing allowed-root gate'
grep -Fq 'explicit confirmation' "$HUB_CLAUDE" || fail 'missing confirmation gate'
grep -Fq 'sole allowed root' "$HUB_CLAUDE" || fail 'missing allowed-root gate'
hub_entry_staged_allowlist_valid "$HUB_AGENTS" \
  || fail 'hub entry must allow only compact-index routing before confirmation'
assert_contains "$HUB_AGENTS" 'ai/architecture.md'
assert_not_contains "$HUB_AGENTS" 'hub-template/ai/architecture.md'

ARCHIPROJECTS_TEMPLATE="$ROOT/hub-template/ai/archiprojects.md"
assert_file "$ARCHIPROJECTS_TEMPLATE"
archiproject_template_valid "$ARCHIPROJECTS_TEMPLATE" \
  || fail 'archiproject template must define the canonical YAML registry schema'

for work_model_file in \
  "$HUB_AGENTS" \
  "$HUB_CLAUDE" \
  "$ROOT/hub-template/ai/architecture.md" \
  "$ROOT/hub-template/ai/skills/hub-project-router/SKILL.md" \
  "$ROOT/hub-template/ai/skills/hub-registry-check/SKILL.md" \
  "$ROOT/docs/file-roles.md"; do
  hub_work_model_contract_valid "$work_model_file" \
    || fail "hub work-model contract missing: $work_model_file"
done

WORK_MODEL_HUB="$TMP_DIR/work-model-hub"
mkdir -p "$WORK_MODEL_HUB/ai/project-cards" "$WORK_MODEL_HUB/projects/primary-project" \
  "$WORK_MODEL_HUB/projects/none-project" "$WORK_MODEL_HUB/projects/legacy-project"
for work_model_project in primary-project none-project legacy-project; do
  scaffold_project_memory "$WORK_MODEL_HUB/projects/$work_model_project"
done
printf '%s\n' '# Allowed Roots' '' "- $WORK_MODEL_HUB/projects" > "$WORK_MODEL_HUB/ai/allowed-roots.md"
printf '%s\n' '# Project Registry' '' \
  '## primary-project' \
  'Name: Primary contribution' \
  'Type: work' \
  'Status: active' \
  "Path: $WORK_MODEL_HUB/projects/primary-project" \
  'Tags: fixture' \
  'Card: ai/project-cards/primary-project.md' '' \
  '## none-project' \
  'Name: No archiproject' \
  'Type: work' \
  'Status: active' \
  "Path: $WORK_MODEL_HUB/projects/none-project" \
  'Tags: fixture' \
  'Card: ai/project-cards/none-project.md' '' \
  '## legacy-project' \
  'Name: Legacy card' \
  'Type: work' \
  'Status: active' \
  "Path: $WORK_MODEL_HUB/projects/legacy-project" \
  'Tags: fixture' \
  'Card: ai/project-cards/legacy-project.md' > "$WORK_MODEL_HUB/ai/project-registry.md"
printf '%s\n' '# Project Card' '' \
  'Project ID: primary-project' 'Name: Primary contribution' 'Type: work' 'Status: active' \
  'Last updated: 2026-08-24' 'Purpose: Smoke fixture.' 'Typical tasks: Exercise compatibility.' \
  "Memory entry point: $WORK_MODEL_HUB/projects/primary-project/ai/current-task.md" \
  'primary_archiproject: unified-assistant' 'archiproject_contribution: 25' \
  'related_archiprojects: none' > "$WORK_MODEL_HUB/ai/project-cards/primary-project.md"
printf '%s\n' '# Project Card' '' \
  'Project ID: none-project' 'Name: No archiproject' 'Type: work' 'Status: active' \
  'Last updated: 2026-08-24' 'Purpose: Smoke fixture.' 'Typical tasks: Exercise compatibility.' \
  "Memory entry point: $WORK_MODEL_HUB/projects/none-project/ai/current-task.md" \
  'primary_archiproject: none' 'archiproject_contribution: none' \
  'related_archiprojects: none' > "$WORK_MODEL_HUB/ai/project-cards/none-project.md"
printf '%s\n' '# Project Card' '' \
  'Project ID: legacy-project' 'Name: Legacy card' 'Type: work' 'Status: active' \
  'Last updated: 2026-08-24' 'Purpose: Smoke fixture.' 'Typical tasks: Exercise compatibility.' \
  "Memory entry point: $WORK_MODEL_HUB/projects/legacy-project/ai/current-task.md" \
  > "$WORK_MODEL_HUB/ai/project-cards/legacy-project.md"
cp "$ARCHIPROJECTS_TEMPLATE" "$WORK_MODEL_HUB/ai/archiprojects.md"
printf '%s\n' '' \
  '## unified-assistant' \
  '```yaml' \
  'id: unified-assistant' \
  'name: Unified assistant' \
  'status: active' \
  'target: 100' \
  'unit: percent' \
  'due: none' \
  '```' >> "$WORK_MODEL_HUB/ai/archiprojects.md"
archiproject_card_fields_valid "$WORK_MODEL_HUB/ai/project-cards/primary-project.md" \
  || fail 'primary archiproject fixture fields are invalid'
archiproject_card_fields_valid "$WORK_MODEL_HUB/ai/project-cards/none-project.md" \
  || fail 'none archiproject fixture fields are invalid'
assert_not_contains "$WORK_MODEL_HUB/ai/project-cards/legacy-project.md" 'primary_archiproject:'
bash "$ROOT/scripts/check-hub-registry.sh" "$WORK_MODEL_HUB" > "$TMP_DIR/work-model-registry.out"
assert_contains "$TMP_DIR/work-model-registry.out" 'Registry check passed: 3 projects'

copy_work_model_hub() {
  local destination="$1"
  cp -R "$WORK_MODEL_HUB" "$destination"
  perl -pi -e "s#\\Q$WORK_MODEL_HUB\\E#$destination#g" \
    "$destination/ai/allowed-roots.md" \
    "$destination/ai/project-registry.md" \
    "$destination/ai/project-cards/primary-project.md" \
    "$destination/ai/project-cards/none-project.md" \
    "$destination/ai/project-cards/legacy-project.md"
}

# Task 2 reuses one mutable fixture and resets it cheaply between cases.
reset_work_model_hub() {
  local destination="$1"
  rsync -a --delete "$WORK_MODEL_BASE"/ "$destination"/
  perl -pi -e "s#\\Q$WORK_MODEL_BASE\\E#$destination#g" \
    "$destination/ai/allowed-roots.md" \
    "$destination/ai/project-registry.md" \
    "$destination/ai/project-cards/primary-project.md" \
    "$destination/ai/project-cards/none-project.md" \
    "$destination/ai/project-cards/legacy-project.md"
}

WORK_MODEL_BASE="$TMP_DIR/work-model-base"
copy_work_model_hub "$WORK_MODEL_BASE"

# New archiproject metadata must be all-or-nothing and link only to well-formed,
# known registry entries. Legacy cards intentionally remain valid.
TASK2_ARCHIPROJECT="$TMP_DIR/task2-archiproject"
reset_work_model_hub "$TASK2_ARCHIPROJECT"

for partial_field in primary_archiproject archiproject_contribution related_archiprojects; do
  reset_work_model_hub "$TASK2_ARCHIPROJECT"
  sed "/^$partial_field:/d" "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md" \
    > "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp"
  mv "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp" \
    "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md"
  if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/partial-archiproject.out" 2>&1; then
    fail "validator accepted partially supplied archiproject fields without $partial_field"
  fi
  assert_contains "$TMP_DIR/partial-archiproject.out" 'archiproject fields must be supplied together'
done

reset_work_model_hub "$TASK2_ARCHIPROJECT"
sed 's/^primary_archiproject: unified-assistant$/primary_archiproject: unknown-archiproject/' \
  "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md" > "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp"
mv "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp" "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/unknown-primary.out" 2>&1; then
  fail 'validator accepted an unknown primary archiproject'
fi
assert_contains "$TMP_DIR/unknown-primary.out" 'unknown primary archiproject'

reset_work_model_hub "$TASK2_ARCHIPROJECT"
sed 's/^archiproject_contribution: 25$/archiproject_contribution: 0/' \
  "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md" > "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp"
mv "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp" "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md"
bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/zero-contribution.out"
assert_contains "$TMP_DIR/zero-contribution.out" 'Registry check passed: 3 projects'

for invalid_contribution in -1 not-a-number; do
  reset_work_model_hub "$TASK2_ARCHIPROJECT"
  sed "s/^archiproject_contribution: 25$/archiproject_contribution: $invalid_contribution/" \
    "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md" > "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp"
  mv "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp" "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md"
  if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/invalid-contribution.out" 2>&1; then
    fail "validator accepted invalid archiproject contribution: $invalid_contribution"
  fi
  assert_contains "$TMP_DIR/invalid-contribution.out" 'archiproject contribution must be a nonnegative number'
done

DUPLICATE_RELATED="$TMP_DIR/duplicate-related-archiprojects"
reset_work_model_hub "$TASK2_ARCHIPROJECT"
sed 's/^related_archiprojects: none$/related_archiprojects: related-work, related-work/' \
  "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md" > "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp"
mv "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp" "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/duplicate-related.out" 2>&1; then
  fail 'validator accepted duplicate related archiproject IDs'
fi
assert_contains "$TMP_DIR/duplicate-related.out" 'duplicate related archiproject'

RELATED_PRIMARY="$TMP_DIR/related-primary-archiproject"
reset_work_model_hub "$TASK2_ARCHIPROJECT"
sed 's/^related_archiprojects: none$/related_archiprojects: unified-assistant/' \
  "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md" > "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp"
mv "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp" "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/related-primary.out" 2>&1; then
  fail 'validator accepted a related archiproject equal to the primary ID'
fi
assert_contains "$TMP_DIR/related-primary.out" 'related archiproject must not equal primary archiproject'

UNKNOWN_RELATED="$TMP_DIR/unknown-related-archiproject"
reset_work_model_hub "$TASK2_ARCHIPROJECT"
sed 's/^related_archiprojects: none$/related_archiprojects: unknown-archiproject/' \
  "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md" > "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp"
mv "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp" "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/unknown-related.out" 2>&1; then
  fail 'validator accepted an unknown related archiproject'
fi
assert_contains "$TMP_DIR/unknown-related.out" 'unknown related archiproject'

for malformed_field in primary_archiproject archiproject_contribution related_archiprojects; do
  reset_work_model_hub "$TASK2_ARCHIPROJECT"
  sed "s/^$malformed_field: .*/$malformed_field:/" \
    "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md" \
    > "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp"
  mv "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp" \
    "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md"
  if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/malformed-archiproject-field.out" 2>&1; then
    fail "validator accepted an empty archiproject field: $malformed_field"
  fi
  assert_contains "$TMP_DIR/malformed-archiproject-field.out" 'archiproject fields must be non-empty'

  reset_work_model_hub "$TASK2_ARCHIPROJECT"
  sed "s/^$malformed_field: /$malformed_field:/" \
    "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md" \
    > "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp"
  mv "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md.tmp" \
    "$TASK2_ARCHIPROJECT/ai/project-cards/primary-project.md"
  if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/malformed-archiproject-field.out" 2>&1; then
    fail "validator accepted a no-space archiproject field: $malformed_field"
  fi
  assert_contains "$TMP_DIR/malformed-archiproject-field.out" 'archiproject fields must be non-empty'
done

reset_work_model_hub "$TASK2_ARCHIPROJECT"
sed 's/^id: unified-assistant$/id: different-id/' "$TASK2_ARCHIPROJECT/ai/archiprojects.md" \
  > "$TASK2_ARCHIPROJECT/ai/archiprojects.md.tmp"
mv "$TASK2_ARCHIPROJECT/ai/archiprojects.md.tmp" "$TASK2_ARCHIPROJECT/ai/archiprojects.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/malformed-archiproject-registry.out" 2>&1; then
  fail 'validator accepted a malformed archiproject registry entry'
fi
assert_contains "$TMP_DIR/malformed-archiproject-registry.out" 'archiproject registry entry ID mismatch'

for malformed_archiproject in \
  'status: unknown' \
  'name: ' \
  'heading: invalid_id' \
  'target: not-a-number' \
  'unit: ' \
  'due: 2026-02-30' \
  'due: 2026/08/24'; do
  reset_work_model_hub "$TASK2_ARCHIPROJECT"
  field="${malformed_archiproject%%:*}"
  value="${malformed_archiproject#*: }"
  case "$field" in
    heading)
      sed -e 's/^## unified-assistant$/## invalid_id/' -e 's/^id: unified-assistant$/id: invalid_id/' \
        "$TASK2_ARCHIPROJECT/ai/archiprojects.md" \
        > "$TASK2_ARCHIPROJECT/ai/archiprojects.md.tmp"
      ;;
    *)
      sed "s|^$field: .*|$field: $value|" "$TASK2_ARCHIPROJECT/ai/archiprojects.md" \
        > "$TASK2_ARCHIPROJECT/ai/archiprojects.md.tmp"
      ;;
  esac
  mv "$TASK2_ARCHIPROJECT/ai/archiprojects.md.tmp" "$TASK2_ARCHIPROJECT/ai/archiprojects.md"
  if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/malformed-archiproject-value.out" 2>&1; then
    fail "validator accepted malformed archiproject $malformed_archiproject"
  fi
  assert_contains "$TMP_DIR/malformed-archiproject-value.out" 'invalid archiproject'
done

reset_work_model_hub "$TASK2_ARCHIPROJECT"
awk '
  /^due: / { print; print "unexpected: must-fail"; next }
  { print }
' "$TASK2_ARCHIPROJECT/ai/archiprojects.md" \
  > "$TASK2_ARCHIPROJECT/ai/archiprojects.md.tmp"
mv "$TASK2_ARCHIPROJECT/ai/archiprojects.md.tmp" "$TASK2_ARCHIPROJECT/ai/archiprojects.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$TASK2_ARCHIPROJECT" > "$TMP_DIR/unknown-archiproject-key.out" 2>&1; then
  fail 'validator accepted an unknown YAML key in archiproject registry'
fi
assert_contains "$TMP_DIR/unknown-archiproject-key.out" 'unrecognized YAML line'

bash "$ROOT/scripts/check-consistency.sh" > "$TMP_DIR/work-model-consistency.out"
assert_contains "$TMP_DIR/work-model-consistency.out" 'All canonical lists are consistent.'

portable_hub_install_contract

THIRD_ACTIVATION="$TMP_DIR/entry-with-third-activation.md"
cp "$HUB_AGENTS" "$THIRD_ACTIVATION"
printf '%s\n' '<!-- Tool-specific activation: A third tool reads this entry differently. -->' >> "$THIRD_ACTIVATION"
assert_contains <(normalize_entry "$THIRD_ACTIVATION") \
  '<!-- Tool-specific activation: A third tool reads this entry differently. -->'

cmp -s <(normalize_entry "$HUB_AGENTS") <(normalize_entry "$HUB_CLAUDE") \
  || fail 'hub entry files differ beyond title and activation paragraph'

for skill in hub-project-router hub-project-switch hub-project-register hub-project-create hub-project-migrate hub-registry-check hub-environment-check hub-task-intake hub-task-switch hub-task-finish hub-knowledge-enable hub-knowledge-capture hub-knowledge-review; do
  file="$ROOT/hub-template/ai/skills/$skill/SKILL.md"
  assert_file "$file"
  assert_contains "$file" 'name:'
  assert_contains "$file" 'description:'
  assert_contains "$file" 'explicit confirmation'
done

PROJECT_CREATE_SKILL="$ROOT/hub-template/ai/skills/hub-project-create/SKILL.md"
project_create_contract_valid "$PROJECT_CREATE_SKILL" \
  || fail 'project-create must define the confirmation-gated creation contract'
project_create_knowledge_scaffold_valid "$PROJECT_CREATE_SKILL" \
  || fail 'project-create must preview and create the four knowledge directories safely'
assert_contains "$PROJECT_CREATE_SKILL" '<canonical-hub>/projects'

PROJECT_CREATE_WITHOUT_UNSAFE_NAMES="$TMP_DIR/project-create-without-unsafe-name-guard.md"
sed '/unsafe project names/d' "$PROJECT_CREATE_SKILL" > "$PROJECT_CREATE_WITHOUT_UNSAFE_NAMES"
assert_rejected project_create_contract_valid "$PROJECT_CREATE_WITHOUT_UNSAFE_NAMES"

PROJECT_CREATE_WITHOUT_GIT_GUARANTEE="$TMP_DIR/project-create-without-git-guarantee.md"
sed '/never attach or overwrite an existing remote/d' "$PROJECT_CREATE_SKILL" \
  > "$PROJECT_CREATE_WITHOUT_GIT_GUARANTEE"
assert_rejected project_create_contract_valid "$PROJECT_CREATE_WITHOUT_GIT_GUARANTEE"

PROJECT_CREATE_WITHOUT_KNOWLEDGE_DIRECTORY="$TMP_DIR/project-create-without-knowledge-directory.md"
sed '/knowledge\/runbooks\//d' "$PROJECT_CREATE_SKILL" > "$PROJECT_CREATE_WITHOUT_KNOWLEDGE_DIRECTORY"
assert_rejected project_create_knowledge_scaffold_valid "$PROJECT_CREATE_WITHOUT_KNOWLEDGE_DIRECTORY"

KNOWLEDGE_ENABLE_SKILL="$ROOT/hub-template/ai/skills/hub-knowledge-enable/SKILL.md"
knowledge_enable_contract_valid "$KNOWLEDGE_ENABLE_SKILL" \
  || fail 'missing knowledge-enable workflow safety contract'

KNOWLEDGE_ENABLE_WITHOUT_NO_WRITES="$TMP_DIR/knowledge-enable-without-preconfirmation-write-gate.md"
sed '/Do not write before confirmation/d' "$KNOWLEDGE_ENABLE_SKILL" \
  > "$KNOWLEDGE_ENABLE_WITHOUT_NO_WRITES"
assert_rejected knowledge_enable_contract_valid "$KNOWLEDGE_ENABLE_WITHOUT_NO_WRITES"

KNOWLEDGE_ENABLE_WITHOUT_SYMLINK_GUARD="$TMP_DIR/knowledge-enable-without-symlink-guard.md"
sed '/Never follow a symlink/d' "$KNOWLEDGE_ENABLE_SKILL" \
  > "$KNOWLEDGE_ENABLE_WITHOUT_SYMLINK_GUARD"
assert_rejected knowledge_enable_contract_valid "$KNOWLEDGE_ENABLE_WITHOUT_SYMLINK_GUARD"

KNOWLEDGE_ENABLE_WITHOUT_PATH_TYPES="$TMP_DIR/knowledge-enable-without-path-types.md"
sed '/Inspect path types with `lstat`/d' "$KNOWLEDGE_ENABLE_SKILL" \
  > "$KNOWLEDGE_ENABLE_WITHOUT_PATH_TYPES"
assert_rejected knowledge_enable_contract_valid "$KNOWLEDGE_ENABLE_WITHOUT_PATH_TYPES"

HUB_KNOWLEDGE_CAPTURE="$ROOT/hub-template/ai/skills/hub-knowledge-capture/SKILL.md"
HUB_KNOWLEDGE_REVIEW="$ROOT/hub-template/ai/skills/hub-knowledge-review/SKILL.md"
hub_knowledge_capture_contract_valid "$HUB_KNOWLEDGE_CAPTURE" \
  || fail 'hub-owned knowledge-capture contract is incomplete'
hub_knowledge_review_contract_valid "$HUB_KNOWLEDGE_REVIEW" \
  || fail 'hub-owned knowledge-review contract is incomplete'

HUB_CAPTURE_WITHOUT_TRAVERSAL="$TMP_DIR/hub-capture-without-traversal.md"
sed '/Reject absolute paths and any path containing a `\.\.` segment/d' \
  "$HUB_KNOWLEDGE_CAPTURE" > "$HUB_CAPTURE_WITHOUT_TRAVERSAL"
assert_rejected hub_knowledge_capture_contract_valid "$HUB_CAPTURE_WITHOUT_TRAVERSAL"

HUB_REVIEW_WITHOUT_SYMLINK="$TMP_DIR/hub-review-without-symlink.md"
sed '/reject any symlink component without following it/d' \
  "$HUB_KNOWLEDGE_REVIEW" > "$HUB_REVIEW_WITHOUT_SYMLINK"
assert_rejected hub_knowledge_review_contract_valid "$HUB_REVIEW_WITHOUT_SYMLINK"

hub_task_finish_knowledge_offer_valid "$ROOT/hub-template/ai/skills/hub-task-finish/SKILL.md" \
  || fail 'hub task-finish must offer but never start knowledge-review'

PROJECT_MIGRATE_SKILL="$ROOT/hub-template/ai/skills/hub-project-migrate/SKILL.md"
project_migrate_contract_valid "$PROJECT_MIGRATE_SKILL" \
  || fail 'project-migrate must define the preview-first safe move contract'

PROJECT_MIGRATE_WITH_PERMANENT_SOURCE="$TMP_DIR/project-migrate-with-permanent-source.md"
sed '/never write.*ai\/allowed-roots\.md/d' "$PROJECT_MIGRATE_SKILL" \
  > "$PROJECT_MIGRATE_WITH_PERMANENT_SOURCE"
assert_rejected project_migrate_contract_valid "$PROJECT_MIGRATE_WITH_PERMANENT_SOURCE"

PROJECT_MIGRATE_WITH_COPY="$TMP_DIR/project-migrate-with-copy.md"
sed '/Move, never copy/d' "$PROJECT_MIGRATE_SKILL" > "$PROJECT_MIGRATE_WITH_COPY"
assert_rejected project_migrate_contract_valid "$PROJECT_MIGRATE_WITH_COPY"

PROJECT_MIGRATE_WITH_AUTOMATIC_CONTINUE="$TMP_DIR/project-migrate-with-automatic-continue.md"
sed '/continue automatically/d' "$PROJECT_MIGRATE_SKILL" \
  > "$PROJECT_MIGRATE_WITH_AUTOMATIC_CONTINUE"
assert_rejected project_migrate_contract_valid "$PROJECT_MIGRATE_WITH_AUTOMATIC_CONTINUE"

PROJECT_MIGRATE_WITHOUT_UNSAFE_CANDIDATES="$TMP_DIR/project-migrate-without-unsafe-candidates.md"
sed '/Never move backups,/d' \
  "$PROJECT_MIGRATE_SKILL" > "$PROJECT_MIGRATE_WITHOUT_UNSAFE_CANDIDATES"
assert_rejected project_migrate_contract_valid "$PROJECT_MIGRATE_WITHOUT_UNSAFE_CANDIDATES"

legacy_cleanup_contract_valid "$PROJECT_MIGRATE_SKILL" \
  || fail 'project-migrate must define the optional legacy standalone cleanup contract'

PROJECT_MIGRATE_WITHOUT_CLEANUP_GATE="$TMP_DIR/project-migrate-without-cleanup-gate.md"
sed '/Cleanup confirmation is separate/d' "$PROJECT_MIGRATE_SKILL" \
  > "$PROJECT_MIGRATE_WITHOUT_CLEANUP_GATE"
assert_rejected legacy_cleanup_contract_valid "$PROJECT_MIGRATE_WITHOUT_CLEANUP_GATE"

PROJECT_MIGRATE_WITHOUT_MEMORY_PATH="$TMP_DIR/project-migrate-without-memory-path.md"
sed '/ai\/project-context\.md/d' "$PROJECT_MIGRATE_SKILL" \
  > "$PROJECT_MIGRATE_WITHOUT_MEMORY_PATH"
assert_rejected legacy_cleanup_contract_valid "$PROJECT_MIGRATE_WITHOUT_MEMORY_PATH"

PROJECT_MIGRATE_WITH_AUTOMATIC_CLEANUP="$TMP_DIR/project-migrate-with-automatic-cleanup.md"
awk '
  /^## Russian preview template$/ {
    print "Cleanup is automatic: recursively delete the entire project with rm -rf."
  }
  { print }
' "$PROJECT_MIGRATE_SKILL" > "$PROJECT_MIGRATE_WITH_AUTOMATIC_CLEANUP"
assert_rejected legacy_cleanup_contract_valid "$PROJECT_MIGRATE_WITH_AUTOMATIC_CLEANUP"

legacy_cleanup_mutations_rejected "$PROJECT_MIGRATE_SKILL"

for hub_entry in "$HUB_AGENTS" "$HUB_CLAUDE" "$ROOT/hub-template/ai/architecture.md"; do
  legacy_cleanup_order_valid "$hub_entry" \
    || fail "hub cleanup routing order missing or out of order: $hub_entry"
done

for workflow in hub-environment-check hub-task-intake hub-task-switch hub-task-finish; do
  hub_shared_workflow_valid "$ROOT/hub-template/ai/skills/$workflow/SKILL.md" "$workflow" \
    || fail "shared hub workflow must preserve post-confirmation and memory-isolation gates: $workflow"
done

HUB_ARCHITECTURE="$ROOT/hub-template/ai/architecture.md"
hub_architecture_security_precedence_valid "$HUB_ARCHITECTURE" \
  || fail 'hub security and routing rules must outrank all project content'

INFO="$ROOT/hub-template/ai/skills/hub-info-update/SKILL.md"
LOCAL="$ROOT/hub-template/ai/skills/hub-local-router-install/SKILL.md"
assert_file "$INFO"
assert_file "$LOCAL"
grep -Fq 'Do not save the source transcript by default' "$INFO" \
  || fail 'transcript retention gate missing'
grep -Fq 'Confirm each affected project separately' "$INFO" \
  || fail 'per-project approval missing'
grep -Fq 'must not replace the current task' "$INFO" \
  || fail 'current-task protection missing'
grep -Fq 'MUST NOT invoke or perform `hub-task-finish`' "$INFO" \
  || fail 'info-update task-finish ban missing'
grep -Fq 'MUST NOT invoke or perform `hub-project-switch`' "$INFO" \
  || fail 'info-update project-switch ban missing'
info_update_project_group_sequence_valid "$INFO" \
  || fail 'info-update must stop for a separate confirmed project-switch between project groups before resuming'
grep -Fq '## Per-project proposal sections' "$INFO" \
  || fail 'per-project proposal structure missing'
for heading in 'Project identity and path' 'Facts' 'Decisions' 'Task changes' \
  'Future tasks' 'Signals' 'Hypotheses' 'Uncertainties' 'Proposed file edits' \
  'Per-project approval'; do
  grep -Fq "### $heading" "$INFO" \
    || fail "per-project proposal heading missing: $heading"
done
INFO_TEXT="$(tr '\n' ' ' < "$INFO" | tr -s ' ')"
[[ "$INFO_TEXT" == *'only after every related project group'* ]] \
  || fail 'cross-project signal placement rule missing'
info_update_confidence_schema_valid "$INFO" \
  || fail 'info-update confidence values must use uncertain, not unknown'
info_update_affected_projects_order_valid "$INFO" \
  || fail 'info-update must list affected projects between summary and proposals'
info_update_current_task_source_confidence_valid "$INFO" \
  || fail 'current-task change slot must include source and confidence immediately below'
grep -Fq 'at least three stable independent areas' "$LOCAL" \
  || fail 'local-router threshold missing'
grep -Fq 'no separate current task' "$LOCAL" \
  || fail 'local-router task boundary missing'

SIGNALS="$ROOT/hub-template/ai/cross-project-signals.md"
grep -Fq 'Confidence:' "$SIGNALS" \
  || fail 'signal confidence field missing'
grep -Eq 'expected_effect|review_after|expires_at' "$SIGNALS" \
  && fail 'fragile signal field present'
grep -Fq 'Hypotheses (optional)' "$SIGNALS" \
  || fail 'hypothesis separation missing'

ROUTER_SKILL="$ROOT/hub-template/ai/skills/hub-project-router/SKILL.md"
assert_contains "$ROUTER_SKILL" 'maximum of three'
assert_contains "$ROUTER_SKILL" 'high, medium, or low'
assert_contains "$ROUTER_SKILL" 'read-compact-project-index.sh'
assert_contains "$ROUTER_SKILL" 'wait for explicit confirmation'
router_read_boundary_valid "$ROUTER_SKILL" \
  || fail 'router must allow only the compact index and forbid broader reads before confirmation'
router_compact_index_reads_valid "$ROUTER_SKILL" \
  || fail 'router must use compact index fields before confirmation'
router_multiple_candidates_template_valid "$ROUTER_SKILL" \
  || fail 'router multi-candidate template must include confidence for all three candidate slots'

ROUTER_WITHOUT_INDEX="$TMP_DIR/router-without-index.md"
sed '/read-compact-project-index\.sh/d' "$ROUTER_SKILL" > "$ROUTER_WITHOUT_INDEX"
assert_rejected router_read_boundary_valid "$ROUTER_WITHOUT_INDEX"

ROUTER_WITHOUT_THIRD_SLOT="$TMP_DIR/router-without-third-slot.md"
sed '/3\. <project-id-3>/d' "$ROUTER_SKILL" > "$ROUTER_WITHOUT_THIRD_SLOT"
assert_rejected router_multiple_candidates_template_valid "$ROUTER_WITHOUT_THIRD_SLOT"

SWITCH_SKILL="$ROOT/hub-template/ai/skills/hub-project-switch/SKILL.md"
assert_contains "$SWITCH_SKILL" 'must not modify the current task'
assert_contains "$SWITCH_SKILL" 'canonical path validation'
SWITCH_TEXT="$(tr '\n' ' ' < "$SWITCH_SKILL" | tr -s ' ')"
[[ "$SWITCH_TEXT" == *'hub-owned `hub-environment-check`'* ]] \
  || fail 'project-switch must invoke hub-owned environment-check'
[[ "$SWITCH_TEXT" == *'hub-owned `hub-task-intake`'* ]] \
  || fail 'project-switch must invoke hub-owned task-intake'
assert_not_contains "$SWITCH_SKILL" 'project entry instructions'

REGISTER_SKILL="$ROOT/hub-template/ai/skills/hub-project-register/SKILL.md"
assert_contains "$REGISTER_SKILL" 'direct child directory names only'
assert_contains "$REGISTER_SKILL" 'Never auto-register backups'
assert_contains "$REGISTER_SKILL" 'approval before reading project context'
for card_field in 'Project ID' Name Type Status 'Last updated' Purpose 'Typical tasks' 'Memory entry point'; do
  assert_contains "$REGISTER_SKILL" "$card_field:"
done
assert_contains "$REGISTER_SKILL" 'must not read the memory entry point'
registration_primary_inventory_valid "$REGISTER_SKILL" \
  || fail 'registration inventory before individual confirmation must use direct child names only'
registration_confirmed_checks_valid "$REGISTER_SKILL" \
  || fail 'registration must defer Git and project-context checks until individual confirmation'
assert_contains "$REGISTER_SKILL" '<canonical-hub>/projects'

REGISTER_WITH_EARLY_GIT="$TMP_DIR/register-with-early-git.md"
awk '
  /^## After individual project confirmation$/ && !injected {
    print "Primary inventory must not inspect .git before confirmation."
    injected = 1
  }
  { print }
' "$REGISTER_SKILL" > "$REGISTER_WITH_EARLY_GIT"
assert_rejected registration_primary_inventory_valid "$REGISTER_WITH_EARLY_GIT"

CHECK_SKILL="$ROOT/hub-template/ai/skills/hub-registry-check/SKILL.md"
assert_contains "$CHECK_SKILL" 'read-only until approval'
assert_contains "$CHECK_SKILL" 'scripts/check-hub-registry.sh'
assert_contains "$CHECK_SKILL" 'cannot invoke it automatically'

VALID="$TMP_DIR/valid-hub"
mkdir -p "$VALID/ai/project-cards" "$VALID/projects/analytics-seo"
scaffold_project_memory "$VALID/projects/analytics-seo"
SENTINEL='MUST_NOT_BE_READ'
printf '%s\n' "$SENTINEL" > "$VALID/projects/analytics-seo/.env"
printf '%s\n' "$SENTINEL" > "$VALID/projects/analytics-seo/credentials.txt"
mkdir -p "$VALID/projects/unregistered-project" "$VALID/projects/analytics-seo-backup"
printf '%s\n' "$SENTINEL" > "$VALID/projects/unregistered-project/private.txt"
printf '%s\n' "$SENTINEL" > "$VALID/projects/analytics-seo-backup/private.txt"
printf '%s\n' '# Allowed Roots' '' "- $VALID/projects" > "$VALID/ai/allowed-roots.md"
printf '%s\n' '# Project Registry' '' \
  '## analytics-seo' \
  'Name: SEO Analytics' \
  'Type: work' \
  'Status: active' \
  "Path: $VALID/projects/analytics-seo" \
  'Tags: seo, analytics, traffic, leads' \
  'Card: ai/project-cards/analytics-seo.md' > "$VALID/ai/project-registry.md"
printf '%s\n' '# Archiprojects' > "$VALID/ai/archiprojects.md"
printf '%s\n' '# Project Card' '' \
  'Project ID: analytics-seo' \
  'Name: SEO Analytics' \
  'Type: work' \
  'Status: active' \
  'Last updated: 2026-08-12' \
  'Purpose: Analyze SEO reporting.' \
  'Typical tasks: Review analytics and reporting.' \
  "Memory entry point: $VALID/projects/analytics-seo/ai/current-task.md" > "$VALID/ai/project-cards/analytics-seo.md"

copy_valid_hub() {
  local destination="$1"
  cp -R "$VALID" "$destination"
  perl -pi -e "s#\\Q$VALID\\E#$destination#g" \
    "$destination/ai/allowed-roots.md" \
    "$destination/ai/project-registry.md" \
    "$destination/ai/project-cards/analytics-seo.md"
}

assert_compact_index_rows_valid() {
  local file="$1" expected
  expected="$TMP_DIR/compact-index.expected"
  printf '%s\n' \
    $'project_id\tname\ttags\tstatus\tpurpose_brief' \
    $'alpha-project\tAlpha Project\talpha, search\tactive\tAlpha purpose.' \
    $'beta-project\tBeta Project\tbeta, routing\tpaused\tBeta purpose.' \
    > "$expected"
  cmp -s "$expected" "$file" \
    || fail "compact project index must be deterministic TSV with exactly five columns"
}

bash -x "$ROOT/scripts/check-hub-registry.sh" "$VALID" > "$TMP_DIR/valid.out" 2> "$TMP_DIR/valid.trace"
assert_contains "$TMP_DIR/valid.out" 'Registry check passed'
assert_contains "$TMP_DIR/valid.out" '1 projects'
assert_not_contains "$TMP_DIR/valid.out" "$SENTINEL"
assert_not_contains "$TMP_DIR/valid.trace" "$SENTINEL"
assert_forbidden_reads_absent "$TMP_DIR/valid.trace" \
  '/.env' '/credentials.txt' '/unregistered-project/private.txt' '/analytics-seo-backup/private.txt'
echo 'Sentinel evidence: validator output and xtrace contain neither the marker nor the named forbidden file paths.'

MISSING_ARCHIPROJECTS="$TMP_DIR/missing-archiprojects"
copy_valid_hub "$MISSING_ARCHIPROJECTS"
rm "$MISSING_ARCHIPROJECTS/ai/archiprojects.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$MISSING_ARCHIPROJECTS" > "$TMP_DIR/missing-archiprojects.out" 2>&1; then
  fail 'registry validator accepted a hub without canonical archiprojects.md'
fi

# The valid fixture intentionally holds two unregistered directories. They must
# be reported on stderr without changing the exit code or the stdout summary,
# and without reading anything inside them.
bash "$ROOT/scripts/check-hub-registry.sh" "$VALID" \
  > "$TMP_DIR/valid-warn.out" 2> "$TMP_DIR/valid-warn.err" \
  || fail 'an unregistered directory must not change the validator exit code'
assert_contains "$TMP_DIR/valid-warn.err" 'WARNING: unregistered directory in projects root: unregistered-project'
assert_contains "$TMP_DIR/valid-warn.err" 'WARNING: unregistered directory in projects root: analytics-seo-backup'
assert_contains "$TMP_DIR/valid-warn.out" 'Registry check passed: 1 projects'
assert_not_contains "$TMP_DIR/valid-warn.out" 'WARNING'
assert_not_contains "$TMP_DIR/valid-warn.err" "$SENTINEL"

COMPACT="$TMP_DIR/compact-index-hub"
mkdir -p "$COMPACT/ai/project-cards" "$COMPACT/projects/alpha-project" "$COMPACT/projects/beta-project"
scaffold_project_memory "$COMPACT/projects/alpha-project"
scaffold_project_memory "$COMPACT/projects/beta-project"
printf '%s\n' 'MUST_NOT_BE_READ' > "$COMPACT/projects/alpha-project/ai/current-task.md"
printf '%s\n' '# Allowed Roots' '' "- $COMPACT/projects" > "$COMPACT/ai/allowed-roots.md"
printf '%s\n' '# Project Registry' '' \
  '## beta-project' \
  'Name: Beta Project' \
  'Type: work' \
  'Status: paused' \
  "Path: $COMPACT/projects/beta-project" \
  'Tags: beta, routing' \
  'Card: ai/project-cards/beta-project.md' '' \
  '## alpha-project' \
  'Name: Alpha Project' \
  'Type: work' \
  'Status: active' \
  "Path: $COMPACT/projects/alpha-project" \
  'Tags: alpha, search' \
  'Card: ai/project-cards/alpha-project.md' > "$COMPACT/ai/project-registry.md"
printf '%s\n' '# Project Card' '' \
  'Project ID: beta-project' \
  'Name: Beta Project' \
  'Type: work' \
  'Status: paused' \
  'Last updated: 2026-08-12' \
  'Purpose: Beta purpose.' \
  'Typical tasks: Route queries.' \
  "Memory entry point: $COMPACT/projects/beta-project/ai/current-task.md" \
  > "$COMPACT/ai/project-cards/beta-project.md"
printf '%s\n' '# Project Card' '' \
  'Project ID: alpha-project' \
  'Name: Alpha Project' \
  'Type: work' \
  'Status: active' \
  'Last updated: 2026-08-12' \
  'Purpose: Alpha purpose.' \
  'Typical tasks: Find projects.' \
  "Memory entry point: $COMPACT/projects/alpha-project/ai/current-task-MUST_NOT_BE_READ.md" \
  > "$COMPACT/ai/project-cards/alpha-project.md"

bash "$ROOT/scripts/read-compact-project-index.sh" "$COMPACT" \
  > "$TMP_DIR/compact-index.out" 2> "$TMP_DIR/compact-index.err"
assert_compact_index_rows_valid "$TMP_DIR/compact-index.out"
assert_not_contains "$TMP_DIR/compact-index.out" 'MUST_NOT_BE_READ'
assert_not_contains "$TMP_DIR/compact-index.out" 'Memory entry point'
assert_not_contains "$TMP_DIR/compact-index.out" 'ai/current-task.md'
assert_not_contains "$TMP_DIR/compact-index.err" 'MUST_NOT_BE_READ'

for symlink_case in ai registry project-cards card; do
  SYMLINK_COMPACT="$TMP_DIR/compact-index-symlink-$symlink_case"
  SYMLINK_OUTSIDE="$TMP_DIR/compact-index-outside-$symlink_case"
  cp -R "$COMPACT" "$SYMLINK_COMPACT"
  mkdir -p "$SYMLINK_OUTSIDE"
  printf '%s\n' 'COMPACT_INDEX_SYMLINK_SENTINEL' > "$SYMLINK_OUTSIDE/private.txt"
  case "$symlink_case" in
    ai)
      rm -rf "$SYMLINK_COMPACT/ai"
      ln -s "$SYMLINK_OUTSIDE" "$SYMLINK_COMPACT/ai"
      ;;
    registry)
      rm "$SYMLINK_COMPACT/ai/project-registry.md"
      ln -s "$SYMLINK_OUTSIDE/private.txt" "$SYMLINK_COMPACT/ai/project-registry.md"
      ;;
    project-cards)
      rm -rf "$SYMLINK_COMPACT/ai/project-cards"
      ln -s "$SYMLINK_OUTSIDE" "$SYMLINK_COMPACT/ai/project-cards"
      ;;
    card)
      rm "$SYMLINK_COMPACT/ai/project-cards/alpha-project.md"
      ln -s "$SYMLINK_OUTSIDE/private.txt" "$SYMLINK_COMPACT/ai/project-cards/alpha-project.md"
      ;;
  esac
  if bash "$ROOT/scripts/read-compact-project-index.sh" "$SYMLINK_COMPACT" \
    > "$TMP_DIR/compact-index-symlink-$symlink_case.out" \
    2> "$TMP_DIR/compact-index-symlink-$symlink_case.err"; then
    fail "compact project index accepted a $symlink_case symlink"
  fi
  assert_not_contains "$TMP_DIR/compact-index-symlink-$symlink_case.out" 'COMPACT_INDEX_SYMLINK_SENTINEL'
  assert_not_contains "$TMP_DIR/compact-index-symlink-$symlink_case.err" 'COMPACT_INDEX_SYMLINK_SENTINEL'
done

# Metadata search must not traverse into project directories or require full
# project cards. It reads only index fields and each card's Purpose line.
COMPACT_METADATA_ONLY="$TMP_DIR/compact-metadata-only-hub"
mkdir -p "$COMPACT_METADATA_ONLY/ai/project-cards" "$COMPACT_METADATA_ONLY/projects/unregistered-project"
printf '%s\n' 'MUST_NOT_BE_READ' > "$COMPACT_METADATA_ONLY/projects/unregistered-project/private.txt"
printf '%s\n' '# Project Registry' '' \
  '## beta-project' \
  'Name: Beta Project' \
  'Tags: beta, routing' \
  'Status: paused' \
  '## alpha-project' \
  'Name: Alpha Project' \
  'Tags: alpha, search' \
  'Status: active' > "$COMPACT_METADATA_ONLY/ai/project-registry.md"
printf '%s\n' 'Purpose: Beta purpose.' > "$COMPACT_METADATA_ONLY/ai/project-cards/beta-project.md"
printf '%s\n' 'Purpose: Alpha purpose.' > "$COMPACT_METADATA_ONLY/ai/project-cards/alpha-project.md"
bash "$ROOT/scripts/read-compact-project-index.sh" "$COMPACT_METADATA_ONLY" \
  > "$TMP_DIR/compact-metadata-only.out" 2> "$TMP_DIR/compact-metadata-only.err"
assert_compact_index_rows_valid "$TMP_DIR/compact-metadata-only.out"
[ ! -s "$TMP_DIR/compact-metadata-only.err" ] \
  || fail 'compact project index must keep a valid metadata-only lookup quiet'
assert_not_contains "$TMP_DIR/compact-metadata-only.out" 'MUST_NOT_BE_READ'
assert_not_contains "$TMP_DIR/compact-metadata-only.err" 'MUST_NOT_BE_READ'
assert_not_contains "$TMP_DIR/compact-metadata-only.err" 'unregistered-project'

TAB_COMPACT="$TMP_DIR/tab-compact-index-hub"
cp -R "$COMPACT" "$TAB_COMPACT"
perl -pi -e "s#\\Q$COMPACT\\E#$TAB_COMPACT#g" \
  "$TAB_COMPACT/ai/allowed-roots.md" \
  "$TAB_COMPACT/ai/project-registry.md" \
  "$TAB_COMPACT/ai/project-cards/alpha-project.md" \
  "$TAB_COMPACT/ai/project-cards/beta-project.md"
perl -0pi -e 's/Tags: alpha, search/Tags: alpha,\tsearch/' \
  "$TAB_COMPACT/ai/project-registry.md"
if bash "$ROOT/scripts/read-compact-project-index.sh" "$TAB_COMPACT" \
  > "$TMP_DIR/tab-compact-index.out" 2> "$TMP_DIR/tab-compact-index.err"; then
  fail 'compact project index accepted tab-bearing metadata'
fi
assert_not_contains "$TMP_DIR/tab-compact-index.out" $'project_id\tname\ttags\tstatus\tpurpose_brief'
[ ! -s "$TMP_DIR/tab-compact-index.out" ] \
  || fail 'tab-bearing metadata must not produce compact-index output'

BROKEN_COMPACT="$TMP_DIR/broken-compact-index-hub"
cp -R "$COMPACT" "$BROKEN_COMPACT"
awk '
  /^## alpha-project$/ { in_alpha = 1 }
  /^## / && $0 != "## alpha-project" { in_alpha = 0 }
  in_alpha && /^Tags: / { next }
  { print }
' "$BROKEN_COMPACT/ai/project-registry.md" \
  > "$BROKEN_COMPACT/ai/project-registry.md.tmp"
mv "$BROKEN_COMPACT/ai/project-registry.md.tmp" "$BROKEN_COMPACT/ai/project-registry.md"
if bash "$ROOT/scripts/read-compact-project-index.sh" "$BROKEN_COMPACT" \
  > "$TMP_DIR/broken-compact-index.out" 2> "$TMP_DIR/broken-compact-index.err"; then
  fail 'compact project index accepted invalid registry data'
fi
assert_not_contains "$TMP_DIR/broken-compact-index.out" $'project_id\tname\ttags\tstatus\tpurpose_brief'

# A hub whose projects root holds only registered projects stays silent.
QUIET_HUB="$TMP_DIR/quiet-hub"
copy_valid_hub "$QUIET_HUB"
rm -rf "$QUIET_HUB/projects/unregistered-project" "$QUIET_HUB/projects/analytics-seo-backup"
bash "$ROOT/scripts/check-hub-registry.sh" "$QUIET_HUB" \
  > "$TMP_DIR/quiet.out" 2> "$TMP_DIR/quiet.err" \
  || fail 'clean fixture must pass'
assert_contains "$TMP_DIR/quiet.out" 'Registry check passed: 1 projects'
assert_not_contains "$TMP_DIR/quiet.err" 'WARNING'
echo 'Unregistered-directory evidence: warned on stderr, exit code and stdout summary unchanged.'

EXTERNAL_ALLOWED_ROOT="$TMP_DIR/external-allowed-root-hub"
mkdir -p "$TMP_DIR/external-projects"
copy_valid_hub "$EXTERNAL_ALLOWED_ROOT"
printf '%s\n' '# Allowed Roots' '' "- $TMP_DIR/external-projects" > "$EXTERNAL_ALLOWED_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$EXTERNAL_ALLOWED_ROOT" > "$TMP_DIR/external-root.out" 2>&1; then
  fail 'validator accepted an external allowed root'
fi
assert_contains "$TMP_DIR/external-root.out" 'allowed root must be exactly the canonical projects root'

DUPLICATE_ALLOWED_ROOT="$TMP_DIR/duplicate-allowed-root-hub"
copy_valid_hub "$DUPLICATE_ALLOWED_ROOT"
printf '%s\n' "- $DUPLICATE_ALLOWED_ROOT/projects" >> "$DUPLICATE_ALLOWED_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$DUPLICATE_ALLOWED_ROOT" > "$TMP_DIR/duplicate-root.out" 2>&1; then
  fail 'validator accepted duplicate allowed roots'
fi
assert_contains "$TMP_DIR/duplicate-root.out" 'allowed-roots must contain exactly one canonical projects root'

OUTSIDE_PROJECT="$TMP_DIR/outside-project-hub"
copy_valid_hub "$OUTSIDE_PROJECT"
printf '%s\n' "$SENTINEL" >> "$OUTSIDE_PROJECT/ai/project-cards/analytics-seo.md"
sed "s#Path: $OUTSIDE_PROJECT/projects/analytics-seo#Path: $TMP_DIR/outside/analytics-seo#" \
  "$OUTSIDE_PROJECT/ai/project-registry.md" > "$OUTSIDE_PROJECT/ai/project-registry.md.tmp"
mv "$OUTSIDE_PROJECT/ai/project-registry.md.tmp" "$OUTSIDE_PROJECT/ai/project-registry.md"
if bash -x "$ROOT/scripts/check-hub-registry.sh" "$OUTSIDE_PROJECT" \
  > "$TMP_DIR/outside-project.out" 2> "$TMP_DIR/outside-project.trace"; then
  fail 'validator accepted a project path outside the canonical projects root'
fi
assert_contains "$TMP_DIR/outside-project.trace" 'project path must be a direct child of the canonical projects root'
assert_not_contains "$TMP_DIR/outside-project.out" "$SENTINEL"
assert_not_contains "$TMP_DIR/outside-project.trace" "$SENTINEL"

SENTINEL_CARD="$TMP_DIR/card-sentinel.md"
printf '%s\n' '# External Card' '' 'Project ID: analytics-seo' "$SENTINEL" > "$SENTINEL_CARD"

for card_escape_case in lexical symlink canonical; do
  escaped_hub="$TMP_DIR/card-$card_escape_case-hub"
  copy_valid_hub "$escaped_hub"
  case "$card_escape_case" in
    lexical)
      escaped_card='ai/project-cards/../../../card-sentinel.md'
      ;;
    symlink)
      ln -s "$SENTINEL_CARD" "$escaped_hub/ai/project-cards/escaped-card.md"
      escaped_card='ai/project-cards/escaped-card.md'
      ;;
    canonical)
      mkdir -p "$TMP_DIR/external-cards"
      cp "$SENTINEL_CARD" "$TMP_DIR/external-cards/analytics-seo.md"
      ln -s "$TMP_DIR/external-cards" "$escaped_hub/ai/project-cards/external"
      escaped_card='ai/project-cards/external/analytics-seo.md'
      ;;
  esac
  sed "s#Card: ai/project-cards/analytics-seo.md#Card: $escaped_card#" \
    "$escaped_hub/ai/project-registry.md" > "$escaped_hub/ai/project-registry.md.tmp"
  mv "$escaped_hub/ai/project-registry.md.tmp" "$escaped_hub/ai/project-registry.md"

  if bash -x "$ROOT/scripts/check-hub-registry.sh" "$escaped_hub" \
    > "$TMP_DIR/card-$card_escape_case.out" 2> "$TMP_DIR/card-$card_escape_case.trace"; then
    fail "validator accepted a $card_escape_case card escape"
  fi
  assert_contains "$TMP_DIR/card-$card_escape_case.trace" 'Card must be ai/project-cards/analytics-seo.md'
  assert_not_contains "$TMP_DIR/card-$card_escape_case.out" "$SENTINEL"
  assert_not_contains "$TMP_DIR/card-$card_escape_case.trace" "$SENTINEL"
  assert_not_contains "$TMP_DIR/card-$card_escape_case.trace" "grep -Fqx 'Project ID: analytics-seo'"
done
echo 'Malicious traversal evidence: lexical and symlink card escapes were rejected before the card-content check; sentinel markers were absent from output and xtrace.'

for scale_case in 5:2400 20:9600 50:24000 100:48000; do
  scale_count="${scale_case%%:*}"
  scale_budget="${scale_case#*:}"
  scale_hub="$TMP_DIR/scale-$scale_count-hub"
  scale_root="$scale_hub/projects"
  mkdir -p "$scale_hub/ai/project-cards" "$scale_root"
  printf '%s\n' '# Allowed Roots' '' "- $scale_root" > "$scale_hub/ai/allowed-roots.md"
  generate_registry "$scale_hub" "$scale_root" "$scale_count"

  bash "$ROOT/scripts/check-hub-registry.sh" "$scale_hub" > "$TMP_DIR/scale-$scale_count.out"
  assert_contains "$TMP_DIR/scale-$scale_count.out" "$scale_count projects"
  measured_bytes="$(wc -c < "$scale_hub/ai/project-registry.md" | tr -d '[:space:]')"
  [ "$measured_bytes" -le "$scale_budget" ] \
    || fail "registry with $scale_count projects uses $measured_bytes bytes; budget is $scale_budget"
  echo "Scale fixture: $scale_count projects, $measured_bytes/$scale_budget bytes"
done

for required_field in Name Type Status Path Tags Card; do
  missing_field="$TMP_DIR/missing-$required_field-hub"
  copy_valid_hub "$missing_field"
  sed "/^$required_field: /d" "$missing_field/ai/project-registry.md" > "$missing_field/ai/project-registry.md.tmp"
  mv "$missing_field/ai/project-registry.md.tmp" "$missing_field/ai/project-registry.md"
  if bash "$ROOT/scripts/check-hub-registry.sh" "$missing_field" > "$TMP_DIR/missing-$required_field.out" 2>&1; then
    fail "validator accepted an entry without $required_field"
  fi
  assert_contains "$TMP_DIR/missing-$required_field.out" "missing $required_field"
done

for required_card_field in 'Project ID' Name Type Status 'Last updated' Purpose 'Typical tasks' 'Memory entry point'; do
  missing_card_field="$TMP_DIR/missing-card-${required_card_field// /-}-hub"
  copy_valid_hub "$missing_card_field"
  sed "/^$required_card_field: /d" "$missing_card_field/ai/project-cards/analytics-seo.md" \
    > "$missing_card_field/ai/project-cards/analytics-seo.md.tmp"
  mv "$missing_card_field/ai/project-cards/analytics-seo.md.tmp" "$missing_card_field/ai/project-cards/analytics-seo.md"
  if bash "$ROOT/scripts/check-hub-registry.sh" "$missing_card_field" > "$TMP_DIR/missing-card-${required_card_field// /-}.out" 2>&1; then
    fail "validator accepted a card without $required_card_field"
  fi
  assert_contains "$TMP_DIR/missing-card-${required_card_field// /-}.out" "missing card $required_card_field"
done

CARD_MISMATCH="$TMP_DIR/card-mismatch-hub"
copy_valid_hub "$CARD_MISMATCH"
sed 's/^Project ID: analytics-seo$/Project ID: another-project/' \
  "$CARD_MISMATCH/ai/project-cards/analytics-seo.md" > "$CARD_MISMATCH/ai/project-cards/analytics-seo.md.tmp"
mv "$CARD_MISMATCH/ai/project-cards/analytics-seo.md.tmp" "$CARD_MISMATCH/ai/project-cards/analytics-seo.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$CARD_MISMATCH" > "$TMP_DIR/card-mismatch.out" 2>&1; then
  fail 'validator accepted a card with a different Project ID'
fi
assert_contains "$TMP_DIR/card-mismatch.out" 'card Project ID mismatch'

CARD_STATUS_MISMATCH="$TMP_DIR/card-status-mismatch-hub"
copy_valid_hub "$CARD_STATUS_MISMATCH"
sed 's/^Status: active$/Status: paused/' "$CARD_STATUS_MISMATCH/ai/project-cards/analytics-seo.md" \
  > "$CARD_STATUS_MISMATCH/ai/project-cards/analytics-seo.md.tmp"
mv "$CARD_STATUS_MISMATCH/ai/project-cards/analytics-seo.md.tmp" "$CARD_STATUS_MISMATCH/ai/project-cards/analytics-seo.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$CARD_STATUS_MISMATCH" > "$TMP_DIR/card-status-mismatch.out" 2>&1; then
  fail 'validator accepted a card with a different Status'
fi
assert_contains "$TMP_DIR/card-status-mismatch.out" 'card Status mismatch'

UNSAFE_MEMORY_ENTRY="$TMP_DIR/unsafe-memory-entry-hub"
copy_valid_hub "$UNSAFE_MEMORY_ENTRY"
sed "s#^Memory entry point: .*#Memory entry point: $TMP_DIR/outside/ai/current-task.md#" \
  "$UNSAFE_MEMORY_ENTRY/ai/project-cards/analytics-seo.md" > "$UNSAFE_MEMORY_ENTRY/ai/project-cards/analytics-seo.md.tmp"
mv "$UNSAFE_MEMORY_ENTRY/ai/project-cards/analytics-seo.md.tmp" "$UNSAFE_MEMORY_ENTRY/ai/project-cards/analytics-seo.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$UNSAFE_MEMORY_ENTRY" > "$TMP_DIR/unsafe-memory-entry.out" 2>&1; then
  fail 'validator accepted a memory entry point outside the registered project ai directory'
fi
assert_contains "$TMP_DIR/unsafe-memory-entry.out" 'card Memory entry point must stay beneath the registered project ai directory'

DUPLICATE_MEMORY_ENTRY="$TMP_DIR/duplicate-memory-entry-hub"
copy_valid_hub "$DUPLICATE_MEMORY_ENTRY"
printf '%s\n' "Memory entry point: $TMP_DIR/outside/ai/current-task.md" >> "$DUPLICATE_MEMORY_ENTRY/ai/project-cards/analytics-seo.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$DUPLICATE_MEMORY_ENTRY" > "$TMP_DIR/duplicate-memory-entry.out" 2>&1; then
  fail 'validator accepted a duplicate Memory entry point field'
fi
assert_contains "$TMP_DIR/duplicate-memory-entry.out" 'duplicate card Memory entry point:'

# A registered active project must carry the full memory scaffold.
for missing_memory_file in current-task paused-tasks future-tasks project-context decisions changelog; do
  MISSING_MEMORY="$TMP_DIR/missing-memory-$missing_memory_file-hub"
  copy_valid_hub "$MISSING_MEMORY"
  rm "$MISSING_MEMORY/projects/analytics-seo/ai/$missing_memory_file.md"
  if bash "$ROOT/scripts/check-hub-registry.sh" "$MISSING_MEMORY" \
    > "$TMP_DIR/missing-memory-$missing_memory_file.out" 2>&1; then
    fail "validator accepted a project without ai/$missing_memory_file.md"
  fi
  assert_contains "$TMP_DIR/missing-memory-$missing_memory_file.out" \
    "missing project memory file for analytics-seo: ai/$missing_memory_file.md"
done

MEMORY_SYMLINK="$TMP_DIR/memory-symlink-hub"
copy_valid_hub "$MEMORY_SYMLINK"
rm "$MEMORY_SYMLINK/projects/analytics-seo/ai/decisions.md"
ln -s "$TMP_DIR/outside-memory-target.md" "$MEMORY_SYMLINK/projects/analytics-seo/ai/decisions.md"
printf '%s\n' "$SENTINEL" > "$TMP_DIR/outside-memory-target.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$MEMORY_SYMLINK" \
  > "$TMP_DIR/memory-symlink.out" 2>&1; then
  fail 'validator accepted a symlinked project memory file'
fi
assert_contains "$TMP_DIR/memory-symlink.out" 'project memory file must not be a symlink'
assert_not_contains "$TMP_DIR/memory-symlink.out" "$SENTINEL"

# An archived project is not required to keep an active memory scaffold.
ARCHIVED_MEMORY="$TMP_DIR/archived-memory-hub"
copy_valid_hub "$ARCHIVED_MEMORY"
rm "$ARCHIVED_MEMORY/projects/analytics-seo/ai/future-tasks.md"
perl -pi -e 's/^Status: active$/Status: archived/' \
  "$ARCHIVED_MEMORY/ai/project-registry.md" \
  "$ARCHIVED_MEMORY/ai/project-cards/analytics-seo.md"
bash "$ROOT/scripts/check-hub-registry.sh" "$ARCHIVED_MEMORY" > "$TMP_DIR/archived-memory.out"
assert_contains "$TMP_DIR/archived-memory.out" 'Registry check passed'

# The installed hub's two entry files must stay equal beyond their header lines.
ENTRY_PARITY="$TMP_DIR/entry-parity-hub"
copy_valid_hub "$ENTRY_PARITY"
printf '%s\n' '# Personal AI Hub — Codex' \
  '<!-- Tool-specific activation: Codex reads AGENTS.md as its project entry file. -->' \
  '' '- Shared hub rule.' > "$ENTRY_PARITY/AGENTS.md"
printf '%s\n' '# Personal AI Hub — Claude Code' \
  '<!-- Tool-specific activation: Claude Code reads CLAUDE.md as its project entry file. -->' \
  '' '- Shared hub rule.' > "$ENTRY_PARITY/CLAUDE.md"
bash "$ROOT/scripts/check-hub-registry.sh" "$ENTRY_PARITY" > "$TMP_DIR/entry-parity.out"
assert_contains "$TMP_DIR/entry-parity.out" 'Registry check passed'

printf '%s\n' '- A rule only Codex received.' >> "$ENTRY_PARITY/AGENTS.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ENTRY_PARITY" \
  > "$TMP_DIR/entry-divergence.out" 2>&1; then
  fail 'validator accepted diverging hub entry files'
fi
assert_contains "$TMP_DIR/entry-divergence.out" \
  'CLAUDE.md and AGENTS.md diverge outside their tool-specific header lines'

ENTRY_HALF_MISSING="$TMP_DIR/entry-half-missing-hub"
copy_valid_hub "$ENTRY_HALF_MISSING"
printf '%s\n' '# Personal AI Hub — Codex' '' '- Shared hub rule.' > "$ENTRY_HALF_MISSING/AGENTS.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ENTRY_HALF_MISSING" \
  > "$TMP_DIR/entry-half-missing.out" 2>&1; then
  fail 'validator accepted a hub carrying only one entry file'
fi
assert_contains "$TMP_DIR/entry-half-missing.out" 'while AGENTS.md is present'

# A leftover unprefixed skill directory means an update did not finish.
STALE_SKILL="$TMP_DIR/stale-skill-hub"
copy_valid_hub "$STALE_SKILL"
mkdir -p "$STALE_SKILL/ai/skills/hub-task-intake" "$STALE_SKILL/ai/skills/task-intake"
if bash "$ROOT/scripts/check-hub-registry.sh" "$STALE_SKILL" \
  > "$TMP_DIR/stale-skill.out" 2>&1; then
  fail 'validator accepted an unprefixed hub skill directory'
fi
assert_contains "$TMP_DIR/stale-skill.out" 'hub skill directory must be named hub-*: ai/skills/task-intake'

# A hub whose skills are all prefixed passes.
FRESH_SKILL="$TMP_DIR/fresh-skill-hub"
copy_valid_hub "$FRESH_SKILL"
mkdir -p "$FRESH_SKILL/ai/skills/hub-task-intake"
bash "$ROOT/scripts/check-hub-registry.sh" "$FRESH_SKILL" > "$TMP_DIR/fresh-skill.out"
assert_contains "$TMP_DIR/fresh-skill.out" 'Registry check passed'

INVALID="$TMP_DIR/invalid-hub"
copy_valid_hub "$INVALID"
sed "s#Path: $INVALID/projects/analytics-seo#Path: $TMP_DIR/outside#" \
  "$INVALID/ai/project-registry.md" > "$INVALID/ai/project-registry.md.tmp"
mv "$INVALID/ai/project-registry.md.tmp" "$INVALID/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$INVALID" > "$TMP_DIR/invalid.out" 2>&1; then
  fail 'validator accepted project outside allowed roots'
fi
assert_contains "$TMP_DIR/invalid.out" 'project path must be a direct child of the canonical projects root'

MISSING_ROOT="$TMP_DIR/missing-root-hub"
copy_valid_hub "$MISSING_ROOT"
printf '%s\n' '# Allowed Roots' '' "- $TMP_DIR/does-not-exist" > "$MISSING_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$MISSING_ROOT" > "$TMP_DIR/missing-root.out" 2>&1; then
  fail 'validator accepted a nonexistent allowed root'
fi
assert_contains "$TMP_DIR/missing-root.out" 'allowed root must be exactly the canonical projects root'

RELATIVE_ROOT="$TMP_DIR/relative-root-hub"
copy_valid_hub "$RELATIVE_ROOT"
printf '%s\n' '# Allowed Roots' '' '- relative/projects' > "$RELATIVE_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$RELATIVE_ROOT" > "$TMP_DIR/relative-root.out" 2>&1; then
  fail 'validator accepted a relative allowed root'
fi
assert_contains "$TMP_DIR/relative-root.out" 'allowed root must be exactly the canonical projects root'

EMPTY_ROOT="$TMP_DIR/empty-root-hub"
copy_valid_hub "$EMPTY_ROOT"
printf '%s\n' '# Allowed Roots' '' '- ' > "$EMPTY_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$EMPTY_ROOT" > "$TMP_DIR/empty-root.out" 2>&1; then
  fail 'validator accepted an empty allowed root'
fi
assert_contains "$TMP_DIR/empty-root.out" 'allowed root must be exactly the canonical projects root'

ROOT_FILESYSTEM="$TMP_DIR/root-filesystem-hub"
copy_valid_hub "$ROOT_FILESYSTEM"
printf '%s\n' '# Allowed Roots' '' '- /' > "$ROOT_FILESYSTEM/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ROOT_FILESYSTEM" > "$TMP_DIR/root-filesystem.out" 2>&1; then
  fail 'validator accepted filesystem root as an allowed root'
fi
assert_contains "$TMP_DIR/root-filesystem.out" 'allowed root must be exactly the canonical projects root'

ROOT_DOUBLE_SLASH="$TMP_DIR/root-double-slash-hub"
copy_valid_hub "$ROOT_DOUBLE_SLASH"
printf '%s\n' '# Allowed Roots' '' '- //' > "$ROOT_DOUBLE_SLASH/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ROOT_DOUBLE_SLASH" > "$TMP_DIR/root-double-slash.out" 2>&1; then
  fail 'validator accepted // as an allowed root'
fi
assert_contains "$TMP_DIR/root-double-slash.out" 'allowed root must be exactly the canonical projects root'

ROOT_SYMLINK_FILESYSTEM="$TMP_DIR/root-symlink-filesystem-hub"
ln -s / "$TMP_DIR/filesystem-root-link"
copy_valid_hub "$ROOT_SYMLINK_FILESYSTEM"
printf '%s\n' '# Allowed Roots' '' "- $TMP_DIR/filesystem-root-link" > "$ROOT_SYMLINK_FILESYSTEM/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ROOT_SYMLINK_FILESYSTEM" > "$TMP_DIR/root-symlink-filesystem.out" 2>&1; then
  fail 'validator accepted a symlink resolving to filesystem root'
fi
assert_contains "$TMP_DIR/root-symlink-filesystem.out" 'allowed root must be exactly the canonical projects root'

HOME_ROOT="$(cd "$HOME" && pwd -P)"
HOME_ALLOWED_ROOT="$TMP_DIR/home-allowed-root-hub"
copy_valid_hub "$HOME_ALLOWED_ROOT"
printf '%s\n' '# Allowed Roots' '' "- $HOME_ROOT" > "$HOME_ALLOWED_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$HOME_ALLOWED_ROOT" > "$TMP_DIR/home-allowed-root.out" 2>&1; then
  fail 'validator accepted the home directory as an allowed root'
fi
assert_contains "$TMP_DIR/home-allowed-root.out" 'allowed root must be exactly the canonical projects root'

LEXICAL_ESCAPE="$TMP_DIR/lexical-escape-hub"
copy_valid_hub "$LEXICAL_ESCAPE"
sed "s#Path: $LEXICAL_ESCAPE/projects/analytics-seo#Path: $TMP_DIR/projects/../outside/missing#" \
  "$LEXICAL_ESCAPE/ai/project-registry.md" > "$LEXICAL_ESCAPE/ai/project-registry.md.tmp"
mv "$LEXICAL_ESCAPE/ai/project-registry.md.tmp" "$LEXICAL_ESCAPE/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$LEXICAL_ESCAPE" > "$TMP_DIR/lexical-escape.out" 2>&1; then
  fail 'validator accepted a lexical path escape'
fi
assert_contains "$TMP_DIR/lexical-escape.out" 'project path must be a direct child of the canonical projects root'

SYMLINK_ESCAPE="$TMP_DIR/symlink-escape-hub"
mkdir -p "$TMP_DIR/outside"
copy_valid_hub "$SYMLINK_ESCAPE"
ln -s "$TMP_DIR/outside" "$SYMLINK_ESCAPE/projects/link-out"
sed "s#Path: $SYMLINK_ESCAPE/projects/analytics-seo#Path: $SYMLINK_ESCAPE/projects/link-out/missing#" \
  "$SYMLINK_ESCAPE/ai/project-registry.md" > "$SYMLINK_ESCAPE/ai/project-registry.md.tmp"
mv "$SYMLINK_ESCAPE/ai/project-registry.md.tmp" "$SYMLINK_ESCAPE/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$SYMLINK_ESCAPE" > "$TMP_DIR/symlink-escape.out" 2>&1; then
  fail 'validator accepted a symlink component escape'
fi
assert_contains "$TMP_DIR/symlink-escape.out" 'project path must be a direct child of the canonical projects root'

MISSING_PROJECT="$TMP_DIR/missing-project-hub"
copy_valid_hub "$MISSING_PROJECT"
sed -e 's/Status: active/Status: missing/' \
  -e "s#Path: $MISSING_PROJECT/projects/analytics-seo#Path: $MISSING_PROJECT/projects/genuinely-missing#" \
  "$MISSING_PROJECT/ai/project-registry.md" > "$MISSING_PROJECT/ai/project-registry.md.tmp"
mv "$MISSING_PROJECT/ai/project-registry.md.tmp" "$MISSING_PROJECT/ai/project-registry.md"
sed -e 's/^Status: active$/Status: missing/' \
  -e "s#^Memory entry point: $MISSING_PROJECT/projects/analytics-seo/#Memory entry point: $MISSING_PROJECT/projects/genuinely-missing/#" \
  "$MISSING_PROJECT/ai/project-cards/analytics-seo.md" \
  > "$MISSING_PROJECT/ai/project-cards/analytics-seo.md.tmp"
mv "$MISSING_PROJECT/ai/project-cards/analytics-seo.md.tmp" "$MISSING_PROJECT/ai/project-cards/analytics-seo.md"
bash "$ROOT/scripts/check-hub-registry.sh" "$MISSING_PROJECT" > "$TMP_DIR/missing-project.out"
assert_contains "$TMP_DIR/missing-project.out" 'Registry check passed'

HUB_INSTALL="$TMP_DIR/installed-hub/_ai-hub"
if bash "$ROOT/scripts/install.sh" --mode hub "$TMP_DIR/not-a-hub" > "$TMP_DIR/not-a-hub.out" 2>&1; then
  fail 'hub installer accepted a target not named _ai-hub'
fi
assert_contains "$TMP_DIR/not-a-hub.out" 'Hub directory must be named _ai-hub.'

NON_HUB_TARGET="$TMP_DIR/non-hub-target/_ai-hub"
mkdir -p "$NON_HUB_TARGET"
printf '%s\n' 'do not overwrite' > "$NON_HUB_TARGET/existing.txt"
if bash "$ROOT/scripts/install.sh" --mode hub "$NON_HUB_TARGET" > "$TMP_DIR/non-hub-target.out" 2>&1; then
  fail 'hub installer accepted a nonempty target that is not an installed hub'
fi
assert_contains "$TMP_DIR/non-hub-target.out" 'Target is not an installed personal AI hub'
assert_contains "$NON_HUB_TARGET/existing.txt" 'do not overwrite'

bash -x "$ROOT/scripts/install.sh" --mode hub "$HUB_INSTALL" > "$TMP_DIR/install.out" 2> "$TMP_DIR/install.trace"
assert_not_contains "$TMP_DIR/install.out" "$SENTINEL"
assert_not_contains "$TMP_DIR/install.trace" "$SENTINEL"
assert_forbidden_reads_absent "$TMP_DIR/install.trace" \
  '/.env' '/credentials.txt' '/unregistered-folder/private.txt' '/example-backup/private/private.txt'
echo 'Sentinel evidence: installer output and xtrace contain neither the marker nor the named forbidden file paths.'
assert_file "$HUB_INSTALL/AGENTS.md"
assert_file "$HUB_INSTALL/CLAUDE.md"
assert_file "$HUB_INSTALL/ai/project-registry.md"
assert_file "$HUB_INSTALL/scripts/read-compact-project-index.sh"
assert_file "$HUB_INSTALL/ai/archiprojects.md"
assert_file "$HUB_INSTALL/scripts/check-hub-registry.sh"
assert_file "$HUB_INSTALL/projects/.gitkeep"
assert_file "$HUB_INSTALL/ai/skills/hub-knowledge-capture/SKILL.md"
assert_file "$HUB_INSTALL/ai/skills/hub-knowledge-review/SKILL.md"
ARCHIPROJECTS_BASE="$TMP_DIR/archiprojects-base"
cp -R "$HUB_INSTALL" "$ARCHIPROJECTS_BASE"
PROJECT_ROOT="$HUB_INSTALL/projects"
mkdir -p "$PROJECT_ROOT/example-project" "$PROJECT_ROOT/example-backup"
printf '%s\n' "$SENTINEL" > "$PROJECT_ROOT/example-project/.env"
printf '%s\n' "$SENTINEL" > "$PROJECT_ROOT/example-project/credentials.txt"
mkdir -p "$PROJECT_ROOT/unregistered-folder" "$PROJECT_ROOT/example-backup/private"
printf '%s\n' "$SENTINEL" > "$PROJECT_ROOT/unregistered-folder/private.txt"
printf '%s\n' "$SENTINEL" > "$PROJECT_ROOT/example-backup/private/private.txt"
PROJECT_ROOT_CANONICAL="$(cd "$PROJECT_ROOT" && pwd -P)"
assert_contains "$HUB_INSTALL/ai/allowed-roots.md" "$PROJECT_ROOT_CANONICAL"
assert_contains "$TMP_DIR/install.out" 'Registration requires confirmation'
grep -Fq 'example-project' "$HUB_INSTALL/ai/project-registry.md" && fail 'installer auto-registered a project'
bash "$ROOT/scripts/check-hub-registry.sh" "$HUB_INSTALL" > "$TMP_DIR/installed-hub-registry.out"
assert_contains "$TMP_DIR/installed-hub-registry.out" 'Registry check passed'
bash "$HUB_INSTALL/scripts/check-hub-registry.sh" "$HUB_INSTALL" > "$TMP_DIR/installed-hub-local-registry.out"
assert_contains "$TMP_DIR/installed-hub-local-registry.out" 'Registry check passed'

ARCHIPROJECTS_SURVIVE="$TMP_DIR/archiprojects-survive-hub"
cp -R "$ARCHIPROJECTS_BASE" "$ARCHIPROJECTS_SURVIVE"
printf '%s\n' '# Archiprojects' '' 'USER_ARCHIPROJECT_MUST_SURVIVE' > "$ARCHIPROJECTS_SURVIVE/ai/archiprojects.md"
cp "$ARCHIPROJECTS_SURVIVE/ai/archiprojects.md" "$TMP_DIR/archiprojects.before"
bash "$ROOT/scripts/update-installed-hub.sh" --hub "$ARCHIPROJECTS_SURVIVE" --source "$ROOT" --apply --allow-dirty > "$TMP_DIR/archiprojects-survive.out"
cmp -s "$TMP_DIR/archiprojects.before" "$ARCHIPROJECTS_SURVIVE/ai/archiprojects.md" || fail 'hub updater overwrote existing archiprojects.md'

ARCHIPROJECTS_MISSING="$TMP_DIR/archiprojects-missing-hub"
cp -R "$ARCHIPROJECTS_BASE" "$ARCHIPROJECTS_MISSING"
rm "$ARCHIPROJECTS_MISSING/ai/archiprojects.md"
bash "$ROOT/scripts/update-installed-hub.sh" --hub "$ARCHIPROJECTS_MISSING" --source "$ROOT" --apply --allow-dirty > "$TMP_DIR/archiprojects-missing.out"
assert_file "$ARCHIPROJECTS_MISSING/ai/archiprojects.md"
cmp -s "$ROOT/hub-template/ai/archiprojects.md" "$ARCHIPROJECTS_MISSING/ai/archiprojects.md" \
  || fail 'hub updater did not restore missing archiprojects.md from the template'

cp "$HUB_INSTALL/ai/project-registry.md" "$TMP_DIR/install-registry.before"
cp "$HUB_INSTALL/ai/allowed-roots.md" "$TMP_DIR/install-roots.before"
bash "$ROOT/scripts/install.sh" --mode hub "$HUB_INSTALL" > "$TMP_DIR/install-update.out"
cmp -s "$TMP_DIR/install-registry.before" "$HUB_INSTALL/ai/project-registry.md" || fail 'hub reinstall overwrote registry'
cmp -s "$TMP_DIR/install-roots.before" "$HUB_INSTALL/ai/allowed-roots.md" || fail 'hub reinstall overwrote allowed roots'
git -C "$HUB_INSTALL" config user.email "smoke@example.invalid"
git -C "$HUB_INSTALL" config user.name "Smoke Test"
git -C "$HUB_INSTALL" add .
git -C "$HUB_INSTALL" commit -m "test: install hub" >/dev/null

if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$ROOT/template" --dry-run > "$TMP_DIR/standalone-source.out" 2>&1; then
  fail 'hub updater accepted the standalone template as a hub source'
fi
assert_contains "$TMP_DIR/standalone-source.out" 'Source template is not a personal AI hub'

MISSING_COMPACT_SOURCE="$TMP_DIR/missing-compact-source"
mkdir -p "$MISSING_COMPACT_SOURCE"
cp -R "$ROOT/hub-template" "$MISSING_COMPACT_SOURCE/hub-template"
if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$MISSING_COMPACT_SOURCE" --dry-run > "$TMP_DIR/missing-compact-source.out" 2>&1; then
  fail 'hub updater accepted a source without the mandatory compact reader'
fi
assert_contains "$TMP_DIR/missing-compact-source.out" 'missing mandatory script: scripts/read-compact-project-index.sh'

INCOMPLETE_HUB_SOURCE="$TMP_DIR/incomplete-hub-source"
mkdir -p "$INCOMPLETE_HUB_SOURCE"
cp -R "$ROOT/hub-template" "$INCOMPLETE_HUB_SOURCE/hub-template"
mkdir -p "$INCOMPLETE_HUB_SOURCE/scripts"
cp "$ROOT/scripts/read-compact-project-index.sh" "$INCOMPLETE_HUB_SOURCE/scripts/read-compact-project-index.sh"
rm "$INCOMPLETE_HUB_SOURCE/hub-template/ai/skills/hub-project-router/SKILL.md"
if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$INCOMPLETE_HUB_SOURCE" --dry-run > "$TMP_DIR/incomplete-hub-source.out" 2>&1; then
  fail 'hub updater accepted a source without a mandatory hub skill'
fi
assert_contains "$TMP_DIR/incomplete-hub-source.out" 'missing mandatory hub skill: hub-project-router'

INCOMPLETE_KNOWLEDGE_SOURCE="$TMP_DIR/incomplete-knowledge-source"
mkdir -p "$INCOMPLETE_KNOWLEDGE_SOURCE"
cp -R "$ROOT/hub-template" "$INCOMPLETE_KNOWLEDGE_SOURCE/hub-template"
mkdir -p "$INCOMPLETE_KNOWLEDGE_SOURCE/scripts"
cp "$ROOT/scripts/read-compact-project-index.sh" "$INCOMPLETE_KNOWLEDGE_SOURCE/scripts/read-compact-project-index.sh"
rm "$INCOMPLETE_KNOWLEDGE_SOURCE/hub-template/ai/skills/hub-knowledge-review/SKILL.md"
if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$INCOMPLETE_KNOWLEDGE_SOURCE" --dry-run > "$TMP_DIR/incomplete-knowledge-source.out" 2>&1; then
  fail 'hub updater accepted a source without the mandatory knowledge quality cycle'
fi
assert_contains "$TMP_DIR/incomplete-knowledge-source.out" 'missing mandatory hub skill: hub-knowledge-review'

# Regression: --source must resolve against the caller's directory, not the hub.
# Before this fix a relative --source silently resolved inside the hub, so the
# updater could compare the hub with itself and report "no updates" (Audit 1).
RELATIVE_SOURCE_OUT="$TMP_DIR/relative-source.out"
(cd "$ROOT" && bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$HUB_INSTALL" --source . --dry-run) > "$RELATIVE_SOURCE_OUT" 2>&1 \
  || fail "relative --source dry-run against the hub failed unexpectedly"
assert_contains "$RELATIVE_SOURCE_OUT" "Source template: $ROOT/hub-template"
assert_not_contains "$RELATIVE_SOURCE_OUT" "Source template: $HUB_INSTALL"

# A source that resolves to the target itself is refused outright.
if bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$HUB_INSTALL" --source "$HUB_INSTALL" --dry-run \
  > "$TMP_DIR/self-source.out" 2>&1; then
  fail 'hub updater compared the hub with itself'
fi
assert_contains "$TMP_DIR/self-source.out" 'resolves to the hub itself'
echo 'Source-resolution evidence: relative --source resolved against the caller, self-source refused.'

# --check compares version numbers only. Its success message must not read as
# "the files match", because a hub with a matching version and a drifted rule
# file is reported as up to date (Audit 3, FT-20260815-002).
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$HUB_INSTALL" --source "$ROOT" --check > "$TMP_DIR/check-wording.out" 2>&1 \
  || fail "--check against a matching-version hub failed unexpectedly"
assert_contains "$TMP_DIR/check-wording.out" 'Version numbers match'
assert_contains "$TMP_DIR/check-wording.out" '--dry-run'
assert_not_contains "$TMP_DIR/check-wording.out" 'Hub architecture is up to date (v'
echo 'Check-wording evidence: --check states that it compared version numbers only.'

printf '%s\n' '# Allowed Roots' '' '- /custom/projects' > "$HUB_INSTALL/ai/allowed-roots.md"
printf '%s\n' '# Project Registry' '' 'custom registry' > "$HUB_INSTALL/ai/project-registry.md"
printf '%s\n' 'Project ID: custom' > "$HUB_INSTALL/ai/active-project.md"
printf '%s\n' '# Custom Card' '' 'Project ID: custom' > "$HUB_INSTALL/ai/project-cards/custom.md"
printf '%s\n' '# Cross-Project Signals' '' 'custom signal' > "$HUB_INSTALL/ai/cross-project-signals.md"
printf '%s\n' '# Archived Memory' '' 'custom archive' > "$HUB_INSTALL/ai/archive/custom.md"
cp "$HUB_INSTALL/ai/allowed-roots.md" "$TMP_DIR/allowed-roots.before"
cp "$HUB_INSTALL/ai/project-registry.md" "$TMP_DIR/registry.before"
cp "$HUB_INSTALL/ai/active-project.md" "$TMP_DIR/active.before"
cp "$HUB_INSTALL/ai/project-cards/custom.md" "$TMP_DIR/card.before"
cp "$HUB_INSTALL/ai/cross-project-signals.md" "$TMP_DIR/signals.before"
cp "$HUB_INSTALL/ai/archive/custom.md" "$TMP_DIR/archive.before"
rm "$HUB_INSTALL/ai/archive/.gitkeep"
rm "$HUB_INSTALL/ai/project-cards/.gitkeep"
printf '%s\n' 'stale hub entry' > "$HUB_INSTALL/AGENTS.md"
printf '%s\n' 'stale validator' > "$HUB_INSTALL/scripts/check-hub-registry.sh"
printf '%s\n' 'stale compact index' > "$HUB_INSTALL/scripts/read-compact-project-index.sh"

bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$ROOT" --dry-run > "$TMP_DIR/hub-dry-run.out"
assert_contains "$TMP_DIR/hub-dry-run.out" '### AGENTS.md'
assert_contains "$TMP_DIR/hub-dry-run.out" '### scripts/read-compact-project-index.sh'
assert_contains "$TMP_DIR/hub-dry-run.out" 'Would create missing hub memory file without overwriting hub memory: ai/archive/.gitkeep'
assert_contains "$TMP_DIR/hub-dry-run.out" 'Would create missing hub memory file without overwriting hub memory: ai/project-cards/.gitkeep'
assert_not_exists "$HUB_INSTALL/ai/archive/.gitkeep"
assert_not_exists "$HUB_INSTALL/ai/project-cards/.gitkeep"

# A superseded path present in the hub is announced in dry-run and not removed.
SUPERSEDED_PREVIEW="$TMP_DIR/superseded-preview-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_PREVIEW"
mkdir -p "$SUPERSEDED_PREVIEW/ai/skills/task-intake"
printf '%s\n' '# Legacy fixture' > "$SUPERSEDED_PREVIEW/ai/skills/task-intake/SKILL.md"
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_PREVIEW" --source "$ROOT" --dry-run \
  > "$TMP_DIR/superseded-preview.out" 2>&1
assert_contains "$TMP_DIR/superseded-preview.out" 'Superseded paths to remove:'
assert_contains "$TMP_DIR/superseded-preview.out" 'ai/skills/task-intake'
assert_file "$SUPERSEDED_PREVIEW/ai/skills/task-intake/SKILL.md"

# Apply mode removes the superseded directory.
SUPERSEDED_APPLY="$TMP_DIR/superseded-apply-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_APPLY"
mkdir -p "$SUPERSEDED_APPLY/ai/skills/task-intake"
printf '%s\n' '# Legacy fixture' > "$SUPERSEDED_APPLY/ai/skills/task-intake/SKILL.md"
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_APPLY" --source "$ROOT" --apply --allow-dirty \
  > "$TMP_DIR/superseded-apply.out" 2>&1
assert_contains "$TMP_DIR/superseded-apply.out" 'Removed superseded path: ai/skills/task-intake'
assert_not_exists "$SUPERSEDED_APPLY/ai/skills/task-intake"

# A symlinked superseded path is refused, not followed.
SUPERSEDED_SYMLINK="$TMP_DIR/superseded-symlink-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_SYMLINK"
mkdir -p "$TMP_DIR/superseded-outside-dir"
printf '%s\n' 'MUST_NOT_BE_REMOVED' > "$TMP_DIR/superseded-outside-dir/SKILL.md"
ln -s "$TMP_DIR/superseded-outside-dir" "$SUPERSEDED_SYMLINK/ai/skills/task-intake"
if bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_SYMLINK" --source "$ROOT" --apply --allow-dirty \
  > "$TMP_DIR/superseded-symlink.out" 2>&1; then
  fail 'updater removed a symlinked superseded path'
fi
assert_contains "$TMP_DIR/superseded-symlink.out" 'superseded path must not be a symlink'
assert_file "$TMP_DIR/superseded-outside-dir/SKILL.md"

# A symlinked ANCESTOR directory is refused, not followed.
SUPERSEDED_ANCESTOR="$TMP_DIR/superseded-ancestor-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_ANCESTOR"
mkdir -p "$TMP_DIR/outsideandirectory-with-legacy"
printf '%s\n' '# Legacy fixture' > "$TMP_DIR/outsideandirectory-with-legacy/SKILL.md"
# Replace ai/skills with a symlink to outside directory
rm -rf "$SUPERSEDED_ANCESTOR/ai/skills"
ln -s "$TMP_DIR/outsideandirectory-with-legacy" "$SUPERSEDED_ANCESTOR/ai/skills"
mkdir -p "$SUPERSEDED_ANCESTOR/ai/skills/task-intake"
printf '%s\n' '# Legacy fixture' > "$SUPERSEDED_ANCESTOR/ai/skills/task-intake/SKILL.md"
if bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_ANCESTOR" --source "$ROOT" --apply --allow-dirty \
  > "$TMP_DIR/superseded-ancestor.out" 2>&1; then
  fail 'updater removed a superseded path through a symlinked ancestor'
fi
assert_contains "$TMP_DIR/superseded-ancestor.out" 'superseded path must not be a symlink'
assert_file "$TMP_DIR/outsideandirectory-with-legacy/SKILL.md"

# Empty rel entry is rejected before rm -rf by the real updater.
SUPERSEDED_EMPTY_HUB="$TMP_DIR/superseded-empty-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_EMPTY_HUB"
if SUPERSEDED_TEST_EMPTY=1 bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_EMPTY_HUB" --source "$ROOT" --apply --allow-dirty \
  > "$TMP_DIR/superseded-empty.out" 2>&1; then
  fail 'updater accepted an empty superseded path'
fi
assert_contains "$TMP_DIR/superseded-empty.out" 'superseded path must not be empty'
assert_file "$SUPERSEDED_EMPTY_HUB/ai/architecture.md"

for check_args in \
  "--check --apply" \
  "--apply --check" \
  "--check --commit" \
  "--commit --check"; do
  CHECK_HUB="$TMP_DIR/check-${check_args// /-}"
  cp -R "$HUB_INSTALL" "$CHECK_HUB"
  perl -0pi -e 's/Version: [0-9]+\.[0-9]+/Version: 0.1/' "$CHECK_HUB/ai/architecture.md"
  cp "$CHECK_HUB/AGENTS.md" "$TMP_DIR/check-agents.before"
  cp "$CHECK_HUB/ai/architecture.md" "$TMP_DIR/check-architecture.before"
  before_commit="$(git -C "$CHECK_HUB" rev-parse HEAD)"

  if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$CHECK_HUB" --source "$ROOT" --allow-dirty $check_args > "$TMP_DIR/check.out" 2>&1; then
    fail "$check_args should exit 1 when update is available"
  fi
  cmp -s "$TMP_DIR/check-agents.before" "$CHECK_HUB/AGENTS.md" || fail "$check_args changed AGENTS.md"
  cmp -s "$TMP_DIR/check-architecture.before" "$CHECK_HUB/ai/architecture.md" || fail "$check_args changed architecture"
  [ "$(git -C "$CHECK_HUB" rev-parse HEAD)" = "$before_commit" ] || fail "$check_args created a commit"
done

if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$ROOT" --apply > "$TMP_DIR/hub-dirty.out" 2>&1; then
  fail 'hub updater accepted a dirty tree without --allow-dirty'
fi
assert_contains "$TMP_DIR/hub-dirty.out" 'Working tree is not clean'

bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$ROOT" --apply --allow-dirty > "$TMP_DIR/hub-update.out"
cmp -s "$ROOT/hub-template/AGENTS.md" "$HUB_INSTALL/AGENTS.md" || fail 'hub update did not replace protected entry file'
cmp -s "$ROOT/scripts/check-hub-registry.sh" "$HUB_INSTALL/scripts/check-hub-registry.sh" || fail 'hub update did not replace protected validator'
cmp -s "$ROOT/scripts/read-compact-project-index.sh" "$HUB_INSTALL/scripts/read-compact-project-index.sh" || fail 'hub update did not replace compact project index reader'
cmp -s "$TMP_DIR/allowed-roots.before" "$HUB_INSTALL/ai/allowed-roots.md" || fail 'hub update overwrote allowed roots'
cmp -s "$TMP_DIR/registry.before" "$HUB_INSTALL/ai/project-registry.md" || fail 'hub update overwrote registry'
cmp -s "$TMP_DIR/active.before" "$HUB_INSTALL/ai/active-project.md" || fail 'hub update overwrote active project'
cmp -s "$TMP_DIR/card.before" "$HUB_INSTALL/ai/project-cards/custom.md" || fail 'hub update overwrote project card'
cmp -s "$TMP_DIR/signals.before" "$HUB_INSTALL/ai/cross-project-signals.md" || fail 'hub update overwrote cross-project signals'
cmp -s "$TMP_DIR/archive.before" "$HUB_INSTALL/ai/archive/custom.md" || fail 'hub update overwrote archive memory'
assert_file "$HUB_INSTALL/ai/archive/.gitkeep"
assert_file "$HUB_INSTALL/ai/project-cards/.gitkeep"

# A second apply has no missing memory templates. It must still complete under
# `set -u`; an empty updater array is not an error.
bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$ROOT" --apply --allow-dirty > "$TMP_DIR/hub-repeat-update.out"
assert_contains "$TMP_DIR/hub-repeat-update.out" 'Applied personal AI hub update.'

# The updater must guarantee the required ignore line without overwriting a
# hub .gitignore that carries the user's own entries (Audit 5).
printf '%s\n' '# user entry' '/scratch/' > "$HUB_INSTALL/.gitignore"
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$HUB_INSTALL" --source "$ROOT" --apply --allow-dirty > "$TMP_DIR/gitignore-update.out"
assert_contains "$HUB_INSTALL/.gitignore" '/projects/'
assert_contains "$HUB_INSTALL/.gitignore" '# user entry'
assert_contains "$HUB_INSTALL/.gitignore" '/scratch/'

# Running again must not duplicate the line.
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$HUB_INSTALL" --source "$ROOT" --apply --allow-dirty > "$TMP_DIR/gitignore-repeat.out"
[ "$(grep -Fxc '/projects/' "$HUB_INSTALL/.gitignore")" -eq 1 ] \
  || fail 'updater duplicated the /projects/ ignore line'
echo 'Gitignore evidence: required line ensured, user entries preserved, no duplication.'

HUB_COMMIT="$TMP_DIR/commit-hub/_ai-hub"
bash "$ROOT/scripts/install.sh" --mode hub "$HUB_COMMIT" >/dev/null
git -C "$HUB_COMMIT" config user.email "smoke@example.invalid"
git -C "$HUB_COMMIT" config user.name "Smoke Test"
git -C "$HUB_COMMIT" add .
git -C "$HUB_COMMIT" commit -m "test: install hub" >/dev/null
printf '%s\n' '# Project Registry' '' 'commit-safe registry' > "$HUB_COMMIT/ai/project-registry.md"
cp "$HUB_COMMIT/ai/project-registry.md" "$TMP_DIR/commit-registry.before"
COMMIT_SOURCE="$TMP_DIR/commit-source"
mkdir -p "$COMMIT_SOURCE/scripts"
cp -R "$ROOT/hub-template" "$COMMIT_SOURCE/hub-template"
cp "$ROOT/scripts/read-compact-project-index.sh" "$COMMIT_SOURCE/scripts/read-compact-project-index.sh"
printf '%s\n' '' '<!-- updater commit fixture -->' >> "$COMMIT_SOURCE/hub-template/AGENTS.md"
printf '%s\n' '# New Archive Template' > "$COMMIT_SOURCE/hub-template/ai/archive/new-template.md"
bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_COMMIT" --source "$COMMIT_SOURCE" --commit --allow-dirty > "$TMP_DIR/hub-commit.out"
cmp -s "$TMP_DIR/commit-registry.before" "$HUB_COMMIT/ai/project-registry.md" || fail 'hub commit overwrote registry'
assert_contains <(git -C "$HUB_COMMIT" show --format= --name-only HEAD) 'AGENTS.md'
assert_contains <(git -C "$HUB_COMMIT" show --format= --name-only HEAD) 'ai/archive/new-template.md'
assert_not_contains <(git -C "$HUB_COMMIT" show --format= --name-only HEAD) 'ai/project-registry.md'
[ "$(git -C "$HUB_COMMIT" log -1 --pretty=%s)" = 'chore: update personal AI hub' ] || fail 'unexpected hub update commit message'
git -C "$HUB_COMMIT" diff --quiet -- ai/project-registry.md && fail 'hub commit unexpectedly cleaned custom registry change'
git -C "$HUB_COMMIT" diff --cached --quiet || fail 'hub updater left staged changes after commit'

# Regression: --commit must stage, commit, and report removed superseded
# paths (Finding 1). Without the fix, UPDATE_PATHS never included the
# removed path, so the commit was skipped and the tree was left dirty.
COMMIT_REMOVAL_HUB="$TMP_DIR/commit-removal-hub/_ai-hub"
bash "$ROOT/scripts/install.sh" --mode hub "$COMMIT_REMOVAL_HUB" >/dev/null
git -C "$COMMIT_REMOVAL_HUB" config user.email "smoke@example.invalid"
git -C "$COMMIT_REMOVAL_HUB" config user.name "Smoke Test"
mkdir -p "$COMMIT_REMOVAL_HUB/ai/skills/task-intake"
printf '%s\n' '# Legacy fixture' > "$COMMIT_REMOVAL_HUB/ai/skills/task-intake/SKILL.md"
git -C "$COMMIT_REMOVAL_HUB" add .
git -C "$COMMIT_REMOVAL_HUB" commit -m "test: install hub with legacy skill" >/dev/null
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$COMMIT_REMOVAL_HUB" --source "$ROOT" --commit \
  > "$TMP_DIR/commit-removal.out"
assert_contains "$TMP_DIR/commit-removal.out" 'Removed 1 superseded path(s):'
assert_contains "$TMP_DIR/commit-removal.out" 'ai/skills/task-intake'
assert_not_exists "$COMMIT_REMOVAL_HUB/ai/skills/task-intake"
[ -z "$(git -C "$COMMIT_REMOVAL_HUB" status --porcelain)" ] \
  || fail 'commit did not stage/commit the removed superseded path, leaving the tree dirty'
assert_contains <(git -C "$COMMIT_REMOVAL_HUB" show --format= --name-only HEAD) 'ai/skills/task-intake/SKILL.md'

# Regression: --check must not report "up to date" while a stale superseded
# path is still present, even when the architecture version already matches
# (Finding 2).
STALE_CHECK_HUB="$TMP_DIR/stale-check-hub"
cp -R "$HUB_INSTALL" "$STALE_CHECK_HUB"
mkdir -p "$STALE_CHECK_HUB/ai/skills/task-intake"
printf '%s\n' '# Legacy fixture' > "$STALE_CHECK_HUB/ai/skills/task-intake/SKILL.md"
if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$STALE_CHECK_HUB" --source "$ROOT" --check \
  > "$TMP_DIR/stale-check.out" 2>&1; then
  fail '--check reported up to date while a stale superseded path remained'
fi
assert_contains "$TMP_DIR/stale-check.out" 'stale superseded paths remain'
assert_file "$STALE_CHECK_HUB/ai/skills/task-intake/SKILL.md"

# Regression: refuse to remove superseded paths when --source points at a
# template older than the version that introduced removal (Finding 3).
OLD_SOURCE="$TMP_DIR/old-source-hub"
mkdir -p "$OLD_SOURCE/scripts"
cp -R "$ROOT/hub-template" "$OLD_SOURCE/hub-template"
cp "$ROOT/scripts/read-compact-project-index.sh" "$OLD_SOURCE/scripts/read-compact-project-index.sh"
perl -0pi -e 's/Version: [0-9]+\.[0-9]+/Version: 1.2/' "$OLD_SOURCE/hub-template/ai/architecture.md"
mkdir -p "$OLD_SOURCE/hub-template/ai/skills/task-intake"
printf '%s\n' '# Legacy fixture' > "$OLD_SOURCE/hub-template/ai/skills/task-intake/SKILL.md"
OLD_SOURCE_HUB="$TMP_DIR/old-source-target-hub"
cp -R "$HUB_INSTALL" "$OLD_SOURCE_HUB"
mkdir -p "$OLD_SOURCE_HUB/ai/skills/task-intake"
printf '%s\n' '# Legacy fixture' > "$OLD_SOURCE_HUB/ai/skills/task-intake/SKILL.md"
if bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$OLD_SOURCE_HUB" --source "$OLD_SOURCE" --apply --allow-dirty \
  > "$TMP_DIR/old-source.out" 2>&1; then
  fail 'updater removed superseded paths using an older-than-1.3 source template'
fi
assert_contains "$TMP_DIR/old-source.out" 'refusing to delete hub skills'
assert_file "$OLD_SOURCE_HUB/ai/skills/task-intake/SKILL.md"
assert_file "$OLD_SOURCE_HUB/ai/skills/hub-project-router/SKILL.md"

# Regression: the source-version gate must run BEFORE any protected-file
# copying, so an old source template is refused before it can write
# anything to the hub (deferred Finding A). Without the fix, --apply copies
# AGENTS.md/CLAUDE.md/ai/architecture.md and only aborts afterward, leaving
# the hub partially downgraded.
GATE_ORDER_SOURCE="$TMP_DIR/gate-order-source"
mkdir -p "$GATE_ORDER_SOURCE/scripts"
cp -R "$ROOT/hub-template" "$GATE_ORDER_SOURCE/hub-template"
cp "$ROOT/scripts/read-compact-project-index.sh" "$GATE_ORDER_SOURCE/scripts/read-compact-project-index.sh"
perl -0pi -e 's/Version: [0-9]+\.[0-9]+/Version: 1.2/' "$GATE_ORDER_SOURCE/hub-template/ai/architecture.md"
printf '%s\n' '' '<!-- must never land in the hub: version gate ran too late -->' >> "$GATE_ORDER_SOURCE/hub-template/AGENTS.md"
GATE_ORDER_HUB="$TMP_DIR/gate-order-hub"
cp -R "$HUB_INSTALL" "$GATE_ORDER_HUB"
cp "$GATE_ORDER_HUB/AGENTS.md" "$TMP_DIR/gate-order-agents.before"
if bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$GATE_ORDER_HUB" --source "$GATE_ORDER_SOURCE" --apply --allow-dirty \
  > "$TMP_DIR/gate-order.out" 2>&1; then
  fail 'updater applied protected-file updates using an older-than-1.3 source template'
fi
assert_contains "$TMP_DIR/gate-order.out" 'refusing to delete hub skills'
cmp -s "$TMP_DIR/gate-order-agents.before" "$GATE_ORDER_HUB/AGENTS.md" \
  || fail 'version gate ran after copying protected files: AGENTS.md was overwritten before the refusal'

# Regression: superseded-path removal must validate every entry before
# deleting anything (deferred Finding B). Without the fix,
# remove_superseded_path validates and deletes in the same pass, so a valid
# entry earlier in SUPERSEDED_PATHS is already removed by the time a later
# invalid entry aborts the run.
ATOMIC_REMOVAL_HUB="$TMP_DIR/atomic-removal-hub"
cp -R "$HUB_INSTALL" "$ATOMIC_REMOVAL_HUB"
mkdir -p "$ATOMIC_REMOVAL_HUB/ai/skills/task-intake"
printf '%s\n' '# Legacy fixture' > "$ATOMIC_REMOVAL_HUB/ai/skills/task-intake/SKILL.md"
if SUPERSEDED_TEST_EMPTY=1 bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$ATOMIC_REMOVAL_HUB" --source "$ROOT" --apply --allow-dirty \
  > "$TMP_DIR/atomic-removal.out" 2>&1; then
  fail 'updater accepted an empty superseded path entry'
fi
assert_contains "$TMP_DIR/atomic-removal.out" 'superseded path must not be empty'
assert_file "$ATOMIC_REMOVAL_HUB/ai/skills/task-intake/SKILL.md"

# Regression: a superseded path value of exactly ".." (no slash) must be
# rejected by the traversal guard, not fall through to rm -rf on the hub's
# parent directory (Finding 4). Reuses the SUPERSEDED_TEST_* env hook
# pattern already used above for the empty-path regression.
DOTDOT_HUB="$TMP_DIR/dotdot-hub"
cp -R "$HUB_INSTALL" "$DOTDOT_HUB"
DOTDOT_SIBLING_MARKER="$TMP_DIR/dotdot-sibling-marker"
printf '%s\n' 'must survive' > "$DOTDOT_SIBLING_MARKER"
if SUPERSEDED_TEST_DOTDOT=1 bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$DOTDOT_HUB" --source "$ROOT" --apply --allow-dirty \
  > "$TMP_DIR/dotdot.out" 2>&1; then
  fail 'updater accepted a bare ".." superseded path'
fi
assert_contains "$TMP_DIR/dotdot.out" 'superseded path must be hub-relative without traversal'
assert_file "$DOTDOT_SIBLING_MARKER"
assert_file "$DOTDOT_HUB/ai/architecture.md"

assistant_workflow_source_valid "$ROOT/scripts/assistant-workflows.sh"
hub_workflows_rule_valid

echo "Hub smoke tests passed."
