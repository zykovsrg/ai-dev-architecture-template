#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-hub-smoke.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_contains() { grep -Fq "$2" "$1" || fail "expected '$2' in $1"; }
assert_not_contains() { ! grep -Fq "$2" "$1" || fail "did not expect '$2' in $1"; }
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
generate_registry() {
  local hub="$1" root="$2" count="$3" i id
  printf '%s\n' '# Project Registry' > "$hub/ai/project-registry.md"
  i=1
  while [ "$i" -le "$count" ]; do
    id="fixture-project-$i"
    mkdir -p "$root/$id"
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

  [[ "$section" == *'ai/cross-project-signals.md'* ]] &&
    [[ "$section" == *'name one of the candidates'* ]] &&
    [[ "$section" == *'active/relevant'* ]] &&
    [[ "$section" == *'Do not read project memory, source code'* ]] &&
    [[ "$section" != *'Do not read cross-project signals'* ]]
}
router_staged_signal_reads_valid() {
  local section step_one step_two step_four
  section="$(section_text "$1" '## Read allowlist and phases' '## Required response shape')"
  step_one="$(printf '%s\n' "$section" | awk '/^1\. /{in_step=1} in_step && /^2\. /{exit} in_step{print}')"
  step_two="$(printf '%s\n' "$section" | awk '/^2\. /{in_step=1} in_step && /^3\. /{exit} in_step{print}')"
  step_four="$(printf '%s\n' "$section" | awk '/^4\. /{in_step=1} in_step && /^5\. /{exit} in_step{print}')"

  [[ "$step_one" == *'compact hub index only'* ]] &&
    [[ "$step_one" == *'active-project.md'* ]] &&
    [[ "$step_one" != *'cross-project-signals.md'* ]] &&
    [[ "$step_two" == *'maximum of three candidates'* ]] &&
    [[ "$step_four" == *'only related active signals'* ]] &&
    [[ "$step_four" == *'name one of the candidates'* ]]
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

  [[ "$section" == *'ai/allowed-roots.md'*'ai/project-registry.md'*'ai/active-project.md'*'up to three candidate cards'*'related active signals'* ]]
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

  [[ "$text" == *'separate confirmed `project-switch` between project groups'* ]] &&
    [[ "$text" == *'resume `info-update` only after that switch'* ]] &&
    [[ "$text" == *'must not invoke or perform `project-switch`'* ]]
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
    [[ "$text" == *'hub-owned `environment-check`'* ]] &&
    [[ "$text" == *'hub-owned `task-intake`'* ]] &&
    [[ "$text" == *'unsafe project names'* ]] &&
    [[ "$text" == *'Git repositories must not be created or modified'* ]] &&
    [[ "$text" == *'must not add application code, dependencies, services, AGENTS.md, CLAUDE.md, or shared skills'* ]]
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

  if ! bash "$ROOT/scripts/install.sh" --mode hub "$portable_hub" > "$install_out" 2>&1; then
    fail 'portable hub install without --root was rejected'
  fi
  assert_file "$portable_hub/projects/.gitkeep"
  assert_contains "$portable_hub/.gitignore" '/projects/'
  [ "$(grep -Fxc -- "- $portable_hub/projects" "$portable_hub/ai/allowed-roots.md")" -eq 1 ] \
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
grep -Fq 'allowed roots' "$HUB_AGENTS" || fail 'missing allowed-root gate'
grep -Fq 'explicit confirmation' "$HUB_CLAUDE" || fail 'missing confirmation gate'
grep -Fq 'allowed roots' "$HUB_CLAUDE" || fail 'missing allowed-root gate'
hub_entry_staged_allowlist_valid "$HUB_AGENTS" \
  || fail 'hub entry must match staged router reads: index, up to three cards, then related active signals'
assert_contains "$HUB_AGENTS" 'ai/architecture.md'
assert_not_contains "$HUB_AGENTS" 'hub-template/ai/architecture.md'

portable_hub_install_contract

THIRD_ACTIVATION="$TMP_DIR/entry-with-third-activation.md"
cp "$HUB_AGENTS" "$THIRD_ACTIVATION"
printf '%s\n' '<!-- Tool-specific activation: A third tool reads this entry differently. -->' >> "$THIRD_ACTIVATION"
assert_contains <(normalize_entry "$THIRD_ACTIVATION") \
  '<!-- Tool-specific activation: A third tool reads this entry differently. -->'

cmp -s <(normalize_entry "$HUB_AGENTS") <(normalize_entry "$HUB_CLAUDE") \
  || fail 'hub entry files differ beyond title and activation paragraph'

for skill in project-router project-switch project-register project-create project-migrate registry-check environment-check task-intake task-switch task-finish; do
  file="$ROOT/hub-template/ai/skills/$skill/SKILL.md"
  assert_file "$file"
  assert_contains "$file" 'name:'
  assert_contains "$file" 'description:'
  assert_contains "$file" 'explicit confirmation'
done

PROJECT_CREATE_SKILL="$ROOT/hub-template/ai/skills/project-create/SKILL.md"
project_create_contract_valid "$PROJECT_CREATE_SKILL" \
  || fail 'project-create must define the confirmation-gated creation contract'

PROJECT_CREATE_WITHOUT_UNSAFE_NAMES="$TMP_DIR/project-create-without-unsafe-name-guard.md"
sed '/unsafe project names/d' "$PROJECT_CREATE_SKILL" > "$PROJECT_CREATE_WITHOUT_UNSAFE_NAMES"
assert_rejected project_create_contract_valid "$PROJECT_CREATE_WITHOUT_UNSAFE_NAMES"

PROJECT_CREATE_WITHOUT_GIT_GUARANTEE="$TMP_DIR/project-create-without-git-guarantee.md"
sed '/Git repositories must not be created or modified/d' "$PROJECT_CREATE_SKILL" \
  > "$PROJECT_CREATE_WITHOUT_GIT_GUARANTEE"
assert_rejected project_create_contract_valid "$PROJECT_CREATE_WITHOUT_GIT_GUARANTEE"

for workflow in environment-check task-intake task-switch task-finish; do
  hub_shared_workflow_valid "$ROOT/hub-template/ai/skills/$workflow/SKILL.md" "$workflow" \
    || fail "shared hub workflow must preserve post-confirmation and memory-isolation gates: $workflow"
done

HUB_ARCHITECTURE="$ROOT/hub-template/ai/architecture.md"
hub_architecture_security_precedence_valid "$HUB_ARCHITECTURE" \
  || fail 'hub security and routing rules must outrank all project content'

INFO="$ROOT/hub-template/ai/skills/info-update/SKILL.md"
LOCAL="$ROOT/hub-template/ai/skills/local-router-install/SKILL.md"
assert_file "$INFO"
assert_file "$LOCAL"
grep -Fq 'Do not save the source transcript by default' "$INFO" \
  || fail 'transcript retention gate missing'
grep -Fq 'Confirm each affected project separately' "$INFO" \
  || fail 'per-project approval missing'
grep -Fq 'must not replace the current task' "$INFO" \
  || fail 'current-task protection missing'
grep -Fq 'MUST NOT invoke or perform `task-finish`' "$INFO" \
  || fail 'info-update task-finish ban missing'
grep -Fq 'MUST NOT invoke or perform `project-switch`' "$INFO" \
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

ROUTER_SKILL="$ROOT/hub-template/ai/skills/project-router/SKILL.md"
assert_contains "$ROUTER_SKILL" 'maximum of three candidates'
assert_contains "$ROUTER_SKILL" 'high, medium, or low'
assert_contains "$ROUTER_SKILL" 'read only candidate cards'
assert_contains "$ROUTER_SKILL" 'wait for explicit confirmation'
router_read_boundary_valid "$ROUTER_SKILL" \
  || fail 'router must allow only relevant hub cross-project signals and forbid project memory/code before confirmation'
router_staged_signal_reads_valid "$ROUTER_SKILL" \
  || fail 'router must stage cross-project signal reads after candidate selection'
router_multiple_candidates_template_valid "$ROUTER_SKILL" \
  || fail 'router multi-candidate template must include confidence for all three candidate slots'

ROUTER_WITHOUT_SIGNALS="$TMP_DIR/router-without-signals.md"
sed '/ai\/cross-project-signals\.md/d' "$ROUTER_SKILL" > "$ROUTER_WITHOUT_SIGNALS"
assert_rejected router_read_boundary_valid "$ROUTER_WITHOUT_SIGNALS"

ROUTER_WITHOUT_THIRD_SLOT="$TMP_DIR/router-without-third-slot.md"
sed '/3\. <project-id-3>/d' "$ROUTER_SKILL" > "$ROUTER_WITHOUT_THIRD_SLOT"
assert_rejected router_multiple_candidates_template_valid "$ROUTER_WITHOUT_THIRD_SLOT"

SWITCH_SKILL="$ROOT/hub-template/ai/skills/project-switch/SKILL.md"
assert_contains "$SWITCH_SKILL" 'must not modify the current task'
assert_contains "$SWITCH_SKILL" 'canonical path validation'
SWITCH_TEXT="$(tr '\n' ' ' < "$SWITCH_SKILL" | tr -s ' ')"
[[ "$SWITCH_TEXT" == *'hub-owned `environment-check`'* ]] \
  || fail 'project-switch must invoke hub-owned environment-check'
[[ "$SWITCH_TEXT" == *'hub-owned `task-intake`'* ]] \
  || fail 'project-switch must invoke hub-owned task-intake'
assert_not_contains "$SWITCH_SKILL" 'project entry instructions'

REGISTER_SKILL="$ROOT/hub-template/ai/skills/project-register/SKILL.md"
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

REGISTER_WITH_EARLY_GIT="$TMP_DIR/register-with-early-git.md"
awk '
  /^## After individual project confirmation$/ && !injected {
    print "Primary inventory must not inspect .git before confirmation."
    injected = 1
  }
  { print }
' "$REGISTER_SKILL" > "$REGISTER_WITH_EARLY_GIT"
assert_rejected registration_primary_inventory_valid "$REGISTER_WITH_EARLY_GIT"

CHECK_SKILL="$ROOT/hub-template/ai/skills/registry-check/SKILL.md"
assert_contains "$CHECK_SKILL" 'read-only until approval'
assert_contains "$CHECK_SKILL" 'scripts/check-hub-registry.sh'
assert_contains "$CHECK_SKILL" 'cannot invoke it automatically'

VALID="$TMP_DIR/valid-hub"
mkdir -p "$VALID/ai/project-cards" "$VALID/projects/analytics-seo"
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
printf '%s\n' '# Project Card' '' \
  'Project ID: analytics-seo' \
  'Name: SEO Analytics' \
  'Type: work' \
  'Status: active' \
  'Last updated: 2026-08-12' \
  'Purpose: Analyze SEO reporting.' \
  'Typical tasks: Review analytics and reporting.' \
  "Memory entry point: $VALID/projects/analytics-seo/ai/current-task.md" > "$VALID/ai/project-cards/analytics-seo.md"

bash -x "$ROOT/scripts/check-hub-registry.sh" "$VALID" > "$TMP_DIR/valid.out" 2> "$TMP_DIR/valid.trace"
assert_contains "$TMP_DIR/valid.out" 'Registry check passed'
assert_contains "$TMP_DIR/valid.out" '1 projects'
assert_not_contains "$TMP_DIR/valid.out" "$SENTINEL"
assert_not_contains "$TMP_DIR/valid.trace" "$SENTINEL"
assert_forbidden_reads_absent "$TMP_DIR/valid.trace" \
  '/.env' '/credentials.txt' '/unregistered-project/private.txt' '/analytics-seo-backup/private.txt'
echo 'Sentinel evidence: validator output and xtrace contain neither the marker nor the named forbidden file paths.'

SENTINEL_CARD="$TMP_DIR/card-sentinel.md"
printf '%s\n' '# External Card' '' 'Project ID: analytics-seo' "$SENTINEL" > "$SENTINEL_CARD"

for card_escape_case in lexical symlink canonical; do
  escaped_hub="$TMP_DIR/card-$card_escape_case-hub"
  cp -R "$VALID" "$escaped_hub"
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
    "$VALID/ai/project-registry.md" > "$escaped_hub/ai/project-registry.md"

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
  cp -R "$VALID" "$missing_field"
  sed "/^$required_field: /d" "$VALID/ai/project-registry.md" > "$missing_field/ai/project-registry.md"
  if bash "$ROOT/scripts/check-hub-registry.sh" "$missing_field" > "$TMP_DIR/missing-$required_field.out" 2>&1; then
    fail "validator accepted an entry without $required_field"
  fi
  assert_contains "$TMP_DIR/missing-$required_field.out" "missing $required_field"
done

for required_card_field in 'Project ID' Name Type Status 'Last updated' Purpose 'Typical tasks' 'Memory entry point'; do
  missing_card_field="$TMP_DIR/missing-card-${required_card_field// /-}-hub"
  cp -R "$VALID" "$missing_card_field"
  sed "/^$required_card_field: /d" "$VALID/ai/project-cards/analytics-seo.md" \
    > "$missing_card_field/ai/project-cards/analytics-seo.md"
  if bash "$ROOT/scripts/check-hub-registry.sh" "$missing_card_field" > "$TMP_DIR/missing-card-${required_card_field// /-}.out" 2>&1; then
    fail "validator accepted a card without $required_card_field"
  fi
  assert_contains "$TMP_DIR/missing-card-${required_card_field// /-}.out" "missing card $required_card_field"
done

CARD_MISMATCH="$TMP_DIR/card-mismatch-hub"
cp -R "$VALID" "$CARD_MISMATCH"
sed 's/^Project ID: analytics-seo$/Project ID: another-project/' \
  "$VALID/ai/project-cards/analytics-seo.md" > "$CARD_MISMATCH/ai/project-cards/analytics-seo.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$CARD_MISMATCH" > "$TMP_DIR/card-mismatch.out" 2>&1; then
  fail 'validator accepted a card with a different Project ID'
fi
assert_contains "$TMP_DIR/card-mismatch.out" 'card Project ID mismatch'

CARD_STATUS_MISMATCH="$TMP_DIR/card-status-mismatch-hub"
cp -R "$VALID" "$CARD_STATUS_MISMATCH"
sed 's/^Status: active$/Status: paused/' "$VALID/ai/project-cards/analytics-seo.md" \
  > "$CARD_STATUS_MISMATCH/ai/project-cards/analytics-seo.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$CARD_STATUS_MISMATCH" > "$TMP_DIR/card-status-mismatch.out" 2>&1; then
  fail 'validator accepted a card with a different Status'
fi
assert_contains "$TMP_DIR/card-status-mismatch.out" 'card Status mismatch'

UNSAFE_MEMORY_ENTRY="$TMP_DIR/unsafe-memory-entry-hub"
cp -R "$VALID" "$UNSAFE_MEMORY_ENTRY"
sed "s#^Memory entry point: .*#Memory entry point: $TMP_DIR/outside/ai/current-task.md#" \
  "$VALID/ai/project-cards/analytics-seo.md" > "$UNSAFE_MEMORY_ENTRY/ai/project-cards/analytics-seo.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$UNSAFE_MEMORY_ENTRY" > "$TMP_DIR/unsafe-memory-entry.out" 2>&1; then
  fail 'validator accepted a memory entry point outside the registered project ai directory'
fi
assert_contains "$TMP_DIR/unsafe-memory-entry.out" 'card Memory entry point must stay beneath the registered project ai directory'

DUPLICATE_MEMORY_ENTRY="$TMP_DIR/duplicate-memory-entry-hub"
cp -R "$VALID" "$DUPLICATE_MEMORY_ENTRY"
printf '%s\n' "Memory entry point: $TMP_DIR/outside/ai/current-task.md" >> "$DUPLICATE_MEMORY_ENTRY/ai/project-cards/analytics-seo.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$DUPLICATE_MEMORY_ENTRY" > "$TMP_DIR/duplicate-memory-entry.out" 2>&1; then
  fail 'validator accepted a duplicate Memory entry point field'
fi
assert_contains "$TMP_DIR/duplicate-memory-entry.out" 'duplicate card Memory entry point:'

INVALID="$TMP_DIR/invalid-hub"
cp -R "$VALID" "$INVALID"
sed "s#Path: $VALID/projects/analytics-seo#Path: $TMP_DIR/outside#" \
  "$VALID/ai/project-registry.md" > "$INVALID/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$INVALID" > "$TMP_DIR/invalid.out" 2>&1; then
  fail 'validator accepted project outside allowed roots'
fi
assert_contains "$TMP_DIR/invalid.out" 'outside allowed roots'

MISSING_ROOT="$TMP_DIR/missing-root-hub"
cp -R "$VALID" "$MISSING_ROOT"
printf '%s\n' '# Allowed Roots' '' "- $TMP_DIR/does-not-exist" > "$MISSING_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$MISSING_ROOT" > "$TMP_DIR/missing-root.out" 2>&1; then
  fail 'validator accepted a nonexistent allowed root'
fi
assert_contains "$TMP_DIR/missing-root.out" 'allowed root does not exist'

RELATIVE_ROOT="$TMP_DIR/relative-root-hub"
cp -R "$VALID" "$RELATIVE_ROOT"
printf '%s\n' '# Allowed Roots' '' '- relative/projects' > "$RELATIVE_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$RELATIVE_ROOT" > "$TMP_DIR/relative-root.out" 2>&1; then
  fail 'validator accepted a relative allowed root'
fi
assert_contains "$TMP_DIR/relative-root.out" 'allowed root must be a nonempty absolute path'

EMPTY_ROOT="$TMP_DIR/empty-root-hub"
cp -R "$VALID" "$EMPTY_ROOT"
printf '%s\n' '# Allowed Roots' '' '- ' > "$EMPTY_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$EMPTY_ROOT" > "$TMP_DIR/empty-root.out" 2>&1; then
  fail 'validator accepted an empty allowed root'
fi
assert_contains "$TMP_DIR/empty-root.out" 'allowed root must be a nonempty absolute path'

ROOT_FILESYSTEM="$TMP_DIR/root-filesystem-hub"
cp -R "$VALID" "$ROOT_FILESYSTEM"
printf '%s\n' '# Allowed Roots' '' '- /' > "$ROOT_FILESYSTEM/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ROOT_FILESYSTEM" > "$TMP_DIR/root-filesystem.out" 2>&1; then
  fail 'validator accepted filesystem root as an allowed root'
fi
assert_contains "$TMP_DIR/root-filesystem.out" 'ERROR: allowed root must not be /'

ROOT_DOUBLE_SLASH="$TMP_DIR/root-double-slash-hub"
cp -R "$VALID" "$ROOT_DOUBLE_SLASH"
printf '%s\n' '# Allowed Roots' '' '- //' > "$ROOT_DOUBLE_SLASH/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ROOT_DOUBLE_SLASH" > "$TMP_DIR/root-double-slash.out" 2>&1; then
  fail 'validator accepted // as an allowed root'
fi
assert_contains "$TMP_DIR/root-double-slash.out" 'allowed root must not be /'

ROOT_SYMLINK_FILESYSTEM="$TMP_DIR/root-symlink-filesystem-hub"
ln -s / "$TMP_DIR/filesystem-root-link"
cp -R "$VALID" "$ROOT_SYMLINK_FILESYSTEM"
printf '%s\n' '# Allowed Roots' '' "- $TMP_DIR/filesystem-root-link" > "$ROOT_SYMLINK_FILESYSTEM/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ROOT_SYMLINK_FILESYSTEM" > "$TMP_DIR/root-symlink-filesystem.out" 2>&1; then
  fail 'validator accepted a symlink resolving to filesystem root'
fi
assert_contains "$TMP_DIR/root-symlink-filesystem.out" 'allowed root must not be /'

HOME_ROOT="$(cd "$HOME" && pwd -P)"
HOME_ALLOWED_ROOT="$TMP_DIR/home-allowed-root-hub"
cp -R "$VALID" "$HOME_ALLOWED_ROOT"
printf '%s\n' '# Allowed Roots' '' "- $HOME_ROOT" > "$HOME_ALLOWED_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$HOME_ALLOWED_ROOT" > "$TMP_DIR/home-allowed-root.out" 2>&1; then
  fail 'validator accepted the home directory as an allowed root'
fi
assert_contains "$TMP_DIR/home-allowed-root.out" 'allowed root must not be the home directory'

LEXICAL_ESCAPE="$TMP_DIR/lexical-escape-hub"
cp -R "$VALID" "$LEXICAL_ESCAPE"
sed "s#Path: $VALID/projects/analytics-seo#Path: $TMP_DIR/projects/../outside/missing#" \
  "$VALID/ai/project-registry.md" > "$LEXICAL_ESCAPE/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$LEXICAL_ESCAPE" > "$TMP_DIR/lexical-escape.out" 2>&1; then
  fail 'validator accepted a lexical path escape'
fi
assert_contains "$TMP_DIR/lexical-escape.out" 'outside allowed roots'

SYMLINK_ESCAPE="$TMP_DIR/symlink-escape-hub"
mkdir -p "$TMP_DIR/outside"
ln -s "$TMP_DIR/outside" "$TMP_DIR/projects/link-out"
cp -R "$VALID" "$SYMLINK_ESCAPE"
sed "s#Path: $VALID/projects/analytics-seo#Path: $TMP_DIR/projects/link-out/missing#" \
  "$VALID/ai/project-registry.md" > "$SYMLINK_ESCAPE/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$SYMLINK_ESCAPE" > "$TMP_DIR/symlink-escape.out" 2>&1; then
  fail 'validator accepted a symlink component escape'
fi
assert_contains "$TMP_DIR/symlink-escape.out" 'outside allowed roots'

MISSING_PROJECT="$TMP_DIR/missing-project-hub"
cp -R "$VALID" "$MISSING_PROJECT"
sed -e 's/Status: active/Status: missing/' \
  -e "s#Path: $VALID/projects/analytics-seo#Path: $TMP_DIR/projects/genuinely-missing#" \
  "$VALID/ai/project-registry.md" > "$MISSING_PROJECT/ai/project-registry.md"
sed -e 's/^Status: active$/Status: missing/' \
  -e "s#^Memory entry point: $VALID/projects/analytics-seo/#Memory entry point: $TMP_DIR/projects/genuinely-missing/#" \
  "$VALID/ai/project-cards/analytics-seo.md" \
  > "$MISSING_PROJECT/ai/project-cards/analytics-seo.md"
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
assert_file "$HUB_INSTALL/scripts/check-hub-registry.sh"
assert_file "$HUB_INSTALL/projects/.gitkeep"
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

INCOMPLETE_HUB_SOURCE="$TMP_DIR/incomplete-hub-source"
cp -R "$ROOT/hub-template" "$INCOMPLETE_HUB_SOURCE"
rm "$INCOMPLETE_HUB_SOURCE/ai/skills/project-router/SKILL.md"
if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$INCOMPLETE_HUB_SOURCE" --dry-run > "$TMP_DIR/incomplete-hub-source.out" 2>&1; then
  fail 'hub updater accepted a source without a mandatory hub skill'
fi
assert_contains "$TMP_DIR/incomplete-hub-source.out" 'missing mandatory hub skill: project-router'

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

bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$ROOT" --dry-run > "$TMP_DIR/hub-dry-run.out"
assert_contains "$TMP_DIR/hub-dry-run.out" '### AGENTS.md'
assert_contains "$TMP_DIR/hub-dry-run.out" 'Would create missing hub memory file without overwriting hub memory: ai/archive/.gitkeep'
assert_contains "$TMP_DIR/hub-dry-run.out" 'Would create missing hub memory file without overwriting hub memory: ai/project-cards/.gitkeep'
assert_not_exists "$HUB_INSTALL/ai/archive/.gitkeep"
assert_not_exists "$HUB_INSTALL/ai/project-cards/.gitkeep"

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
cmp -s "$TMP_DIR/allowed-roots.before" "$HUB_INSTALL/ai/allowed-roots.md" || fail 'hub update overwrote allowed roots'
cmp -s "$TMP_DIR/registry.before" "$HUB_INSTALL/ai/project-registry.md" || fail 'hub update overwrote registry'
cmp -s "$TMP_DIR/active.before" "$HUB_INSTALL/ai/active-project.md" || fail 'hub update overwrote active project'
cmp -s "$TMP_DIR/card.before" "$HUB_INSTALL/ai/project-cards/custom.md" || fail 'hub update overwrote project card'
cmp -s "$TMP_DIR/signals.before" "$HUB_INSTALL/ai/cross-project-signals.md" || fail 'hub update overwrote cross-project signals'
cmp -s "$TMP_DIR/archive.before" "$HUB_INSTALL/ai/archive/custom.md" || fail 'hub update overwrote archive memory'
assert_file "$HUB_INSTALL/ai/archive/.gitkeep"
assert_file "$HUB_INSTALL/ai/project-cards/.gitkeep"

HUB_COMMIT="$TMP_DIR/commit-hub/_ai-hub"
bash "$ROOT/scripts/install.sh" --mode hub "$HUB_COMMIT" >/dev/null
git -C "$HUB_COMMIT" config user.email "smoke@example.invalid"
git -C "$HUB_COMMIT" config user.name "Smoke Test"
git -C "$HUB_COMMIT" add .
git -C "$HUB_COMMIT" commit -m "test: install hub" >/dev/null
printf '%s\n' '# Project Registry' '' 'commit-safe registry' > "$HUB_COMMIT/ai/project-registry.md"
cp "$HUB_COMMIT/ai/project-registry.md" "$TMP_DIR/commit-registry.before"
COMMIT_SOURCE="$TMP_DIR/commit-source"
cp -R "$ROOT/hub-template" "$COMMIT_SOURCE"
printf '%s\n' '' '<!-- updater commit fixture -->' >> "$COMMIT_SOURCE/AGENTS.md"
printf '%s\n' '# New Archive Template' > "$COMMIT_SOURCE/ai/archive/new-template.md"
bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_COMMIT" --source "$COMMIT_SOURCE" --commit --allow-dirty > "$TMP_DIR/hub-commit.out"
cmp -s "$TMP_DIR/commit-registry.before" "$HUB_COMMIT/ai/project-registry.md" || fail 'hub commit overwrote registry'
assert_contains <(git -C "$HUB_COMMIT" show --format= --name-only HEAD) 'AGENTS.md'
assert_contains <(git -C "$HUB_COMMIT" show --format= --name-only HEAD) 'ai/archive/new-template.md'
assert_not_contains <(git -C "$HUB_COMMIT" show --format= --name-only HEAD) 'ai/project-registry.md'
[ "$(git -C "$HUB_COMMIT" log -1 --pretty=%s)" = 'chore: update personal AI hub' ] || fail 'unexpected hub update commit message'
git -C "$HUB_COMMIT" diff --quiet -- ai/project-registry.md && fail 'hub commit unexpectedly cleaned custom registry change'
git -C "$HUB_COMMIT" diff --cached --quiet || fail 'hub updater left staged changes after commit'

echo "Hub smoke tests passed."
