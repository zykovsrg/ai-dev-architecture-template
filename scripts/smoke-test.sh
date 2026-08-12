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

assert_contains() {
  local file="$1"
  local pattern="$2"
  grep -Fq -- "$pattern" "$file" || fail "expected '$pattern' in $file"
}

assert_not_exists() {
  [ ! -e "$1" ] || fail "expected path to be absent: $1"
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
assert_contains "$TMP_DIR/consistency.out" 'OK [hub skill references] — 10 declared skills exist'
assert_contains "$TMP_DIR/consistency.out" 'OK [hub update classes]'
assert_contains "$TMP_DIR/consistency.out" 'OK [standalone memory updater boundaries]'
assert_contains "$ROOT/scripts/check-consistency.sh" 'extract_block "$standalone_base/AGENTS.md" canon:controlled-memory'
assert_contains "$ROOT/scripts/check-consistency.sh" 'hub architecture absent'
assert_contains "$ROOT/README.md" 'Personal hub'
assert_contains "$ROOT/README.md" 'Обычная архитектура для одного проекта'
assert_contains "$ROOT/README.md" 'единая точка входа'
assert_contains "$ROOT/docs/install.md" '--mode hub'
assert_contains "$ROOT/docs/update.md" 'update-installed-hub.sh'
assert_contains "$ROOT/docs/file-roles.md" 'Hub-managed project memory'
assert_contains "$ROOT/getting-started/getting-started.md" 'personal hub'

PROJECT="$TMP_DIR/project"
init_git_project "$PROJECT"

printf 'custom agent entry\n' > "$PROJECT/AGENTS.md"
bash "$ROOT/scripts/install.sh" "$PROJECT" >/dev/null

assert_contains "$PROJECT/AGENTS.md" "custom agent entry"
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

cp "$PROJECT/AGENTS.md" "$TMP_DIR/standalone-agents.before"
cp "$PROJECT/CLAUDE.md" "$TMP_DIR/standalone-claude.before"
bash "$ROOT/scripts/update-installed-architecture.sh" --project "$PROJECT" --source "$ROOT" --offer-hub > "$TMP_DIR/offer-hub.out"
assert_contains "$TMP_DIR/offer-hub.out" 'bash scripts/install.sh --mode hub'
assert_contains "$TMP_DIR/offer-hub.out" 'Standalone-to-hub migration preview (read-only).'
assert_contains "$TMP_DIR/offer-hub.out" 'ai/current-task.md'
assert_contains "$TMP_DIR/offer-hub.out" 'ai/skills/task-intake/SKILL.md'
assert_contains "$TMP_DIR/offer-hub.out" 'No files will be changed, registered, removed, archived, or migrated.'
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

BAD_PROJECT="$TMP_DIR/bad-project"
init_git_project "$BAD_PROJECT"
printf 'not enough\n' > "$BAD_PROJECT/AGENTS.md"
if bash "$ROOT/scripts/update-installed-architecture.sh" --project "$BAD_PROJECT" --source "$ROOT" --dry-run >/dev/null 2>&1; then
  fail "updater guard should reject project missing ai/architecture.md and ai/current-task.md"
fi

echo "Smoke tests passed."

bash "$ROOT/scripts/hub-smoke-test.sh"
