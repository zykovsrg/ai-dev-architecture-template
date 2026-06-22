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
  grep -q "$pattern" "$file" || fail "expected '$pattern' in $file"
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

PROJECT="$TMP_DIR/project"
init_git_project "$PROJECT"

printf 'custom agent entry\n' > "$PROJECT/AGENTS.md"
bash "$ROOT/scripts/install.sh" "$PROJECT" >/dev/null

assert_contains "$PROJECT/AGENTS.md" "custom agent entry"
assert_file "$PROJECT/ai/current-task.md"
assert_file "$PROJECT/ai/skills/task-intake/SKILL.md"
assert_not_exists "$PROJECT/ai/skills/bugfix-workflow/SKILL.md"

printf '# Current Task\n\nStatus: active\n\nStage: implementation\n\n## Goal\n\nKeep this project memory.\n' > "$PROJECT/ai/current-task.md"
git -C "$PROJECT" add .
git -C "$PROJECT" commit -m "test: install architecture" >/dev/null

bash "$ROOT/scripts/update-installed-architecture.sh" --project "$PROJECT" --source "$ROOT" --apply >/dev/null
assert_contains "$PROJECT/ai/current-task.md" "Keep this project memory."

bash "$ROOT/scripts/update-installed-architecture.sh" --project "$PROJECT" --source "$ROOT" --check >/dev/null

perl -0pi -e 's/Version: [0-9]+\.[0-9]+/Version: 0.1/' "$PROJECT/ai/architecture.md"
if bash "$ROOT/scripts/update-installed-architecture.sh" --project "$PROJECT" --source "$ROOT" --check >/dev/null; then
  fail "--check should exit 1 when update is available"
fi

BAD_PROJECT="$TMP_DIR/bad-project"
init_git_project "$BAD_PROJECT"
printf 'not enough\n' > "$BAD_PROJECT/AGENTS.md"
if bash "$ROOT/scripts/update-installed-architecture.sh" --project "$BAD_PROJECT" --source "$ROOT" --dry-run >/dev/null 2>&1; then
  fail "updater guard should reject project missing ai/architecture.md and ai/current-task.md"
fi

echo "Smoke tests passed."
