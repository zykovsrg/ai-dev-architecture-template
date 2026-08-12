#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-hub-smoke.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_contains() { grep -Fq "$2" "$1" || fail "expected '$2' in $1"; }
assert_file() { [ -f "$1" ] || fail "missing file: $1"; }
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

THIRD_ACTIVATION="$TMP_DIR/entry-with-third-activation.md"
cp "$HUB_AGENTS" "$THIRD_ACTIVATION"
printf '%s\n' '<!-- Tool-specific activation: A third tool reads this entry differently. -->' >> "$THIRD_ACTIVATION"
assert_contains <(normalize_entry "$THIRD_ACTIVATION") \
  '<!-- Tool-specific activation: A third tool reads this entry differently. -->'

cmp -s <(normalize_entry "$HUB_AGENTS") <(normalize_entry "$HUB_CLAUDE") \
  || fail 'hub entry files differ beyond title and activation paragraph'

for skill in project-router project-switch project-register registry-check; do
  file="$ROOT/hub-template/ai/skills/$skill/SKILL.md"
  assert_file "$file"
  assert_contains "$file" 'name:'
  assert_contains "$file" 'description:'
  assert_contains "$file" 'explicit confirmation'
done

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
grep -Fq 'at least three stable independent areas' "$LOCAL" \
  || fail 'local-router threshold missing'
grep -Fq 'no separate current task' "$LOCAL" \
  || fail 'local-router task boundary missing'

SIGNALS="$ROOT/hub-template/ai/cross-project-signals.md"
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
assert_contains "$SWITCH_SKILL" 'task-intake'

REGISTER_SKILL="$ROOT/hub-template/ai/skills/project-register/SKILL.md"
assert_contains "$REGISTER_SKILL" 'direct child directory names only'
assert_contains "$REGISTER_SKILL" 'Never auto-register backups'
assert_contains "$REGISTER_SKILL" 'approval before reading project context'
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
mkdir -p "$VALID/ai/project-cards" "$TMP_DIR/projects/analytics-seo"
printf '%s\n' '# Allowed Roots' '' "- $TMP_DIR/projects" > "$VALID/ai/allowed-roots.md"
printf '%s\n' '# Project Registry' '' \
  '## analytics-seo' \
  'Name: SEO Analytics' \
  'Type: work' \
  'Status: active' \
  "Path: $TMP_DIR/projects/analytics-seo" \
  'Tags: seo, analytics, traffic, leads' \
  'Card: ai/project-cards/analytics-seo.md' > "$VALID/ai/project-registry.md"
printf '%s\n' '# SEO Analytics' '' 'Project ID: analytics-seo' > "$VALID/ai/project-cards/analytics-seo.md"

bash "$ROOT/scripts/check-hub-registry.sh" "$VALID" > "$TMP_DIR/valid.out"
assert_contains "$TMP_DIR/valid.out" 'Registry check passed'

INVALID="$TMP_DIR/invalid-hub"
cp -R "$VALID" "$INVALID"
sed "s#Path: $TMP_DIR/projects/analytics-seo#Path: $TMP_DIR/outside#" \
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

LEXICAL_ESCAPE="$TMP_DIR/lexical-escape-hub"
cp -R "$VALID" "$LEXICAL_ESCAPE"
sed "s#Path: $TMP_DIR/projects/analytics-seo#Path: $TMP_DIR/projects/../outside/missing#" \
  "$VALID/ai/project-registry.md" > "$LEXICAL_ESCAPE/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$LEXICAL_ESCAPE" > "$TMP_DIR/lexical-escape.out" 2>&1; then
  fail 'validator accepted a lexical path escape'
fi
assert_contains "$TMP_DIR/lexical-escape.out" 'outside allowed roots'

SYMLINK_ESCAPE="$TMP_DIR/symlink-escape-hub"
mkdir -p "$TMP_DIR/outside"
ln -s "$TMP_DIR/outside" "$TMP_DIR/projects/link-out"
cp -R "$VALID" "$SYMLINK_ESCAPE"
sed "s#Path: $TMP_DIR/projects/analytics-seo#Path: $TMP_DIR/projects/link-out/missing#" \
  "$VALID/ai/project-registry.md" > "$SYMLINK_ESCAPE/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$SYMLINK_ESCAPE" > "$TMP_DIR/symlink-escape.out" 2>&1; then
  fail 'validator accepted a symlink component escape'
fi
assert_contains "$TMP_DIR/symlink-escape.out" 'outside allowed roots'

MISSING_PROJECT="$TMP_DIR/missing-project-hub"
cp -R "$VALID" "$MISSING_PROJECT"
sed -e 's/Status: active/Status: missing/' \
  -e "s#Path: $TMP_DIR/projects/analytics-seo#Path: $TMP_DIR/projects/genuinely-missing#" \
  "$VALID/ai/project-registry.md" > "$MISSING_PROJECT/ai/project-registry.md"
bash "$ROOT/scripts/check-hub-registry.sh" "$MISSING_PROJECT" > "$TMP_DIR/missing-project.out"
assert_contains "$TMP_DIR/missing-project.out" 'Registry check passed'
