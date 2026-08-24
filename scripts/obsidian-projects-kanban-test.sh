#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GENERATOR="$ROOT/scripts/generate-obsidian-projects-kanban.sh"
TMP_DIR="$(mktemp -d /private/tmp/obsidian-projection.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_file() { [ -f "$1" ] || fail "missing file: $1"; }
assert_not_exists() { [ ! -e "$1" ] || fail "unexpected preview output: $1"; }
assert_contains() { grep -Fq -- "$2" "$1" || fail "expected '$2' in $1"; }
assert_count() {
  local expected="$1" needle="$2" file="$3" actual
  actual="$(grep -F -- "$needle" "$file" | wc -l | tr -d ' ')"
  [ "$actual" -eq "$expected" ] || fail "expected $expected occurrences of '$needle' in $file, got $actual"
}

HUB="$TMP_DIR/hub"
PROJECTS="$HUB/projects"
VAULT="$HUB/tmp/obsidian-vault-copy"
SCOPE="$TMP_DIR/scope.txt"
mkdir -p "$HUB/ai/project-cards" "$PROJECTS" \
  "$VAULT/Obsidian/AI-архитектура/Projects/_views"

printf '%s\n' '# Project Registry' > "$HUB/ai/project-registry.md"

add_fixture() {
  local id="$1" name="$2" registry_status="$3" current="$4" future="$5" paused="$6"
  local project="$PROJECTS/$id"
  mkdir -p "$project/ai"
  printf '%s\n' "$current" > "$project/ai/current-task.md"
  printf '%s\n' "$future" > "$project/ai/future-tasks.md"
  printf '%s\n' "$paused" > "$project/ai/paused-tasks.md"
  cat > "$HUB/ai/project-cards/$id.md" <<EOF
# Project Card

Project ID: $id
Name: $name
Status: $registry_status
Purpose: Synthetic fixture for the Obsidian board contract.
EOF
  cat >> "$HUB/ai/project-registry.md" <<EOF

## $id
Name: $name
Status: $registry_status
Path: $project
Card: $HUB/ai/project-cards/$id.md
EOF
  printf '%s\n' "$id" >> "$SCOPE"
}

add_fixture "active-project" "Active project" "active" \
  $'Status: active\n- [ ] Ship the active task' \
  $'Status: none' $'Status: none'
add_fixture "ready-future-project" "Ready future project" "active" \
  $'Status: none' $'Status: ready\n- [ ] Promote the ready task' $'Status: none'
add_fixture "waiting-project" "Waiting project" "active" \
  $'Status: waiting\n- [ ] Waiting on external answer' $'Status: none' $'Status: none'
add_fixture "paused-project" "Paused project" "active" \
  $'Status: none' $'Status: none' $'Status: paused\n- [ ] Resume paused task'
add_fixture "completed-project" "Completed project" "completed" \
  $'Status: completed\n- [x] Canonical completed task' $'Status: none' $'Status: none'
add_fixture "archived-project" "Archived project" "archived" \
  $'Status: none' $'Status: none' $'Status: none'
add_fixture "legacy-complete-project" "Legacy complete project" "active" \
  $'Status: complete\n- [x] Legacy task must be reviewed' $'Status: none' $'Status: none'

BOARD="$VAULT/Obsidian/AI-архитектура/Projects/_views/Projects-Kanban.md"
MANIFEST="$VAULT/Obsidian/AI-архитектура/Projects/_views/Projects-Kanban.manifest.json"

# RED: this command is intentionally absent until Task 3 implements the generator.
if [ ! -x "$GENERATOR" ]; then
  "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview
  fail "expected the missing generator to fail"
fi

before_files="$(find "$VAULT" -type f -print | sort)"
"$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/preview.txt"
assert_count 1 'id: active-project' "$TMP_DIR/preview.txt"
assert_count 1 'id: ready-future-project' "$TMP_DIR/preview.txt"
assert_count 1 'id: waiting-project' "$TMP_DIR/preview.txt"
assert_count 1 'id: paused-project' "$TMP_DIR/preview.txt"
assert_count 1 'id: completed-project' "$TMP_DIR/preview.txt"
assert_count 1 'id: archived-project' "$TMP_DIR/preview.txt"
assert_count 1 'id: legacy-complete-project' "$TMP_DIR/preview.txt"
assert_contains "$TMP_DIR/preview.txt" 'legacy-complete-project'
assert_contains "$TMP_DIR/preview.txt" 'Incoming'
assert_contains "$TMP_DIR/preview.txt" 'нужно проверить'
[ "$before_files" = "$(find "$VAULT" -type f -print | sort)" ] || fail 'preview created files'
assert_not_exists "$BOARD"
assert_not_exists "$MANIFEST"

expect_scope_failure() {
  local scope_path="$1"
  if "$GENERATOR" --hub "$HUB" --scope "$scope_path" --vault "$VAULT" --preview >"$TMP_DIR/scope-error.txt" 2>&1; then
    fail "expected invalid scope to fail: $scope_path"
  fi
}

printf '%s\n' 'active-project' > "$TMP_DIR/outside-scope.txt"
expect_scope_failure "$TMP_DIR/outside-scope.txt"
expect_scope_failure "relative-scope.txt"

echo "PASS: Obsidian project board contract"
