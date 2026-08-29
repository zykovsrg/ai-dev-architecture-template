#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-dev-arch-smoke.XXXXXX")"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_file() {
  [ -f "$1" ] || fail "missing file: $1"
}

assert_dir() {
  [ -d "$1" ] || fail "missing directory: $1"
}

assert_contains() {
  local file="$1"
  local pattern="$2"
  grep -Fq -- "$pattern" "$file" || fail "expected '$pattern' in $file"
}

assert_not_contains() {
  local file="$1"
  local needle="$2"
  if grep -Fq -- "$needle" "$file"; then
    fail "$file unexpectedly contains: $needle"
  fi
}

assert_not_exists() {
  [ ! -e "$1" ] || fail "expected path to be absent: $1"
}

assert_rejected() {
  if "$@"; then
    fail "knowledge contract validator accepted an intentionally unsafe fixture"
  fi
}

knowledge_path_boundary_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  [[ "$text" == *'canonical project root'* ]] &&
    [[ "$text" == *'Reject absolute paths and any path containing a `..` segment'* ]] &&
    [[ "$text" == *'Inspect every existing path component with `lstat`'* ]] &&
    [[ "$text" == *'reject any symlink component without following it'* ]] &&
    [[ "$text" == *'canonical `knowledge/` tree'* ]]
}

knowledge_capture_contract_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  knowledge_path_boundary_valid "$file" &&
    [[ "$text" == *'explicit `origin` choice'* ]] &&
    [[ "$text" == *'must not default to `stated`'* ]] &&
    [[ "$text" == *'origin: observation'* ]] &&
    [[ "$text" == *'knowledge/inbox/'* ]] &&
    [[ "$text" == *'The canonical target must remain beneath the directory mapped from the selected type'* ]] &&
    [[ "$text" == *'personal data or client data'* ]] &&
    [[ "$text" == *'without echoing the rejected value'* ]] &&
    [[ "$text" == *'Never delete a stale or superseded record'* ]] &&
    [[ "$text" == *'link to its replacement'* ]]
}

knowledge_review_contract_valid() {
  local file="$1" text
  text="$(tr '\n' ' ' < "$file" | tr -s ' ')"

  knowledge_path_boundary_valid "$file" &&
    [[ "$text" == *'`origin`'* ]] &&
    [[ "$text" == *'`valid_from`'* ]] &&
    [[ "$text" == *'origin: inferred'* ]] &&
    [[ "$text" == *'observation outside the inbox'* ]] &&
    [[ "$text" == *'required frontmatter keys: `type`, `status`, `origin`, `valid_from`, `created`, `reviewed`, and `sources`'* ]] &&
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

init_git_project() {
  local project="$1"
  mkdir -p "$project"
  git -C "$project" init >/dev/null
  git -C "$project" config user.email "smoke@example.invalid"
  git -C "$project" config user.name "Smoke Test"
}

echo "Smoke test workspace: $TMP_DIR"

bash "$ROOT/scripts/check-consistency.sh" > "$TMP_DIR/consistency.out"
assert_contains "$TMP_DIR/consistency.out" 'OK [standalone canonical blocks]'
assert_contains "$TMP_DIR/consistency.out" 'OK [hub entry parity]'
assert_contains "$TMP_DIR/consistency.out" 'OK [hub skill references] — 17 declared skills exist'
assert_contains "$TMP_DIR/consistency.out" 'OK [hub update classes]'
assert_contains "$TMP_DIR/consistency.out" 'OK [standalone memory updater boundaries]'
assert_contains "$TMP_DIR/consistency.out" 'OK [hub skill naming]'

# Regression: [hub skill naming] must actually catch an unnamed skill, and its
# backtick-delimited match must not let a longer existing name (hub-project-router,
# hub-project-create, hub-project-migrate, hub-project-register, hub-project-switch)
# falsely credit a same-prefix probe (hub-project) that no rule file names on its own.
NAMING_PROBE_UNNAMED="hub-template/ai/skills/hub-naming-probe-unnamed"
NAMING_PROBE_PREFIX="hub-template/ai/skills/hub-project"
naming_probe_cleanup() {
  rm -rf "$ROOT/$NAMING_PROBE_UNNAMED" "$ROOT/$NAMING_PROBE_PREFIX"
}
trap 'naming_probe_cleanup; cleanup' EXIT
mkdir -p "$ROOT/$NAMING_PROBE_UNNAMED" "$ROOT/$NAMING_PROBE_PREFIX"

set +e
(cd "$ROOT" && bash scripts/check-consistency.sh) > "$TMP_DIR/naming-probe.out" 2>&1
naming_probe_status=$?
set -e

naming_probe_cleanup
trap cleanup EXIT

[ "$naming_probe_status" -ne 0 ] || fail "[hub skill naming] should fail with an unnamed skill present"
assert_contains "$TMP_DIR/naming-probe.out" 'UNNAMED [hub skill naming] — hub-naming-probe-unnamed is named in no hub rule file'
assert_contains "$TMP_DIR/naming-probe.out" 'UNNAMED [hub skill naming] — hub-project is named in no hub rule file'

assert_contains "$ROOT/scripts/check-consistency.sh" 'extract_block "$standalone_base/AGENTS.md" canon:controlled-memory'
assert_contains "$ROOT/scripts/check-consistency.sh" 'hub architecture absent'
assert_contains "$ROOT/README.md" 'Personal hub'
assert_contains "$ROOT/README.md" 'Обычная архитектура для одного проекта'
assert_contains "$ROOT/README.md" 'единая точка входа'
assert_contains "$ROOT/docs/install.md" '--mode hub'
assert_contains "$ROOT/docs/update.md" 'update-installed-hub.sh'
assert_contains "$ROOT/docs/file-roles.md" 'Hub-managed project memory'
assert_contains "$ROOT/template/ai/current-task.md" 'Task ID: TASK-YYYYMMDD-NNN'
assert_contains "$ROOT/template/ai/paused-tasks.md" 'Task ID: TASK-YYYYMMDD-NNN'
# The paused template must show the exact field order the renderer and the
# confirmed rename parser expect, or a real paused record becomes unreadable.
paused_template_block="$(printf '%s\n' '### YYYY-MM-DD — Task title' '' 'Task ID: TASK-YYYYMMDD-NNN' '' 'Status: paused')"
PAUSED_TEMPLATE_BLOCK="$paused_template_block" perl -0777 -ne 'exit(index($_, $ENV{PAUSED_TEMPLATE_BLOCK}) >= 0 ? 0 : 1)' \
  "$ROOT/template/ai/paused-tasks.md" || fail 'paused template does not match the generated paused record format'
for task_skill in hub-task-intake hub-task-switch; do
  assert_contains "$ROOT/hub-template/ai/skills/$task_skill/SKILL.md" 'TASK-<project-id>-<UTC-date>-<NNN>'
done
for task_skill in hub-task-intake hub-task-switch hub-task-finish; do
  assert_contains "$ROOT/hub-template/ai/skills/$task_skill/SKILL.md" 'trusted architecture-to-Obsidian refresh'
  assert_contains "$ROOT/hub-template/ai/skills/$task_skill/SKILL.md" 'confirmed Obsidian-to-architecture proposal'
  assert_contains "$ROOT/hub-template/ai/skills/$task_skill/SKILL.md" 'do not overwrite'
  assert_contains "$ROOT/hub-template/ai/skills/$task_skill/SKILL.md" 'central Obsidian vault'
done
assert_contains "$ROOT/hub-template/ai/skills/hub-info-update/SKILL.md" 'central Obsidian vault'
assert_contains "$ROOT/hub-template/ai/architecture.md" 'Central Obsidian Projection'
for sync_doc in docs/concepts.md docs/install.md docs/update.md; do
  assert_contains "$ROOT/$sync_doc" 'trusted architecture-to-Obsidian refresh'
  assert_contains "$ROOT/$sync_doc" 'confirmed Obsidian-to-architecture proposal'
  assert_contains "$ROOT/$sync_doc" '--confirm-launchd-install'
  assert_contains "$ROOT/$sync_doc" '--confirm-launchd-uninstall'
done
for knowledge_doc in docs/file-roles.md docs/install.md docs/update.md docs/concepts.md; do
  assert_contains "$ROOT/$knowledge_doc" "Existing-project knowledge enablement is available only through the hub's"
  assert_contains "$ROOT/$knowledge_doc" 'Legacy standalone knowledge migration is out of scope.'
done
assert_contains "$ROOT/getting-started/help.md" 'Obsidian'
assert_contains "$ROOT/scripts/hub-smoke-test.sh" 'legacy_cleanup_contract_valid'
assert_contains "$ROOT/scripts/hub-smoke-test.sh" 'legacy_cleanup_order_valid'
assert_contains "$ROOT/scripts/hub-smoke-test.sh" 'cleanup_section_text'
assert_contains "$ROOT/scripts/hub-smoke-test.sh" 'legacy_cleanup_mutations_rejected'
assert_contains "$ROOT/hub-template/ai/skills/hub-project-migrate/SKILL.md" \
  'Optional legacy standalone cleanup'
assert_contains "$ROOT/hub-template/ai/skills/hub-project-migrate/SKILL.md" \
  'Do not delete `ai/` as a directory.'
assert_contains "$ROOT/hub-template/ai/skills/hub-project-migrate/SKILL.md" \
  'Do not archive, back up, copy, replace, or follow symlinks.'

for entry in "$ROOT/template/AGENTS.md" "$ROOT/template/CLAUDE.md"; do
  assert_contains "$entry" 'simplest sufficient solution'
  assert_contains "$entry" 'Separate verified facts from interpretations, hypotheses, and opinions.'
  assert_contains "$entry" 'security-sensitive change'
  assert_contains "$entry" 'wording or copy review'
done

for entry in "$ROOT/hub-template/AGENTS.md" "$ROOT/hub-template/CLAUDE.md"; do
  assert_contains "$entry" 'simplest sufficient solution'
  assert_contains "$entry" 'Separate verified facts from interpretations, hypotheses, and opinions.'
done

assert_not_contains "$ROOT/template/AGENTS.md" 'theme-factory'
assert_not_contains "$ROOT/template/CLAUDE.md" 'theme-factory'

PROJECT="$TMP_DIR/project"
init_git_project "$PROJECT"

printf 'custom agent entry\n' > "$PROJECT/AGENTS.md"
bash "$ROOT/scripts/install.sh" "$PROJECT" >/dev/null

assert_contains "$PROJECT/AGENTS.md" "custom agent entry"
assert_dir "$PROJECT/knowledge/research"
assert_dir "$PROJECT/knowledge/decisions"
assert_dir "$PROJECT/knowledge/risks"
assert_dir "$PROJECT/knowledge/runbooks"
assert_dir "$PROJECT/knowledge/inbox"
assert_file "$PROJECT/knowledge/README.md"
assert_file "$PROJECT/knowledge/record-template.md"
assert_contains "$PROJECT/knowledge/record-template.md" 'origin: stated'
assert_contains "$PROJECT/knowledge/record-template.md" 'valid_from: null'
assert_file "$PROJECT/ai/skills/knowledge-capture/SKILL.md"
assert_file "$PROJECT/ai/skills/knowledge-review/SKILL.md"
assert_contains "$PROJECT/knowledge/README.md" 'Knowledge records must be secret-free.'
assert_contains "$PROJECT/knowledge/README.md" 'The only allowed statuses are `draft`, `verified`, `needs-review`, `stale`, or'
assert_contains "$PROJECT/knowledge/README.md" '`superseded`:'
assert_contains "$PROJECT/ai/skills/knowledge-capture/SKILL.md" 'tokens, private keys, or raw environment values. Reject or redact secret values'
assert_contains "$PROJECT/ai/skills/knowledge-capture/SKILL.md" 'before requesting write confirmation; refer to an approved secret-management'
assert_contains "$PROJECT/ai/skills/knowledge-capture/SKILL.md" 'Reject any status outside this vocabulary.'
assert_contains "$PROJECT/ai/skills/knowledge-review/SKILL.md" 'Flag secret content and an invalid status.'
knowledge_capture_contract_valid "$PROJECT/ai/skills/knowledge-capture/SKILL.md" \
  || fail 'knowledge-capture must enforce containment, data safety, and retention'
knowledge_review_contract_valid "$PROJECT/ai/skills/knowledge-review/SKILL.md" \
  || fail 'knowledge-review must enforce containment and the complete record contract'
assert_contains "$PROJECT/knowledge/README.md" 'personal data or client data'
assert_contains "$PROJECT/knowledge/README.md" 'without echoing the rejected value'

CAPTURE_WITHOUT_TRAVERSAL_GUARD="$TMP_DIR/capture-without-traversal-guard.md"
sed '/Reject absolute paths and any path containing a `\.\.` segment/d' \
  "$PROJECT/ai/skills/knowledge-capture/SKILL.md" > "$CAPTURE_WITHOUT_TRAVERSAL_GUARD"
assert_rejected knowledge_capture_contract_valid "$CAPTURE_WITHOUT_TRAVERSAL_GUARD"

CAPTURE_WITHOUT_SYMLINK_GUARD="$TMP_DIR/capture-without-symlink-guard.md"
sed '/reject any symlink component without following it/d' \
  "$PROJECT/ai/skills/knowledge-capture/SKILL.md" > "$CAPTURE_WITHOUT_SYMLINK_GUARD"
assert_rejected knowledge_capture_contract_valid "$CAPTURE_WITHOUT_SYMLINK_GUARD"

REVIEW_WITHOUT_TRAVERSAL_GUARD="$TMP_DIR/review-without-traversal-guard.md"
sed '/Reject absolute paths and any path containing a `\.\.` segment/d' \
  "$PROJECT/ai/skills/knowledge-review/SKILL.md" > "$REVIEW_WITHOUT_TRAVERSAL_GUARD"
assert_rejected knowledge_review_contract_valid "$REVIEW_WITHOUT_TRAVERSAL_GUARD"

REVIEW_WITHOUT_SYMLINK_GUARD="$TMP_DIR/review-without-symlink-guard.md"
sed '/reject any symlink component without following it/d' \
  "$PROJECT/ai/skills/knowledge-review/SKILL.md" > "$REVIEW_WITHOUT_SYMLINK_GUARD"
assert_rejected knowledge_review_contract_valid "$REVIEW_WITHOUT_SYMLINK_GUARD"

REVIEW_WITHOUT_SOURCE_DATES="$TMP_DIR/review-without-source-dates.md"
sed '/publication or update date of each cited source separately/d' \
  "$PROJECT/ai/skills/knowledge-review/SKILL.md" > "$REVIEW_WITHOUT_SOURCE_DATES"
assert_rejected knowledge_review_contract_valid "$REVIEW_WITHOUT_SOURCE_DATES"

cmp -s "$ROOT/template/knowledge/README.md" "$ROOT/knowledge/README.md" \
  || fail 'root and template knowledge READMEs differ'
cmp -s "$ROOT/template/ai/skills/knowledge-capture/SKILL.md" "$ROOT/ai/skills/knowledge-capture/SKILL.md" \
  || fail 'root and template knowledge-capture skills differ'
cmp -s "$ROOT/template/ai/skills/knowledge-review/SKILL.md" "$ROOT/ai/skills/knowledge-review/SKILL.md" \
  || fail 'root and template knowledge-review skills differ'
assert_file "$PROJECT/ai/current-task.md"
assert_file "$PROJECT/ai/skills/task-intake/SKILL.md"
assert_file "$PROJECT/ai/skills/start-screen/SKILL.md"
assert_file "$PROJECT/ai/skills/impeccable/SKILL.md"
assert_file "$PROJECT/ai/skills/theme-factory/SKILL.md"
assert_file "$PROJECT/ai/skills/animate/SKILL.md"
assert_file "$PROJECT/ai/skills/design-motion-principles/SKILL.md"
assert_not_exists "$PROJECT/ai/skills/bugfix-workflow/SKILL.md"

assert_contains "$PROJECT/ai/skills/environment-check/SKILL.md" "Architecture version check"
assert_contains "$PROJECT/ai/external-tools.md" "microsoft/playwright-mcp"

printf '# Current Task\n\nStatus: active\n\nStage: implementation\n\n## Goal\n\nKeep this project memory.\n' > "$PROJECT/ai/current-task.md"
git -C "$PROJECT" add .
git -C "$PROJECT" commit -m "test: install architecture" >/dev/null

bash "$ROOT/scripts/update-installed-architecture.sh" --project "$PROJECT" --source "$ROOT" --apply >/dev/null
assert_contains "$PROJECT/ai/current-task.md" "Keep this project memory."

PRE_KNOWLEDGE_PROJECT="$TMP_DIR/pre-knowledge-project"
init_git_project "$PRE_KNOWLEDGE_PROJECT"
mkdir -p "$PRE_KNOWLEDGE_PROJECT/ai"
for rel in AGENTS.md CLAUDE.md ai/architecture.md ai/external-tools.md; do
  cp "$ROOT/template/$rel" "$PRE_KNOWLEDGE_PROJECT/$rel"
done
printf '# Current Task\n\nStatus: active\n\nStage: implementation\n\n## Goal\n\nKeep pre-knowledge task memory.\n' \
  > "$PRE_KNOWLEDGE_PROJECT/ai/current-task.md"
cp "$PRE_KNOWLEDGE_PROJECT/ai/current-task.md" "$TMP_DIR/pre-knowledge-current-task.before"
git -C "$PRE_KNOWLEDGE_PROJECT" add .
git -C "$PRE_KNOWLEDGE_PROJECT" commit -m "test: pre-knowledge project" >/dev/null

bash "$ROOT/scripts/update-installed-architecture.sh" --project "$PRE_KNOWLEDGE_PROJECT" --source "$ROOT" --apply \
  > "$TMP_DIR/pre-knowledge-update.out"
assert_not_exists "$PRE_KNOWLEDGE_PROJECT/knowledge"
cmp -s "$TMP_DIR/pre-knowledge-current-task.before" "$PRE_KNOWLEDGE_PROJECT/ai/current-task.md" \
  || fail 'updater changed pre-knowledge task memory'
assert_contains "$TMP_DIR/pre-knowledge-update.out" 'Updating does not enable knowledge in existing projects.'

EXISTING_KNOWLEDGE_PROJECT="$TMP_DIR/existing-knowledge-project"
init_git_project "$EXISTING_KNOWLEDGE_PROJECT"
mkdir -p "$EXISTING_KNOWLEDGE_PROJECT/ai" "$EXISTING_KNOWLEDGE_PROJECT/knowledge/research"
for rel in AGENTS.md CLAUDE.md ai/architecture.md ai/external-tools.md; do
  cp "$ROOT/template/$rel" "$EXISTING_KNOWLEDGE_PROJECT/$rel"
done
cp "$ROOT/template/ai/current-task.md" "$EXISTING_KNOWLEDGE_PROJECT/ai/current-task.md"
printf '%s\n' '# Updater boundary record' '' 'This record must remain byte-for-byte unchanged.' \
  > "$EXISTING_KNOWLEDGE_PROJECT/knowledge/research/updater-boundary.md"
cp "$EXISTING_KNOWLEDGE_PROJECT/knowledge/research/updater-boundary.md" \
  "$TMP_DIR/existing-knowledge-record.before"
git -C "$EXISTING_KNOWLEDGE_PROJECT" add .
git -C "$EXISTING_KNOWLEDGE_PROJECT" commit -m "test: existing knowledge record" >/dev/null

bash "$ROOT/scripts/update-installed-architecture.sh" --project "$EXISTING_KNOWLEDGE_PROJECT" --source "$ROOT" --apply >/dev/null
cmp -s "$TMP_DIR/existing-knowledge-record.before" \
  "$EXISTING_KNOWLEDGE_PROJECT/knowledge/research/updater-boundary.md" \
  || fail 'updater changed an existing knowledge record'

cp "$PROJECT/AGENTS.md" "$TMP_DIR/standalone-agents.before"
cp "$PROJECT/CLAUDE.md" "$TMP_DIR/standalone-claude.before"
bash "$ROOT/scripts/update-installed-architecture.sh" --project "$PROJECT" --source "$ROOT" --offer-hub > "$TMP_DIR/offer-hub.out"
assert_contains "$TMP_DIR/offer-hub.out" 'bash scripts/install.sh --mode hub /path/to/_ai-hub'
assert_not_contains "$TMP_DIR/offer-hub.out" '--root'
assert_contains "$TMP_DIR/offer-hub.out" 'Standalone-to-hub migration preview (read-only).'
assert_contains "$TMP_DIR/offer-hub.out" 'ai/current-task.md'
assert_contains "$TMP_DIR/offer-hub.out" 'ai/skills/task-intake/SKILL.md'
assert_contains "$TMP_DIR/offer-hub.out" 'No files will be changed, registered, removed, archived, or migrated.'
assert_contains "$TMP_DIR/offer-hub.out" '-> keep now; archive or remove only in a separately approved migration'
assert_contains "$TMP_DIR/offer-hub.out" 'Future hub structure: <parent>/_ai-hub/projects/<project>'
assert_contains "$TMP_DIR/offer-hub.out" 'does not move projects automatically'
cmp -s "$TMP_DIR/standalone-agents.before" "$PROJECT/AGENTS.md" || fail '--offer-hub changed AGENTS.md'
cmp -s "$TMP_DIR/standalone-claude.before" "$PROJECT/CLAUDE.md" || fail '--offer-hub changed CLAUDE.md'
assert_contains "$PROJECT/ai/current-task.md" 'Keep this project memory.'

bash "$ROOT/scripts/update-installed-architecture.sh" --project "$PROJECT" --source "$ROOT" --check >/dev/null

perl -0pi -e 's/Version: [0-9]+\.[0-9]+/Version: 0.1/' "$PROJECT/ai/architecture.md"
if bash "$ROOT/scripts/update-installed-architecture.sh" --project "$PROJECT" --source "$ROOT" --check >/dev/null; then
  fail "--check should exit 1 when update is available"
fi

for check_args in \
  "--check --apply" \
  "--apply --check" \
  "--check --commit" \
  "--commit --check"; do
  CHECK_PROJECT="$TMP_DIR/check-${check_args// /-}"
  cp -R "$PROJECT" "$CHECK_PROJECT"
  cp "$CHECK_PROJECT/AGENTS.md" "$TMP_DIR/check-agents.before"
  cp "$CHECK_PROJECT/ai/architecture.md" "$TMP_DIR/check-architecture.before"
  before_commit="$(git -C "$CHECK_PROJECT" rev-parse HEAD)"

  if bash "$ROOT/scripts/update-installed-architecture.sh" --project "$CHECK_PROJECT" --source "$ROOT" --allow-dirty $check_args > "$TMP_DIR/check.out" 2>&1; then
    fail "$check_args should exit 1 when update is available"
  fi
  cmp -s "$TMP_DIR/check-agents.before" "$CHECK_PROJECT/AGENTS.md" || fail "$check_args changed AGENTS.md"
  cmp -s "$TMP_DIR/check-architecture.before" "$CHECK_PROJECT/ai/architecture.md" || fail "$check_args changed architecture"
  [ "$(git -C "$CHECK_PROJECT" rev-parse HEAD)" = "$before_commit" ] || fail "$check_args created a commit"
done

# Regression: same relative-source defect in the standalone updater (Audit 1).
RELATIVE_SOURCE_OUT="$TMP_DIR/relative-source.out"
(cd "$ROOT" && bash "$ROOT/scripts/update-installed-architecture.sh" \
  --project "$PROJECT" --source . --dry-run) > "$RELATIVE_SOURCE_OUT" 2>&1 \
  || fail "relative --source dry-run against the project failed unexpectedly"
assert_contains "$RELATIVE_SOURCE_OUT" "Source template: $ROOT/template"
assert_not_contains "$RELATIVE_SOURCE_OUT" "Source template: $PROJECT"

if bash "$ROOT/scripts/update-installed-architecture.sh" \
  --project "$PROJECT" --source "$PROJECT" --dry-run \
  > "$TMP_DIR/self-source.out" 2>&1; then
  fail 'standalone updater compared the project with itself'
fi
assert_contains "$TMP_DIR/self-source.out" 'resolves to the project itself'

BAD_PROJECT="$TMP_DIR/bad-project"
init_git_project "$BAD_PROJECT"
printf 'not enough\n' > "$BAD_PROJECT/AGENTS.md"
if bash "$ROOT/scripts/update-installed-architecture.sh" --project "$BAD_PROJECT" --source "$ROOT" --dry-run >/dev/null 2>&1; then
  fail "updater guard should reject project missing ai/architecture.md and ai/current-task.md"
fi

echo "Smoke tests passed."

bash "$ROOT/scripts/hub-smoke-test.sh"
