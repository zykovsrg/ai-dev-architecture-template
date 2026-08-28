#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GENERATOR="$ROOT/scripts/generate-obsidian-projects-kanban.sh"
TMP_DIR="$(mktemp -d /private/tmp/obsidian-projection.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
assert_file() { [ -f "$1" ] || fail "missing file: $1"; }
assert_not_exists() { [ ! -e "$1" ] || fail "unexpected path: $1"; }
assert_contains() { grep -Fq -- "$2" "$1" || fail "expected '$2' in $1"; }
assert_not_contains() { ! grep -Fq -- "$2" "$1" || fail "unexpected '$2' in $1"; }
assert_exact_line() { grep -Fxq -- "$2" "$1" || fail "expected exact line '$2' in $1"; }
assert_board_isolated() {
  local board="$1" project_id="$2" anchor
  while IFS= read -r anchor; do
    case "$anchor" in
      "$project_id"--*) ;;
      *) fail "board $board contains foreign anchor: $anchor" ;;
    esac
  done < <(sed -n 's/^.*\^//p' "$board")
}

HUB="$TMP_DIR/hub"
PROJECTS="$HUB/projects"
ARCHITECTURE_PROJECT="$PROJECTS/ai-dev-architecture"
VAULT="$ARCHITECTURE_PROJECT/obsidian-vault"
SCOPE="$HUB/scope.txt"
OVERVIEW="$VAULT/Obsidian/Projects-Overview.md"
ARCHITECTURE_BOARD="$VAULT/Obsidian/Projects/ai-dev-architecture/Kanban.md"
WAITING_BOARD="$VAULT/Obsidian/Projects/waiting-project/Kanban.md"
EMPTY_BOARD="$VAULT/Obsidian/Projects/empty-project/Kanban.md"
# Legacy assertions below exercise transactional refresh semantics against one
# project board; the generated global Tasks-Kanban target must remain absent.
TASKS="$ARCHITECTURE_BOARD"
MANIFEST="$VAULT/Obsidian/AI-Architecture.manifest.json"
GENERATED_FILES=(
  "$ARCHITECTURE_BOARD" "$WAITING_BOARD" "$EMPTY_BOARD"
  "$VAULT/Obsidian/Projects/review-project/Kanban.md"
  "$VAULT/Obsidian/Projects/done-project/Kanban.md"
  "$VAULT/Obsidian/Projects/archived-project/Kanban.md"
  "$OVERVIEW" "$MANIFEST"
)
mkdir -p "$HUB/ai/project-cards" "$PROJECTS" "$VAULT/Obsidian"
printf '%s\n' '# Project Registry' > "$HUB/ai/project-registry.md"
cat > "$HUB/ai/archiprojects.md" <<'EOF'
# Archiprojects

## дела

```yaml
id: дела
name: Дела
status: active
kind: group
```
EOF

add_project() {
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
primary_archiproject: дела
archiproject_contribution: architecture
related_archiprojects: none
tags: дела
Status: $registry_status
Purpose: Synthetic fixture.
EOF
  cat >> "$HUB/ai/project-registry.md" <<EOF

## $id
Name: $name
Status: $registry_status
Path: $project
Card: ai/project-cards/$id.md
EOF
  printf '%s\n' "$id" >> "$SCOPE"
}

add_project "ai-dev-architecture" "AI Dev Architecture" "active" \
  $'Status: active\nTask ID: TASK-20260826-001\ndue: 2026-08-26\n\n## Goal\n\nCurrent architecture task' \
  $'### FT-20260826-001 — Idea task\n\nStatus: idea\n\n### FT-20260826-002 — Ready task\n\nStatus: ready\ndue: 2026-08-28\n\n### FT-20260826-003 — Blocked task\n\nStatus: blocked\n\n### FT-20260826-004 — Promoted task\n\nStatus: promoted\n\n### FT-20260826-005 — Dropped task\n\nStatus: dropped\n\n### FT-20260826-006 — Completed future task\n\nStatus: done' \
  $'### 2026-08-20 — Paused task\n\nTask ID: TASK-20260820-001\n\nStatus: paused'
add_project "waiting-project" "Waiting project" "active" \
  $'Status: waiting\nTask ID: TASK-20260826-002\n\n## Goal\n\nWaiting current task' $'No future tasks.' $'No paused tasks.'
add_project "review-project" "Review project" "active" \
  $'Status: review\nTask ID: TASK-20260826-003\n\n## Goal\n\nReview current task' $'No future tasks.' $'No paused tasks.'
add_project "done-project" "Done project" "completed" \
  $'Status: done\nTask ID: TASK-20260826-004\n\n## Goal\n\nDone current task' $'No future tasks.' $'No paused tasks.'
add_project "empty-project" "Empty project" "active" \
  $'Status: backlog\n\n## Goal\n\nNo current task' $'No future tasks.' $'No paused tasks.'
add_project "archived-project" "Archived project" "archived" \
  $'Status: done\nTask ID: TASK-20260826-005\n\n## Goal\n\nArchived task' $'No future tasks.' $'No paused tasks.'

# Seed legacy output and manually maintained project boards. Preview must not
# change these bytes; migration may remove only the legacy generated board and
# must preserve manual boards that are not explicit generated targets.
printf '%s\n' 'legacy generated board' > "$VAULT/Obsidian/Tasks-Kanban.md"
cp "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/legacy-tasks-board"

before_files="$(find "$VAULT" -type f -print | sort)"
before_bytes="$(find "$VAULT" -type f -print0 | xargs -0 shasum -a 256 | sort)"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/preview.txt"
[ "$before_files" = "$(find "$VAULT" -type f -print | sort)" ] || fail 'preview created files'
[ "$before_bytes" = "$(find "$VAULT" -type f -print0 | xargs -0 shasum -a 256 | sort)" ] || fail 'preview changed fixture bytes'
for column in Ideas Ready Active Waiting Blocked Review Paused Done; do assert_contains "$TMP_DIR/preview.txt" "## $column"; done
for title in 'Idea task' 'Ready task' 'Current architecture task' 'Waiting current task' 'Blocked task' 'Review current task' 'Paused task' 'Done current task'; do assert_contains "$TMP_DIR/preview.txt" "$title"; done
assert_contains "$TMP_DIR/preview.txt" '  - project: AI Dev Architecture'
assert_contains "$TMP_DIR/preview.txt" '- [ ] Current architecture task ^ai-dev-architecture--TASK-20260826-001'
assert_contains "$TMP_DIR/preview.txt" '- [ ] Idea task ^ai-dev-architecture--FT-20260826-001'
assert_contains "$TMP_DIR/preview.txt" '- [ ] Paused task ^ai-dev-architecture--TASK-20260820-001'
assert_not_contains "$TMP_DIR/preview.txt" 'Promoted task'
assert_not_contains "$TMP_DIR/preview.txt" 'Dropped task'
assert_not_contains "$TMP_DIR/preview.txt" 'Completed future task'
assert_contains "$TMP_DIR/preview.txt" '--- projects overview ---'
assert_exact_line "$TMP_DIR/preview.txt" '| Проект | Архипроект | Текущая задача |'
assert_exact_line "$TMP_DIR/preview.txt" '| --- | --- | --- |'
assert_contains "$TMP_DIR/preview.txt" '| [[Projects/ai-dev-architecture/Kanban\\|AI Dev Architecture]] | Дела | Current architecture task |'
assert_not_contains "$TMP_DIR/preview.txt" '| Project | Status | Current task | Ready | Waiting | Due |'
assert_not_contains "$TMP_DIR/preview.txt" '| Проект | Статус | Текущая задача | Ready | Waiting | Due |'
assert_not_contains "$TMP_DIR/preview.txt" '| Проект | Архипроект | Текущая задача | Status'
assert_not_contains "$TMP_DIR/preview.txt" '| Проект | Архипроект | Текущая задача | Ready'
assert_not_contains "$TMP_DIR/preview.txt" '| Проект | Архипроект | Текущая задача | Waiting'
assert_not_contains "$TMP_DIR/preview.txt" '| Проект | Архипроект | Текущая задача | Due'
assert_contains "$TMP_DIR/preview.txt" '"format_version": 4'

if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write > "$TMP_DIR/no-confirm.txt" 2>&1; then fail 'write without confirmation succeeded'; fi
assert_file "$VAULT/Obsidian/Tasks-Kanban.md"
cmp -s "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/legacy-tasks-board" || fail 'unconfirmed write changed legacy board'
assert_not_exists "$VAULT/Obsidian/Projects"
assert_not_exists "$ARCHITECTURE_BOARD"; assert_not_exists "$WAITING_BOARD"; assert_not_exists "$OVERVIEW"; assert_not_exists "$MANIFEST"
mkdir -p "$VAULT/Obsidian/Projects/manual-project"
printf '%s\n' 'manual project board' > "$VAULT/Obsidian/Projects/manual-project/Kanban.md"
cp "$VAULT/Obsidian/Projects/manual-project/Kanban.md" "$TMP_DIR/manual-project-board"
mv "$VAULT/Obsidian/Projects" "$TMP_DIR/projects-real"
ln -s /private/tmp "$VAULT/Obsidian/Projects"
if SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/symlink-projects-dir.txt" 2>&1; then fail 'migration accepted symlinked Projects directory'; fi
assert_contains "$TMP_DIR/symlink-projects-dir.txt" 'Projects directory must be a real non-symlink directory'
rm "$VAULT/Obsidian/Projects"
mv "$TMP_DIR/projects-real" "$VAULT/Obsidian/Projects"
ln -s /private/tmp "$VAULT/Obsidian/Projects/empty-project"
if SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/symlink-project-dir.txt" 2>&1; then fail 'migration accepted symlinked project board directory'; fi
assert_contains "$TMP_DIR/symlink-project-dir.txt" 'project board directory is unsafe'
rm "$VAULT/Obsidian/Projects/empty-project"
mkdir "$VAULT/Obsidian/Projects/empty-project"
ln -s /private/tmp "$EMPTY_BOARD"
if SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/symlink-board.txt" 2>&1; then fail 'migration accepted symlinked board target'; fi
assert_contains "$TMP_DIR/symlink-board.txt" 'generated targets must not be symlinks'
rm "$EMPTY_BOARD"
mkdir -p "$(dirname "$ARCHITECTURE_BOARD")"
printf '%s\n' 'manual scoped board' > "$ARCHITECTURE_BOARD"
cp "$ARCHITECTURE_BOARD" "$TMP_DIR/manual-scoped-board"
if SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/manual-scoped.txt" 2>&1; then fail 'migration overwrote manual scoped board'; fi
assert_contains "$TMP_DIR/manual-scoped.txt" 'manual project board exists outside generated manifest'
cmp -s "$ARCHITECTURE_BOARD" "$TMP_DIR/manual-scoped-board" || fail 'migration changed manual scoped board'
rm -f "$ARCHITECTURE_BOARD"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/write.txt"
assert_file "$ARCHITECTURE_BOARD"; assert_file "$WAITING_BOARD"; assert_file "$OVERVIEW"; assert_file "$MANIFEST"
assert_not_exists "$VAULT/Obsidian/Tasks-Kanban.md"
cmp -s "$VAULT/Obsidian/Projects/manual-project/Kanban.md" "$TMP_DIR/manual-project-board" || fail 'migration changed manual project board'
assert_exact_line "$OVERVIEW" '| Проект | Архипроект | Текущая задача |'
assert_exact_line "$OVERVIEW" '| --- | --- | --- |'
assert_contains "$OVERVIEW" '| [[Projects/ai-dev-architecture/Kanban\\|AI Dev Architecture]] | Дела | Current architecture task |'
assert_contains "$ARCHITECTURE_BOARD" 'ai-dev-architecture--TASK-20260826-001'
assert_contains "$WAITING_BOARD" 'waiting-project--TASK-20260826-002'
assert_board_isolated "$ARCHITECTURE_BOARD" ai-dev-architecture
assert_board_isolated "$WAITING_BOARD" waiting-project
assert_board_isolated "$VAULT/Obsidian/Projects/review-project/Kanban.md" review-project
assert_board_isolated "$VAULT/Obsidian/Projects/done-project/Kanban.md" done-project
assert_board_isolated "$VAULT/Obsidian/Projects/archived-project/Kanban.md" archived-project
assert_contains "$VAULT/Obsidian/Projects/archived-project/Kanban.md" 'archived-project--TASK-20260826-005'
assert_file "$EMPTY_BOARD"
for column in Ideas Ready Active Waiting Blocked Review Paused Done; do assert_contains "$EMPTY_BOARD" "## $column"; done
if grep -Eq '\^' "$EMPTY_BOARD"; then fail 'empty project board contains anchors'; fi
if grep -Eq '^- \[[ xX]\] ' "$EMPTY_BOARD"; then fail 'empty project board contains task cards'; fi
/usr/bin/jq -e '.format_version == 4 and (.views.projects_overview.target == "Obsidian/Projects-Overview.md") and ((.project_boards | length) > 0) and ([.project_boards[] | has("project_id") and has("target") and has("sha256")] | all)' "$MANIFEST" >/dev/null || fail 'manifest contract is invalid'
/usr/bin/jq -e '
  ([.project_boards[] | .project_id] | sort) == ["ai-dev-architecture", "archived-project", "done-project", "empty-project", "review-project", "waiting-project"] and
  ([.project_boards[] | select(.project_id == "ai-dev-architecture") | .target] == ["Obsidian/Projects/ai-dev-architecture/Kanban.md"]) and
  ([.project_boards[] | select(.project_id == "waiting-project") | .target] == ["Obsidian/Projects/waiting-project/Kanban.md"]) and
  ([.project_boards[] | select(.project_id == "empty-project") | .target] == ["Obsidian/Projects/empty-project/Kanban.md"])
' "$MANIFEST" >/dev/null || fail 'manifest project board entries are invalid'
/usr/bin/jq -e '[.project_boards[] | .sha256 | test("^[0-9a-f]{64}$")] | all' "$MANIFEST" >/dev/null || fail 'project board sha256 is invalid'
for board_spec in \
  'ai-dev-architecture Obsidian/Projects/ai-dev-architecture/Kanban.md' \
  'waiting-project Obsidian/Projects/waiting-project/Kanban.md' \
  'empty-project Obsidian/Projects/empty-project/Kanban.md' \
  'review-project Obsidian/Projects/review-project/Kanban.md' \
  'done-project Obsidian/Projects/done-project/Kanban.md' \
  'archived-project Obsidian/Projects/archived-project/Kanban.md'; do
  read -r board_id board_target <<EOF
$board_spec
EOF
  board_sha="$(shasum -a 256 "$VAULT/$board_target" | awk '{print $1}')"
  /usr/bin/jq -e --arg id "$board_id" --arg target "$board_target" --arg sha "$board_sha" \
    '[.project_boards[] | select(.project_id == $id and .target == $target and .sha256 == $sha)] | length == 1' "$MANIFEST" >/dev/null \
    || fail "project board hash mismatch: $board_id"
done
/usr/bin/jq -e '.tasks | length == 9' "$MANIFEST" >/dev/null || fail 'manifest task count is invalid'
current_sha="$(shasum -a 256 "$ARCHITECTURE_PROJECT/ai/current-task.md" | awk '{print $1}')"
/usr/bin/jq -e --arg sha "$current_sha" '[.tasks[] | select(.task_id == "TASK-20260826-001") | .source_sha256] == [$sha]' "$MANIFEST" >/dev/null || fail 'manifest source hash is not the source file hash'
future_sha="$(shasum -a 256 "$ARCHITECTURE_PROJECT/ai/future-tasks.md" | awk '{print $1}')"
/usr/bin/jq -e --arg sha "$future_sha" '[.tasks[] | select(.task_id == "FT-20260826-001") | .source_sha256] == [$sha]' "$MANIFEST" >/dev/null || fail 'future task source hash is not the source file hash'
paused_sha="$(shasum -a 256 "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" | awk '{print $1}')"
/usr/bin/jq -e --arg sha "$paused_sha" '[.tasks[] | select(.task_id == "TASK-20260820-001") | .source_sha256] == [$sha]' "$MANIFEST" >/dev/null || fail 'paused task source hash is not the source file hash'

# A v3 migration may remove the legacy board only after proving that it still
# equals the manifest. A manual edit must block before publishing any v4 file.
cp "$MANIFEST" "$TMP_DIR/v4-manifest-before-legacy-check"
cp "$OVERVIEW" "$TMP_DIR/overview-before-legacy-check"
cp "$ARCHITECTURE_BOARD" "$TMP_DIR/board-before-legacy-check"
printf '%s\n' 'valid v3 legacy board' > "$VAULT/Obsidian/Tasks-Kanban.md"
legacy_sha="$(shasum -a 256 "$VAULT/Obsidian/Tasks-Kanban.md" | awk '{print $1}')"
/usr/bin/jq --arg sha "$legacy_sha" '.format_version = 3 | .views.tasks_kanban = {target: "Obsidian/Tasks-Kanban.md", sha256: $sha}' "$MANIFEST" > "$TMP_DIR/v3-manifest.json"
mv "$TMP_DIR/v3-manifest.json" "$MANIFEST"
printf '%s\n' 'manual legacy edit' >> "$VAULT/Obsidian/Tasks-Kanban.md"
cp "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/manual-legacy-board"
if SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/manual-legacy.txt" 2>&1; then fail 'edited v3 legacy board did not block migration'; fi
assert_contains "$TMP_DIR/manual-legacy.txt" 'proposal pending: manual legacy task board edit detected'
cmp -s "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/manual-legacy-board" || fail 'blocked v3 migration changed legacy board'
cmp -s "$OVERVIEW" "$TMP_DIR/overview-before-legacy-check" || fail 'blocked v3 migration changed overview'
cmp -s "$ARCHITECTURE_BOARD" "$TMP_DIR/board-before-legacy-check" || fail 'blocked v3 migration changed project board'
cp "$TMP_DIR/v4-manifest-before-legacy-check" "$MANIFEST"
rm "$VAULT/Obsidian/Tasks-Kanban.md"

printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\ndue: 2026-08-26\n\n## Goal\n\nRefreshed architecture task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$TMP_DIR/refresh.out"
assert_contains "$TASKS" 'Refreshed architecture task'

# Replacing the generated view set is one transaction: a failed move at any
# point must leave every previously published board, overview, and manifest
# byte-for-byte intact.
mkdir -p "$TMP_DIR/fake-bin"
cat > "$TMP_DIR/fake-bin/mv" <<'EOF'
#!/bin/sh
count=0
[ ! -f "$MV_FAIL_STATE" ] || count="$(cat "$MV_FAIL_STATE")"
count=$((count + 1))
printf '%s\n' "$count" > "$MV_FAIL_STATE"
if [ "$count" -eq "$MV_FAIL_AT" ]; then
  exit 91
fi
exec /bin/mv "$@"
EOF
chmod +x "$TMP_DIR/fake-bin/mv"
PUBLISHED_FILES=("${GENERATED_FILES[@]}")
PUBLISHED_DIR="$TMP_DIR/published-set"
mkdir -p "$PUBLISHED_DIR"
for published_file in "${PUBLISHED_FILES[@]}"; do
  cp "$published_file" "$PUBLISHED_DIR/$(basename "$(dirname "$published_file")")-$(basename "$published_file")"
done
printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\ndue: 2026-08-26\n\n## Goal\n\nTransactional architecture task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
for fail_at in 1 2 3 4 5 6 7 8; do
  state="$TMP_DIR/mv-state-$fail_at"
  if PATH="$TMP_DIR/fake-bin:$PATH" MV_FAIL_STATE="$state" MV_FAIL_AT="$fail_at" SOURCE_DATE_EPOCH=1700000000 \
    "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$TMP_DIR/transaction-$fail_at.out" 2>&1; then
    fail "generated view transaction succeeded when mv $fail_at failed"
  fi
  for published_file in "${PUBLISHED_FILES[@]}"; do
    published_copy="$PUBLISHED_DIR/$(basename "$(dirname "$published_file")")-$(basename "$published_file")"
    cmp -s "$published_file" "$published_copy" || fail "published set changed after mv $fail_at failed: $published_file"
  done
done
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$TMP_DIR/transaction-success.out"
assert_contains "$TASKS" 'Transactional architecture task'

sed -i '' 's/Transactional architecture task/Manual Obsidian title/' "$TASKS"
cp "$TASKS" "$TMP_DIR/manual-edited-tasks"
cp "$OVERVIEW" "$TMP_DIR/manual-edited-overview"
cp "$MANIFEST" "$TMP_DIR/manual-edited-manifest"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$TMP_DIR/refresh-manual-task.txt" 2>&1; then fail 'manual task-board edit did not block architecture refresh'; fi
assert_contains "$TMP_DIR/refresh-manual-task.txt" 'proposal pending: manual task board edit detected'
PROPOSAL="$VAULT/.ai-architecture-sync/pending-proposal.json"
assert_file "$PROPOSAL"
/usr/bin/jq -e '
  .state == "ready" and
  (.operations == [{
    "operation": "rename",
    "task_id": "TASK-20260826-001",
    "project_id": "ai-dev-architecture",
    "from": "Transactional architecture task",
    "to": "Manual Obsidian title"
  }]) and
  (.blocked_reasons == [])
' "$PROPOSAL" >/dev/null || fail 'guarded refresh did not create the exact manual-board proposal'
cmp -s "$TASKS" "$TMP_DIR/manual-edited-tasks" || fail 'guarded refresh overwrote the manually edited task board'
cmp -s "$OVERVIEW" "$TMP_DIR/manual-edited-overview" || fail 'guarded refresh changed the overview after a manual board edit'
cmp -s "$MANIFEST" "$TMP_DIR/manual-edited-manifest" || fail 'guarded refresh changed the manifest after a manual board edit'
rm -f "$PROPOSAL"

sed -i '' 's/Manual Obsidian title/Transactional architecture task/' "$TASKS"
printf '%s\n' 'valid v3 migration board' > "$VAULT/Obsidian/Tasks-Kanban.md"
legacy_sha="$(shasum -a 256 "$VAULT/Obsidian/Tasks-Kanban.md" | awk '{print $1}')"
/usr/bin/jq --arg sha "$legacy_sha" '.format_version = 3 | .views.tasks_kanban = {target: "Obsidian/Tasks-Kanban.md", sha256: $sha}' "$MANIFEST" > "$TMP_DIR/v3-migration-manifest.json"
mv "$TMP_DIR/v3-migration-manifest.json" "$MANIFEST"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/v3-migration.txt"
/usr/bin/jq -e '.format_version == 4' "$MANIFEST" >/dev/null || fail 'confirmed v3 migration did not publish v4'
assert_not_exists "$VAULT/Obsidian/Tasks-Kanban.md"
for generated_file in "${GENERATED_FILES[@]}"; do rm -f "$generated_file"; done
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write >/dev/null

printf '\nmanual task edit\n' >> "$TASKS"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/manual-task.txt" 2>&1; then fail 'manual task-board edit did not block write'; fi
assert_contains "$TMP_DIR/manual-task.txt" 'proposal pending'
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write --replace-confirmed-board > "$TMP_DIR/unguarded-replace.txt" 2>&1; then fail 'unguarded board replacement succeeded'; fi
assert_contains "$TMP_DIR/unguarded-replace.txt" '--replace-confirmed-board requires --write --refresh-from-architecture'
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture --replace-confirmed-board > "$TMP_DIR/unconfirmed-replace.txt" 2>&1; then fail 'unconfirmed board replacement succeeded'; fi
assert_contains "$TMP_DIR/unconfirmed-replace.txt" '--replace-confirmed-board requires --write --refresh-from-architecture --confirm-generated-write'
for generated_file in "${GENERATED_FILES[@]}"; do rm -f "$generated_file"; done
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write >/dev/null
printf '\nmanual overview edit\n' >> "$OVERVIEW"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/manual-overview.txt" 2>&1; then fail 'manual overview edit did not block write'; fi
assert_contains "$TMP_DIR/manual-overview.txt" 'proposal pending'

printf '%s\n' $'### 2026-08-20 — Paused task\n\nStatus: paused' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/missing-paused-id.txt" 2>&1; then fail 'paused task without ID did not block preview'; fi
assert_contains "$TMP_DIR/missing-paused-id.txt" 'renderable paused task must have exactly one Task ID'
printf '%s\n' $'### 2026-08-20 — Paused task\n\nTask ID: TASK-20260820-001\n\nStatus: paused' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"

printf '%s\n' $'Status: active\nTask ID: BAD ID\n\n## Goal\n\nCurrent architecture task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/invalid-current-id.txt" 2>&1; then fail 'invalid current ID did not block preview'; fi
assert_contains "$TMP_DIR/invalid-current-id.txt" 'invalid Task ID'

printf '%s\n' $'Status: active\n\n## Goal\n\nCurrent architecture task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/missing-current-id.txt" 2>&1; then fail 'missing current ID did not block preview'; fi
assert_contains "$TMP_DIR/missing-current-id.txt" 'exactly one Task ID'

printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\n\n## Goal\n\nCurrent architecture task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
# The same current-task number in two projects is legal: each project numbers
# its own tasks. The card key keeps the two cards apart.
printf '%s\n' $'Status: waiting\nTask ID: TASK-20260826-001\n\n## Goal\n\nWaiting current task' > "$PROJECTS/waiting-project/ai/current-task.md"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/shared-current-id.txt"
assert_contains "$TMP_DIR/shared-current-id.txt" '- [ ] Current architecture task ^ai-dev-architecture--TASK-20260826-001'
assert_contains "$TMP_DIR/shared-current-id.txt" '- [ ] Waiting current task ^waiting-project--TASK-20260826-001'
printf '%s\n' $'Status: waiting\nTask ID: TASK-20260826-002\n\n## Goal\n\nWaiting current task' > "$PROJECTS/waiting-project/ai/current-task.md"

printf '%s\n' $'Status: active\nTask ID:   TASK-20260826-001  \n\n## Goal\n\nCurrent architecture task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' $'### 2026-08-20 — Paused task\n\nTask ID:   TASK-20260820-001  \n\nStatus: paused' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/external-whitespace.txt"
assert_contains "$TMP_DIR/external-whitespace.txt" '- [ ] Current architecture task ^ai-dev-architecture--TASK-20260826-001'
assert_contains "$TMP_DIR/external-whitespace.txt" '- [ ] Paused task ^ai-dev-architecture--TASK-20260820-001'
assert_not_contains "$TMP_DIR/external-whitespace.txt" '^ai-dev-architecture--TASK-20260826-001  '

printf '%s\n' $'### FT-20260826-001 — Duplicate future task\n\nStatus: idea' >> "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/duplicate-future-id.txt" 2>&1; then fail 'duplicate future ID did not block preview'; fi
assert_contains "$TMP_DIR/duplicate-future-id.txt" 'duplicate task ID'

printf '%s\n' $'### 2026-08-21 — Duplicate paused task\n\nTask ID: TASK-20260820-001\n\nStatus: paused' >> "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/duplicate-paused-id.txt" 2>&1; then fail 'duplicate paused ID did not block preview'; fi
assert_contains "$TMP_DIR/duplicate-paused-id.txt" 'duplicate task ID'
printf '%s\n' $'### 2026-08-20 — Paused task\n\nTask ID:   TASK-20260820-001  \n\nStatus: paused' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"

sed -i '' 's/### FT-20260826-001 — Duplicate future task/### FT-20260826-1x — Invalid future task/' "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/invalid-future-heading.txt"
assert_not_contains "$TMP_DIR/invalid-future-heading.txt" 'Invalid future task'
printf '%s\n' $'### FT-20260826-7 — Single-digit future task\n\nStatus: idea' >> "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/strict-future-heading.txt"
assert_contains "$TMP_DIR/strict-future-heading.txt" '- [ ] Single-digit future task ^ai-dev-architecture--FT-20260826-7'

# New records use a project namespace. Two projects may allocate the same UTC
# date and sequence without colliding, while legacy TASK/FT IDs stay readable.
printf '%s\n' $'Status: active\nTask ID: TASK-ai-dev-architecture-20260826-001\n\n## Goal\n\nNamespaced current task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' $'### TASK-ai-dev-architecture-20260826-002 — Namespaced future task\n\nStatus: ready' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' $'### 2026-08-20 — Namespaced paused task\n\nTask ID: TASK-ai-dev-architecture-20260826-003\n\nStatus: paused' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
printf '%s\n' $'Status: waiting\nTask ID: TASK-waiting-project-20260826-001\n\n## Goal\n\nNamespaced waiting task' > "$PROJECTS/waiting-project/ai/current-task.md"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/namespaced-ids.txt"
assert_contains "$TMP_DIR/namespaced-ids.txt" 'Namespaced current task ^ai-dev-architecture--TASK-ai-dev-architecture-20260826-001'
assert_contains "$TMP_DIR/namespaced-ids.txt" 'Namespaced future task ^ai-dev-architecture--TASK-ai-dev-architecture-20260826-002'
assert_contains "$TMP_DIR/namespaced-ids.txt" 'Namespaced paused task ^ai-dev-architecture--TASK-ai-dev-architecture-20260826-003'
assert_contains "$TMP_DIR/namespaced-ids.txt" 'Namespaced waiting task ^waiting-project--TASK-waiting-project-20260826-001'

printf '%s\n' $'Status: active\nTask ID: TASK-waiting-project-20260826-004\n\n## Goal\n\nForeign namespace task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/foreign-namespace.txt" 2>&1; then
  fail 'generator accepted a new Task ID from another project namespace'
fi
assert_contains "$TMP_DIR/foreign-namespace.txt" 'invalid Task ID for project'

# A task ID identifies a task inside its own project, never across the hub.
# Legacy FT numbers were allocated per project and know nothing about their
# neighbours, so the same number in two projects is normal data, not an error.
# The card key is the project and the task ID together, which is also what
# keeps every board anchor unique inside the single Tasks-Kanban.md file.
printf '%s\n' $'Status: active\nTask ID: TASK-ai-dev-architecture-20260826-001\n\n## Goal\n\nNamespaced current task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' $'### FT-20260826-050 — Shared number here\n\nStatus: idea' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' $'### FT-20260826-050 — Shared number there\n\nStatus: idea' > "$PROJECTS/waiting-project/ai/future-tasks.md"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/shared-number.txt"
assert_contains "$TMP_DIR/shared-number.txt" '- [ ] Shared number here ^ai-dev-architecture--FT-20260826-050'
assert_contains "$TMP_DIR/shared-number.txt" '- [ ] Shared number there ^waiting-project--FT-20260826-050'

# An explicit primary archiproject is required; tags and contribution metadata
# must never be used as an implicit fallback.
cp "$HUB/ai/project-cards/ai-dev-architecture.md" "$TMP_DIR/architecture-card.bak"
sed -i '' '/^primary_archiproject: /d' "$HUB/ai/project-cards/ai-dev-architecture.md"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/missing-primary-archiproject.txt" 2>&1; then
  fail 'missing primary archiproject did not block generation'
fi
assert_contains "$TMP_DIR/missing-primary-archiproject.txt" 'primary_archiproject'
cp "$TMP_DIR/architecture-card.bak" "$HUB/ai/project-cards/ai-dev-architecture.md"

# The same number twice inside one project is still a real collision.
printf '%s\n' $'### FT-20260826-050 — Shared number here\n\nStatus: idea\n\n### FT-20260826-050 — Same number again\n\nStatus: idea' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/same-project-duplicate.txt" 2>&1; then
  fail 'duplicate task ID inside one project did not block preview'
fi
assert_contains "$TMP_DIR/same-project-duplicate.txt" 'duplicate task ID'
printf '%s\n' $'No future tasks.' > "$PROJECTS/waiting-project/ai/future-tasks.md"

echo 'PASS: Obsidian task Kanban and project overview contract'
