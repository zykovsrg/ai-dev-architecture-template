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
assert_not_contains() { ! grep -Fq -- "$2" "$1" || fail "unexpected '$2' in $1"; }
assert_count() {
  local expected="$1" needle="$2" file="$3" actual
  actual="$(grep -F -- "$needle" "$file" | wc -l | tr -d ' ')"
  [ "$actual" -eq "$expected" ] || fail "expected $expected occurrences of '$needle' in $file, got $actual"
}
assert_column() {
  local id="$1" expected="$2" actual
  actual="$(awk -v wanted="$id" '/^## / {column=substr($0, 4)} $0 == "- id: " wanted {print column; exit}' "$TMP_DIR/preview.txt")"
  [ "$actual" = "$expected" ] || fail "expected $id in $expected, got ${actual:-none}"
}

HUB="$TMP_DIR/hub"
PROJECTS="$HUB/projects"
VAULT="$HUB/tmp/obsidian-vault-copy"
SCOPE="$HUB/scope.txt"
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
  $'Status: active\ntask:\n  due: 2026-08-31\n  subtasks:\n    - title: First structured action\n    - title: Second structured action\n    - title: Third structured action\n    - title: Fourth structured action\n    - title: Fifth structured action\n    - title: Sixth structured action\n    - title: Seventh structured action\n    - title: Eighth structured action' \
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
  $'Status: complete\n- [x] Legacy task must be reviewed\nTASK-BODY-SENTINEL' $'Status: none' $'Status: none'
add_fixture "none-status-project" "None status project" "none" \
  $'Status: none' $'Status: none' $'Status: none'
add_fixture "unknown-status-project" "Unknown status project" "mystery" \
  $'Status: active' $'Status: none' $'Status: none'

BOARD="$VAULT/Obsidian/AI-архитектура/Projects/_views/Projects-Kanban.md"
MANIFEST="$VAULT/Obsidian/AI-архитектура/Projects/_views/Projects-Kanban.manifest.json"

# RED: this command is intentionally absent until Task 3 implements the generator.
if [ ! -x "$GENERATOR" ]; then
  "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview
  fail "expected the missing generator to fail"
fi

before_files="$(find "$VAULT" -type f -print | sort)"
PREVIEW_TMP="$TMP_DIR/preview-tmp"
mkdir "$PREVIEW_TMP"
before_preview_tmp="$(find "$PREVIEW_TMP" -print | sort)"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/preview.txt"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/preview-repeat.txt"
cmp -s "$TMP_DIR/preview.txt" "$TMP_DIR/preview-repeat.txt" || fail 'fixed-time preview is not deterministic'
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
assert_column active-project Active
assert_column ready-future-project Planned
assert_column waiting-project Waiting
assert_column paused-project Paused
assert_column completed-project Completed
assert_column archived-project Archived
assert_column legacy-complete-project Incoming
assert_column none-status-project Incoming
assert_column unknown-status-project Incoming
assert_contains "$TMP_DIR/preview.txt" 'First structured action'
assert_count 7 'structured action' "$TMP_DIR/preview.txt"
assert_not_contains "$TMP_DIR/preview.txt" 'Eighth structured action'
assert_contains "$TMP_DIR/preview.txt" 'due: 2026-08-31'
assert_contains "$TMP_DIR/preview.txt" '## Incoming'
assert_contains "$TMP_DIR/preview.txt" '## Planned'
assert_contains "$TMP_DIR/preview.txt" '## Active'
assert_contains "$TMP_DIR/preview.txt" '## Waiting'
assert_contains "$TMP_DIR/preview.txt" '## Paused'
assert_contains "$TMP_DIR/preview.txt" '## Completed'
assert_contains "$TMP_DIR/preview.txt" '## Archived'
[ "$(grep -n '^## ' "$TMP_DIR/preview.txt" | cut -d: -f2 | sed 's/^## //' | tr '\n' '|')" = 'Incoming|Planned|Active|Waiting|Paused|Completed|Archived|' ] || fail 'column order is not deterministic'
[ "$before_files" = "$(find "$VAULT" -type f -print | sort)" ] || fail 'preview created files'
[ "$before_preview_tmp" = "$(find "$PREVIEW_TMP" -print | sort)" ] || fail 'preview created temp files'
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
printf '%s\n' 'active-project' > "$TMP_DIR/dotdot-scope.txt"
expect_scope_failure "$HUB/../dotdot-scope.txt"
expect_scope_failure "relative-scope.txt"

expect_write_failure() {
  if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write "$@" >"$TMP_DIR/write-error.txt" 2>&1; then
    fail "expected unsafe write to fail"
  fi
}

expect_write_failure
"$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/write.txt"
assert_file "$BOARD"
assert_file "$MANIFEST"
[ "$(find "$VAULT" -type f | wc -l | tr -d ' ')" -eq 2 ] || fail 'write created files other than board and manifest'
assert_not_contains "$MANIFEST" 'TASK-BODY-SENTINEL'
assert_contains "$MANIFEST" '"format_version"'
assert_contains "$MANIFEST" '"sources"'

printf '\nmanual edit\n' >> "$BOARD"
board_before="$(shasum -a 256 "$BOARD" | awk '{print $1}')"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write >"$TMP_DIR/manual-edit.txt" 2>&1; then
  fail 'manual board edit must block replacement'
fi
assert_contains "$TMP_DIR/manual-edit.txt" 'proposal pending'
[ "$board_before" = "$(shasum -a 256 "$BOARD" | awk '{print $1}')" ] || fail 'manual board edit was replaced'

rm -f "$BOARD" "$MANIFEST"
rmdir "$VAULT/Obsidian/AI-архитектура/Projects/_views"
ln -s "$TMP_DIR" "$VAULT/Obsidian/AI-архитектура/Projects/_views"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write >"$TMP_DIR/symlink-write.txt" 2>&1; then
  fail 'symlinked target directory must block write'
fi

echo "PASS: Obsidian project board contract"
