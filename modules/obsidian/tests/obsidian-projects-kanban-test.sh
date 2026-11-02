#!/usr/bin/env bash
# Каждый сценарий создаёт собственные входы; подготовка не вызывает генератор.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
source "$ROOT/tests/helpers/shell-scenarios.sh"
RUN_DIR="$(mktemp -d /private/tmp/obsidian-projection.XXXXXX)"
trap 'rm -rf "$RUN_DIR"' EXIT

assert_file() { local rc; scenario_accept_exit 1 ''; scenario_exec rc test -f "$1"; scenario_assert_exit 0 "$rc"; }
assert_not_exists() { local rc; scenario_accept_exit 1 ''; scenario_exec rc test -e "$1"; scenario_assert_exit 1 "$rc"; scenario_exec rc test -L "$1"; scenario_assert_exit 1 "$rc"; }
assert_contains() { local rc; scenario_accept_exit 1 ''; scenario_exec rc grep -Fq -- "$2" "$1"; scenario_assert_exit 0 "$rc"; }
assert_not_contains() { local rc; scenario_accept_exit 1 ''; scenario_exec rc grep -Fq -- "$2" "$1"; scenario_assert_exit 1 "$rc"; }
assert_exact_line() { local rc; scenario_accept_exit 1 ''; scenario_exec rc grep -Fxq -- "$2" "$1"; scenario_assert_exit 0 "$rc"; }
assert_same() { assert_file "$1"; assert_file "$2"; local rc; scenario_accept_exit 1 ''; scenario_exec rc cmp -s "$1" "$2"; scenario_assert_exit 0 "$rc"; }
assert_equal() { local rc; scenario_accept_exit 1 ''; scenario_exec rc test "$1" = "$2"; scenario_assert_exit 0 "$rc"; }
assert_jq() { local rc; scenario_accept_exit 1 ''; scenario_exec rc /usr/bin/jq -e "$@" >/dev/null; scenario_assert_exit 0 "$rc"; }
# Сначала проверить код и весь stderr внешнего чтения, затем читать значение.
read_oracle() {
  local destination="$1" rc
  shift
  scenario_accept_exit 0 ''
  scenario_exec rc "$@" > "$destination"
  scenario_assert_exit 0 "$rc"
}
read_file_sha() {
  local __hash_target="$1" __hash_value __hash_rest
  read_oracle "$TMP_DIR/hash-value" shasum -a 256 "$2"
  IFS=' ' read -r __hash_value __hash_rest < "$TMP_DIR/hash-value"
  printf -v "$__hash_target" '%s' "$__hash_value"
}

assert_board_isolated() {
  local rc
  scenario_accept_exit 1 ''
  scenario_exec rc python3 - "$1" "$2" <<'CHECK'
import pathlib,sys
anchors=[line.split('^',1)[1] for line in pathlib.Path(sys.argv[1]).read_text().splitlines() if '^' in line]
sys.exit(0 if anchors and all(a.startswith(sys.argv[2]+'--') for a in anchors) else 1)
CHECK
  scenario_assert_exit 0 "$rc"
}

fresh_fixture() {
  TMP_DIR="$(mktemp -d "$RUN_DIR/case.XXXXXX")"
  mkdir -p "$TMP_DIR/home" "$TMP_DIR/tmp"
  export HOME="$TMP_DIR/home" TMPDIR="$TMP_DIR/tmp"
  STAGE="$TMP_DIR/stage"
  bash "$ROOT/modules/obsidian/tests/stage-scripts.sh" "$STAGE"
  GENERATOR="$STAGE/generate-obsidian-projects-kanban.sh"
  OUTPUT="$TMP_DIR/output"
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

## дела-архитектура

```yaml
id: дела-архитектура
name: Архитектура
status: active
kind: group
parent: дела
```
EOF

add_project() {
  local id="$1" name="$2" registry_status="$3" current="$4" future="$5" paused="$6"
  local group="${7:-дела}"
  local project="$PROJECTS/$id"
  mkdir -p "$project/ai"
  printf '%s\n' "$current" > "$project/ai/current-task.md"
  printf '%s\n' "$future" > "$project/ai/future-tasks.md"
  printf '%s\n' "$paused" > "$project/ai/paused-tasks.md"
  cat > "$HUB/ai/project-cards/$id.md" <<EOF
# Project Card

Project ID: $id
Name: $name
primary_archiproject: $group
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
  $'Status: active\nTask ID: TASK-20260826-001\nDue: 2026-08-26\n\n## Goal\n\nCurrent architecture task' \
  $'### FT-20260826-001 — Idea task\n\nStatus: idea\n\n### FT-20260826-002 — Ready task\n\nStatus: ready\ndue: 2026-08-28\n\n### FT-20260826-003 — Blocked task\n\nStatus: blocked\n\n### FT-20260826-004 — Promoted task\n\nStatus: promoted\n\n### FT-20260826-005 — Dropped task\n\nStatus: dropped\n\n### FT-20260826-006 — Completed future task\n\nStatus: done' \
  $'### 2026-08-20 — Paused task\n\nTask ID: TASK-20260820-001\n\nStatus: paused' \
  "дела-архитектура"
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
add_project "removed-project" "Removed project" "active" \
  $'Status: active\nTask ID: TASK-20260826-006\n\n## Goal\n\nRemoved task' $'No future tasks.' $'No paused tasks.'

  printf '%s\n' 'legacy generated board' > "$VAULT/Obsidian/Tasks-Kanban.md"
  cp "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/legacy-tasks-board"
}

# Нейтральная предыдущая публикация: независимые байты и их настоящие SHA.
# Это вход транзакции, а не результат проверяемого генератора.
seed_published() {
  python3 - "$HUB" "$VAULT" "$SCOPE" <<'FIXTURE'
import hashlib,json,pathlib,sys
hub,vault,scope=map(pathlib.Path,sys.argv[1:]); out=vault/'Obsidian'
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
boards=[]; sources=[]; tasks=[]
for project in sorted(scope.read_text().splitlines()):
    board=out/'Projects'/project/'Kanban.md'; board.parent.mkdir(parents=True,exist_ok=True)
    board.write_text('---\nkanban-plugin: board\n---\n\n## Active\n\nPrevious verified publication: '+project+'\n')
    boards.append(dict(project_id=project,target=str(board.relative_to(vault)),sha256=hashfile(board)))
    path=hub/'projects'/project; card=hub/'ai/project-cards'/(project+'.md')
    files=[card,*[path/'ai'/name for name in ('current-task.md','future-tasks.md','paused-tasks.md')]]
    aggregate=''.join(hashfile(p)+'  '+str(p)+'\n' for p in files).encode()
    sources.append(dict(id=project,registered_path=str(path),card_path=str(card),sha256=hashlib.sha256(aggregate).hexdigest()))
overview=out/'Projects-Overview.md'; overview.write_text('# Previous verified overview\n')
manifest=dict(format_version=4,generated_at='1700000000',views={'projects_overview':dict(target='Obsidian/Projects-Overview.md',sha256=hashfile(overview))},project_boards=boards,tasks=tasks,sources=sources)
(out/'AI-Architecture.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
FIXTURE
}
remove_source_project() {
  sed -i '' '/^## removed-project$/,$d' "$HUB/ai/project-registry.md"
  sed -i '' '/^removed-project$/d' "$SCOPE"
}
six_published() { fresh_fixture; remove_source_project; seed_published; }
seed_v3() {
  six_published
  printf '%s\n' 'valid v3 legacy board' > "$VAULT/Obsidian/Tasks-Kanban.md"
  local sha
  read_file_sha sha "$VAULT/Obsidian/Tasks-Kanban.md"
  /usr/bin/jq --arg sha "$sha" '.format_version = 3 | .views.tasks_kanban = {target: "Obsidian/Tasks-Kanban.md", sha256: $sha}' "$MANIFEST" > "$TMP_DIR/v3.json"
  mv "$TMP_DIR/v3.json" "$MANIFEST"
}
save_published() {
  SAVED="$TMP_DIR/saved"; mkdir "$SAVED"
  local file parent name
  for file in "${GENERATED_FILES[@]}"; do
    parent="${file%/*}"; name="${parent##*/}-${file##*/}"
    cp "$file" "$SAVED/$name"
  done
}
assert_published_unchanged() {
  local file parent name
  for file in "${GENERATED_FILES[@]}"; do
    parent="${file%/*}"; name="${parent##*/}-${file##*/}"
    assert_same "$file" "$SAVED/$name"
  done
}
run_generator() {
  local expected="$1" diagnostic="$2" rc
  shift 2
  scenario_accept_exit "$expected" "$diagnostic"
  scenario_exec rc env SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" "$@" > "$OUTPUT"
  scenario_assert_exit "$expected" "$rc"
}
preview() { run_generator 0 '' --preview; }
preview_with_rejection_contract() {
  local message="$1" rc
  scenario_accept_exit 1 "error: $message"$'\n'
  scenario_exec rc env SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$OUTPUT"
  scenario_assert_exit 0 "$rc"
}
publish() { run_generator 0 '' --write --confirm-generated-write; }
refresh() { run_generator 0 '' --write --refresh-from-architecture; }
reject() { local message="$1"; shift; run_generator 1 "error: $message"$'\n' "$@"; }
transaction_input() {
  six_published; save_published
  printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\ndue: 2026-08-26\n\n## Goal\n\nTransactional architecture task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
}
fault_commands() {
  mkdir "$TMP_DIR/fake-bin"
  cat > "$TMP_DIR/fake-bin/mv" <<'FAULT'
#!/bin/sh
set -e
if [ -n "${MV_FAIL_AT:-}" ]; then
  count=0
  [ ! -f "$MV_FAIL_STATE" ] || count="$(cat "$MV_FAIL_STATE")"
  count=$((count + 1))
  printf '%s\n' "$count" > "$MV_FAIL_STATE"
  [ "$count" -ne "$MV_FAIL_AT" ] || exit 91
fi
exec /bin/mv "$@"
FAULT
  cat > "$TMP_DIR/fake-bin/rm" <<'FAULT'
#!/bin/sh
for arg in "$@"; do [ "${RM_FAIL_TARGET:-}" != "$arg" ] || exit 92; done
exec /bin/rm "$@"
FAULT
  chmod +x "$TMP_DIR/fake-bin/mv" "$TMP_DIR/fake-bin/rm"
}

# Сначала проверить исход чтения, затем сравнивать полученные файлы.
# Неисправный find/shasum/sort не должен превращаться в неверное значение.
capture_vault_state() {
  local prefix="$1" rc
  scenario_accept_exit 0 ''
  scenario_exec rc bash -c 'set -euo pipefail; find "$1" -type f -print | sort' _ "$VAULT" > "$prefix.files"
  scenario_assert_exit 0 "$rc"
  scenario_exec rc bash -c 'set -euo pipefail; find "$1" -type f -print0 | xargs -0 shasum -a 256 | sort' _ "$VAULT" > "$prefix.hashes"
  scenario_assert_exit 0 "$rc"
}

case_preview_renders_task_and_overview_contract() {
  scenario_begin
  fresh_fixture
  capture_vault_state "$TMP_DIR/before"
  preview
  capture_vault_state "$TMP_DIR/after"
  assert_same "$TMP_DIR/before.files" "$TMP_DIR/after.files"
  assert_same "$TMP_DIR/before.hashes" "$TMP_DIR/after.hashes"
  for column in Ideas Ready Active Waiting Blocked Review Paused Done; do assert_contains "$OUTPUT" "## $column"; done
  for title in 'Idea task' 'Ready task' 'Current architecture task' 'Waiting current task' 'Blocked task' 'Review current task' 'Paused task' 'Done current task'; do assert_contains "$OUTPUT" "$title"; done
  assert_contains "$OUTPUT" '  - project: AI Dev Architecture'
  assert_contains "$OUTPUT" '- [ ] Current architecture task ^ai-dev-architecture--TASK-20260826-001'
  assert_contains "$OUTPUT" '- [ ] Idea task ^ai-dev-architecture--FT-20260826-001'
  assert_contains "$OUTPUT" '- [ ] Paused task ^ai-dev-architecture--TASK-20260820-001'
  assert_not_contains "$OUTPUT" 'Promoted task'
  assert_not_contains "$OUTPUT" 'Dropped task'
  assert_not_contains "$OUTPUT" 'Completed future task'
  assert_contains "$OUTPUT" '--- projects overview ---'
  assert_exact_line "$OUTPUT" '| Проект | Архипроект | Текущая задача |'
  assert_exact_line "$OUTPUT" '| --- | --- | --- |'
  assert_contains "$OUTPUT" '| [[Projects/ai-dev-architecture/Kanban\|AI Dev Architecture]] | Архитектура | Current architecture task |'
  assert_not_contains "$OUTPUT" '| Project | Status | Current task | Ready | Waiting | Due |'
  assert_not_contains "$OUTPUT" '| Проект | Статус | Текущая задача | Ready | Waiting | Due |'
  assert_not_contains "$OUTPUT" '| Проект | Архипроект | Текущая задача | Status'
  assert_not_contains "$OUTPUT" '| Проект | Архипроект | Текущая задача | Ready'
  assert_not_contains "$OUTPUT" '| Проект | Архипроект | Текущая задача | Waiting'
  assert_not_contains "$OUTPUT" '| Проект | Архипроект | Текущая задача | Due'
  assert_contains "$OUTPUT" '"format_version": 4'
  scenario_pass
}

case_write_requires_confirmation() {
  scenario_begin
  fresh_fixture
  reject 'write requires --confirm-generated-write' --write
  assert_same "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/legacy-tasks-board"
  local path
  for path in "$VAULT/Obsidian/Projects" "$ARCHITECTURE_BOARD" "$WAITING_BOARD" "$OVERVIEW" "$MANIFEST"; do assert_not_exists "$path"; done
  scenario_pass
}

case_rejects_symlink_projects_dir() {
  scenario_begin
  fresh_fixture
  mkdir "$TMP_DIR/outside"; ln -s "$TMP_DIR/outside" "$VAULT/Obsidian/Projects"
  reject 'Projects directory must be a real non-symlink directory' --write --confirm-generated-write
  scenario_pass
}

case_rejects_symlink_project_board_dir() {
  scenario_begin
  fresh_fixture
  mkdir -p "$TMP_DIR/outside" "$VAULT/Obsidian/Projects"
  ln -s "$TMP_DIR/outside" "$VAULT/Obsidian/Projects/empty-project"
  reject 'project board directory is unsafe: empty-project' --write --confirm-generated-write
  scenario_pass
}

case_rejects_symlink_board_target() {
  scenario_begin
  six_published
  cp "$EMPTY_BOARD" "$TMP_DIR/outside"
  rm "$EMPTY_BOARD"
  ln -s "$TMP_DIR/outside" "$EMPTY_BOARD"
  reject 'generated targets must not be symlinks' --write --confirm-generated-write
  scenario_pass
}

case_preserves_unmanifested_manual_project_board() {
  scenario_begin
  fresh_fixture
  mkdir -p "$(dirname "$TASKS")"; printf '%s\n' 'manual scoped board' > "$TASKS"
  cp "$TASKS" "$TMP_DIR/manual"
  reject 'proposal pending: manual project board exists outside generated manifest' --write --confirm-generated-write
  assert_same "$TASKS" "$TMP_DIR/manual"
  scenario_pass
}

case_initial_v4_publish_and_isolated_boards() {
  scenario_begin
  fresh_fixture
  mkdir -p "$VAULT/Obsidian/Projects/manual-project"
  printf '%s\n' 'manual project board' > "$VAULT/Obsidian/Projects/manual-project/Kanban.md"
  cp "$VAULT/Obsidian/Projects/manual-project/Kanban.md" "$TMP_DIR/manual-project-board"
  publish
assert_file "$ARCHITECTURE_BOARD"; assert_file "$WAITING_BOARD"; assert_file "$OVERVIEW"; assert_file "$MANIFEST"
assert_same "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/legacy-tasks-board"
assert_same "$VAULT/Obsidian/Projects/manual-project/Kanban.md" "$TMP_DIR/manual-project-board"
assert_exact_line "$OVERVIEW" '| Проект | Архипроект | Текущая задача |'
assert_exact_line "$OVERVIEW" '| --- | --- | --- |'
assert_contains "$OVERVIEW" '| [[Projects/ai-dev-architecture/Kanban\|AI Dev Architecture]] | Архитектура | Current architecture task |'
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
assert_not_contains "$EMPTY_BOARD" '^'
assert_not_contains "$EMPTY_BOARD" '- [ ] '; assert_not_contains "$EMPTY_BOARD" '- [x] '; assert_not_contains "$EMPTY_BOARD" '- [X] '
assert_jq '.format_version == 4 and (.views.projects_overview.target == "Obsidian/Projects-Overview.md") and ((.project_boards | length) > 0) and ([.project_boards[] | has("project_id") and has("target") and has("sha256")] | all)' "$MANIFEST"
assert_jq '
  ([.project_boards[] | .project_id] | sort) == ["ai-dev-architecture", "archived-project", "done-project", "empty-project", "removed-project", "review-project", "waiting-project"] and
  ([.project_boards[] | select(.project_id == "ai-dev-architecture") | .target] == ["Obsidian/Projects/ai-dev-architecture/Kanban.md"]) and
  ([.project_boards[] | select(.project_id == "waiting-project") | .target] == ["Obsidian/Projects/waiting-project/Kanban.md"]) and
  ([.project_boards[] | select(.project_id == "empty-project") | .target] == ["Obsidian/Projects/empty-project/Kanban.md"])
' "$MANIFEST"
assert_jq '[.project_boards[] | .sha256 | test("^[0-9a-f]{64}$")] | all' "$MANIFEST"
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
  read_file_sha board_sha "$VAULT/$board_target"
  assert_jq --arg id "$board_id" --arg target "$board_target" --arg sha "$board_sha" \
    '[.project_boards[] | select(.project_id == $id and .target == $target and .sha256 == $sha)] | length == 1' "$MANIFEST"
done
assert_jq '.tasks | length == 10' "$MANIFEST"
read_file_sha current_sha "$ARCHITECTURE_PROJECT/ai/current-task.md"
assert_jq --arg sha "$current_sha" '[.tasks[] | select(.task_id == "TASK-20260826-001") | .source_sha256] == [$sha]' "$MANIFEST"
read_file_sha future_sha "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
assert_jq --arg sha "$future_sha" '[.tasks[] | select(.task_id == "FT-20260826-001") | .source_sha256] == [$sha]' "$MANIFEST"
read_file_sha paused_sha "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
assert_jq --arg sha "$paused_sha" '[.tasks[] | select(.task_id == "TASK-20260820-001") | .source_sha256] == [$sha]' "$MANIFEST"
  scenario_pass
}

case_refresh_removes_only_verified_retired_board() {
  scenario_begin
  fresh_fixture; seed_published; remove_source_project
  mkdir -p "$VAULT/Obsidian/Projects/unlisted-project"
  printf '%s\n' 'manual unlisted board' > "$VAULT/Obsidian/Projects/unlisted-project/Kanban.md"
  cp "$VAULT/Obsidian/Projects/unlisted-project/Kanban.md" "$TMP_DIR/manual"
  refresh
  assert_not_exists "$VAULT/Obsidian/Projects/removed-project/Kanban.md"
  assert_same "$VAULT/Obsidian/Projects/unlisted-project/Kanban.md" "$TMP_DIR/manual"
  assert_jq '[.project_boards[] | select(.project_id == "removed-project")] | length == 0' "$MANIFEST"
  scenario_pass
}

case_edited_v3_legacy_blocks_migration() {
  scenario_begin
  seed_v3; save_published
  printf '%s\n' 'manual legacy edit' >> "$VAULT/Obsidian/Tasks-Kanban.md"
  cp "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/manual"
  reject 'proposal pending: manual legacy task board edit detected' --write --confirm-generated-write
  assert_same "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/manual"
  assert_published_unchanged
  scenario_pass
}

case_refresh_publishes_canonical_title_change() {
  scenario_begin
  six_published
  sed -i '' 's/Current architecture task/Refreshed architecture task/' "$ARCHITECTURE_PROJECT/ai/current-task.md"
  refresh
  assert_contains "$TASKS" 'Refreshed architecture task'
  scenario_pass
}

case_transaction_rolls_back_move_1() {
  scenario_begin
  transaction_input; fault_commands
  local rc
  scenario_accept_exit 91 ''
  scenario_exec rc env PATH="$TMP_DIR/fake-bin:$PATH" MV_FAIL_STATE="$TMP_DIR/mv-state" MV_FAIL_AT=1 SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$OUTPUT"
  scenario_assert_exit 91 "$rc"
  assert_published_unchanged
  scenario_pass
}

case_transaction_rolls_back_move_2() {
  scenario_begin
  transaction_input; fault_commands
  local rc
  scenario_accept_exit 91 ''
  scenario_exec rc env PATH="$TMP_DIR/fake-bin:$PATH" MV_FAIL_STATE="$TMP_DIR/mv-state" MV_FAIL_AT=2 SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$OUTPUT"
  scenario_assert_exit 91 "$rc"
  assert_published_unchanged
  scenario_pass
}

case_transaction_rolls_back_move_3() {
  scenario_begin
  transaction_input; fault_commands
  local rc
  scenario_accept_exit 91 ''
  scenario_exec rc env PATH="$TMP_DIR/fake-bin:$PATH" MV_FAIL_STATE="$TMP_DIR/mv-state" MV_FAIL_AT=3 SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$OUTPUT"
  scenario_assert_exit 91 "$rc"
  assert_published_unchanged
  scenario_pass
}

case_transaction_rolls_back_move_4() {
  scenario_begin
  transaction_input; fault_commands
  local rc
  scenario_accept_exit 91 ''
  scenario_exec rc env PATH="$TMP_DIR/fake-bin:$PATH" MV_FAIL_STATE="$TMP_DIR/mv-state" MV_FAIL_AT=4 SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$OUTPUT"
  scenario_assert_exit 91 "$rc"
  assert_published_unchanged
  scenario_pass
}

case_transaction_rolls_back_move_5() {
  scenario_begin
  transaction_input; fault_commands
  local rc
  scenario_accept_exit 91 ''
  scenario_exec rc env PATH="$TMP_DIR/fake-bin:$PATH" MV_FAIL_STATE="$TMP_DIR/mv-state" MV_FAIL_AT=5 SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$OUTPUT"
  scenario_assert_exit 91 "$rc"
  assert_published_unchanged
  scenario_pass
}

case_transaction_rolls_back_move_6() {
  scenario_begin
  transaction_input; fault_commands
  local rc
  scenario_accept_exit 91 ''
  scenario_exec rc env PATH="$TMP_DIR/fake-bin:$PATH" MV_FAIL_STATE="$TMP_DIR/mv-state" MV_FAIL_AT=6 SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$OUTPUT"
  scenario_assert_exit 91 "$rc"
  assert_published_unchanged
  scenario_pass
}

case_transaction_rolls_back_move_7() {
  scenario_begin
  transaction_input; fault_commands
  local rc
  scenario_accept_exit 91 ''
  scenario_exec rc env PATH="$TMP_DIR/fake-bin:$PATH" MV_FAIL_STATE="$TMP_DIR/mv-state" MV_FAIL_AT=7 SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$OUTPUT"
  scenario_assert_exit 91 "$rc"
  assert_published_unchanged
  scenario_pass
}

case_transaction_rolls_back_move_8() {
  scenario_begin
  transaction_input; fault_commands
  local rc
  scenario_accept_exit 91 ''
  scenario_exec rc env PATH="$TMP_DIR/fake-bin:$PATH" MV_FAIL_STATE="$TMP_DIR/mv-state" MV_FAIL_AT=8 SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$OUTPUT"
  scenario_assert_exit 91 "$rc"
  assert_published_unchanged
  scenario_pass
}

case_transaction_success_publishes_new_set() {
  scenario_begin
  transaction_input
  refresh
  assert_contains "$TASKS" 'Transactional architecture task'
  scenario_pass
}

case_manual_board_edit_blocks_refresh() {
  scenario_begin
  six_published
  printf '\nmanual task edit\n' >> "$TASKS"; save_published
  reject 'proposal pending: manual task board edit detected; run obsidian-task-sync.sh scan to create a proposal' --write --refresh-from-architecture
  assert_not_exists "$VAULT/.ai-architecture-sync/pending-proposal.json"
  assert_published_unchanged
  scenario_pass
}

case_v3_delete_failure_rolls_back_entire_set() {
  scenario_begin
  seed_v3; save_published; fault_commands
  cp "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/legacy"
  local rc
  scenario_accept_exit 92 ''
  scenario_exec rc env PATH="$TMP_DIR/fake-bin:$PATH" RM_FAIL_TARGET="$VAULT/Obsidian/Tasks-Kanban.md" SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$OUTPUT"
  scenario_assert_exit 92 "$rc"
  assert_published_unchanged
  assert_same "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/legacy"
  scenario_pass
}

case_confirmed_v3_migration_removes_verified_legacy() {
  scenario_begin
  seed_v3; publish
  assert_jq '.format_version == 4' "$MANIFEST"
  assert_not_exists "$VAULT/Obsidian/Tasks-Kanban.md"
  scenario_pass
}

case_v4_refresh_preserves_new_manual_legacy() {
  scenario_begin
  six_published
  printf '%s\n' 'manual post-v4 legacy board' > "$VAULT/Obsidian/Tasks-Kanban.md"
  cp "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/manual"
  refresh
  assert_same "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/manual"
  scenario_pass
}

case_fresh_v4_publish_preserves_manual_legacy() {
  scenario_begin
  fresh_fixture; publish
  assert_same "$VAULT/Obsidian/Tasks-Kanban.md" "$TMP_DIR/legacy-tasks-board"
  scenario_pass
}

case_manual_task_edit_blocks_write() {
  scenario_begin
  six_published
  printf '\nmanual task edit\n' >> "$TASKS"; save_published
  reject 'proposal pending: manual task board edit detected; run obsidian-task-sync.sh scan to create a proposal' --write --confirm-generated-write
  assert_published_unchanged
  scenario_pass
}

case_replace_needs_refresh() {
  scenario_begin
  fresh_fixture
  reject '--replace-confirmed-board requires --write --refresh-from-architecture --confirm-generated-write' --write --confirm-generated-write --replace-confirmed-board
  scenario_pass
}

case_replace_needs_confirmation() {
  scenario_begin
  fresh_fixture
  reject '--replace-confirmed-board requires --write --refresh-from-architecture --confirm-generated-write' --write --refresh-from-architecture --replace-confirmed-board
  scenario_pass
}

case_manual_overview_edit_blocks_write() {
  scenario_begin
  six_published
  printf '\nmanual overview edit\n' >> "$OVERVIEW"; save_published
  reject 'proposal pending: manual project overview edit detected' --write --confirm-generated-write
  assert_published_unchanged
  scenario_pass
}

case_rejects_paused_record_without_id() {
  scenario_begin
  fresh_fixture
  printf '%s\n' $'### 2026-08-20 — Paused task\n\nStatus: paused' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
  run_generator 1 "error: renderable paused task must have exactly one Task ID: $ARCHITECTURE_PROJECT/ai/paused-tasks.md"'\n' --preview
  scenario_pass
}

case_rejects_invalid_current_id() {
  scenario_begin
  fresh_fixture
  sed -i '' 's/TASK-20260826-001/BAD ID/' "$ARCHITECTURE_PROJECT/ai/current-task.md"
  reject "invalid Task ID for project ai-dev-architecture: $ARCHITECTURE_PROJECT/ai/current-task.md" --preview
  scenario_pass
}

case_rejects_missing_current_id() {
  scenario_begin
  fresh_fixture
  sed -i '' '/^Task ID: /d' "$ARCHITECTURE_PROJECT/ai/current-task.md"
  reject "renderable current task must have exactly one Task ID: $ARCHITECTURE_PROJECT/ai/current-task.md" --preview
  scenario_pass
}

case_allows_shared_current_number_between_projects() {
  scenario_begin
  fresh_fixture
  sed -i '' 's/TASK-20260826-002/TASK-20260826-001/' "$PROJECTS/waiting-project/ai/current-task.md"
  preview_with_rejection_contract "duplicate task ID in renderable tasks"
  assert_contains "$OUTPUT" '- [ ] Current architecture task ^ai-dev-architecture--TASK-20260826-001'
  assert_contains "$OUTPUT" '- [ ] Waiting current task ^waiting-project--TASK-20260826-001'
  scenario_pass
}

case_trims_external_task_id_whitespace() {
  scenario_begin
  fresh_fixture
  sed -i '' 's/Task ID: TASK-/Task ID:   TASK-/; s/001$/001  /' "$ARCHITECTURE_PROJECT/ai/current-task.md" "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
  preview_with_rejection_contract "invalid Task ID for project ai-dev-architecture: $ARCHITECTURE_PROJECT/ai/current-task.md"
  assert_exact_line "$OUTPUT" '- [ ] Current architecture task ^ai-dev-architecture--TASK-20260826-001'
  assert_exact_line "$OUTPUT" '- [ ] Paused task ^ai-dev-architecture--TASK-20260820-001'
  assert_not_contains "$OUTPUT" '^ai-dev-architecture--TASK-20260826-001  '
  scenario_pass
}

case_rejects_duplicate_future_id() {
  scenario_begin
  fresh_fixture
  printf '%s\n' $'### FT-20260826-001 — Duplicate future task\n\nStatus: idea' >> "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
  reject 'duplicate task ID in renderable tasks' --preview
  scenario_pass
}

case_rejects_duplicate_paused_id() {
  scenario_begin
  fresh_fixture
  printf '%s\n' $'### 2026-08-21 — Duplicate paused task\n\nTask ID: TASK-20260820-001\n\nStatus: paused' >> "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
  reject 'duplicate task ID in renderable tasks' --preview
  scenario_pass
}

case_ignores_malformed_future_heading() {
  scenario_begin
  fresh_fixture
  printf '%s\n' $'### FT-20260826-1x — Invalid future task\n\nStatus: idea' >> "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
  preview
  assert_not_contains "$OUTPUT" 'Invalid future task'
  scenario_pass
}

case_allows_single_digit_future_id() {
  scenario_begin
  fresh_fixture
  printf '%s\n' $'### FT-20260826-7 — Single-digit future task\n\nStatus: idea' >> "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
  preview
  assert_exact_line "$OUTPUT" '- [ ] Single-digit future task ^ai-dev-architecture--FT-20260826-7'
  scenario_pass
}

case_renders_project_namespaced_task_ids() {
  scenario_begin
  fresh_fixture
  printf '%s\n' $'Status: active\nTask ID: TASK-ai-dev-architecture-20260826-001\n\n## Goal\n\nNamespaced current task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
  printf '%s\n' $'### TASK-ai-dev-architecture-20260826-002 — Namespaced future task\n\nStatus: ready' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
  printf '%s\n' $'### 2026-08-20 — Namespaced paused task\n\nTask ID: TASK-ai-dev-architecture-20260826-003\n\nStatus: paused' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
  printf '%s\n' $'Status: waiting\nTask ID: TASK-waiting-project-20260826-001\n\n## Goal\n\nNamespaced waiting task' > "$PROJECTS/waiting-project/ai/current-task.md"
  preview
  assert_contains "$OUTPUT" 'Namespaced current task ^ai-dev-architecture--TASK-ai-dev-architecture-20260826-001'
  assert_contains "$OUTPUT" 'Namespaced future task ^ai-dev-architecture--TASK-ai-dev-architecture-20260826-002'
  assert_contains "$OUTPUT" 'Namespaced paused task ^ai-dev-architecture--TASK-ai-dev-architecture-20260826-003'
  assert_contains "$OUTPUT" 'Namespaced waiting task ^waiting-project--TASK-waiting-project-20260826-001'
  scenario_pass
}

case_rejects_foreign_task_namespace() {
  scenario_begin
  fresh_fixture
  sed -i '' 's/TASK-20260826-001/TASK-waiting-project-20260826-004/' "$ARCHITECTURE_PROJECT/ai/current-task.md"
  reject "invalid Task ID for project ai-dev-architecture: $ARCHITECTURE_PROJECT/ai/current-task.md" --preview
  scenario_pass
}

case_allows_shared_future_number_between_projects() {
  scenario_begin
  fresh_fixture
  printf '%s\n' $'### FT-20260826-050 — Shared number here\n\nStatus: idea' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
  printf '%s\n' $'### FT-20260826-050 — Shared number there\n\nStatus: idea' > "$PROJECTS/waiting-project/ai/future-tasks.md"
  preview_with_rejection_contract "duplicate task ID in renderable tasks"
  assert_exact_line "$OUTPUT" '- [ ] Shared number here ^ai-dev-architecture--FT-20260826-050'
  assert_exact_line "$OUTPUT" '- [ ] Shared number there ^waiting-project--FT-20260826-050'
  scenario_pass
}

case_explicit_none_primary_group() {
  scenario_begin
  fresh_fixture
  sed -i '' 's/^primary_archiproject: дела-архитектура$/primary_archiproject: none/' "$HUB/ai/project-cards/ai-dev-architecture.md"
  preview
  assert_exact_line "$OUTPUT" '| [[Projects/ai-dev-architecture/Kanban\|AI Dev Architecture]] | — | Current architecture task |'
  scenario_pass
}

case_rejects_missing_primary_group() {
  scenario_begin
  fresh_fixture
  sed -i '' '/^primary_archiproject: /d' "$HUB/ai/project-cards/ai-dev-architecture.md"
  reject 'project card must declare primary_archiproject' --preview
  scenario_pass
}

case_rejects_duplicate_future_within_project() {
  scenario_begin
  fresh_fixture
  printf '%s\n' $'### FT-20260826-050 — Shared number here\n\nStatus: idea\n\n### FT-20260826-050 — Same number again\n\nStatus: idea' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
  reject 'duplicate task ID in renderable tasks' --preview
  scenario_pass
}

scenario_declare preview-renders-task-and-overview-contract case_preview_renders_task_and_overview_contract
scenario_declare write-requires-confirmation case_write_requires_confirmation
scenario_declare rejects-symlink-projects-dir case_rejects_symlink_projects_dir
scenario_declare rejects-symlink-project-board-dir case_rejects_symlink_project_board_dir
scenario_declare rejects-symlink-board-target case_rejects_symlink_board_target
scenario_declare preserves-unmanifested-manual-project-board case_preserves_unmanifested_manual_project_board
scenario_declare initial-v4-publish-and-isolated-boards case_initial_v4_publish_and_isolated_boards
scenario_declare refresh-removes-only-verified-retired-board case_refresh_removes_only_verified_retired_board
scenario_declare edited-v3-legacy-blocks-migration case_edited_v3_legacy_blocks_migration
scenario_declare refresh-publishes-canonical-title-change case_refresh_publishes_canonical_title_change
scenario_declare transaction-rolls-back-move-1 case_transaction_rolls_back_move_1
scenario_declare transaction-rolls-back-move-2 case_transaction_rolls_back_move_2
scenario_declare transaction-rolls-back-move-3 case_transaction_rolls_back_move_3
scenario_declare transaction-rolls-back-move-4 case_transaction_rolls_back_move_4
scenario_declare transaction-rolls-back-move-5 case_transaction_rolls_back_move_5
scenario_declare transaction-rolls-back-move-6 case_transaction_rolls_back_move_6
scenario_declare transaction-rolls-back-move-7 case_transaction_rolls_back_move_7
scenario_declare transaction-rolls-back-move-8 case_transaction_rolls_back_move_8
scenario_declare transaction-success-publishes-new-set case_transaction_success_publishes_new_set
scenario_declare manual-board-edit-blocks-refresh case_manual_board_edit_blocks_refresh
scenario_declare v3-delete-failure-rolls-back-entire-set case_v3_delete_failure_rolls_back_entire_set
scenario_declare confirmed-v3-migration-removes-verified-legacy case_confirmed_v3_migration_removes_verified_legacy
scenario_declare v4-refresh-preserves-new-manual-legacy case_v4_refresh_preserves_new_manual_legacy
scenario_declare fresh-v4-publish-preserves-manual-legacy case_fresh_v4_publish_preserves_manual_legacy
scenario_declare manual-task-edit-blocks-write case_manual_task_edit_blocks_write
scenario_declare replace-needs-refresh case_replace_needs_refresh
scenario_declare replace-needs-confirmation case_replace_needs_confirmation
scenario_declare manual-overview-edit-blocks-write case_manual_overview_edit_blocks_write
scenario_declare rejects-paused-record-without-id case_rejects_paused_record_without_id
scenario_declare rejects-invalid-current-id case_rejects_invalid_current_id
scenario_declare rejects-missing-current-id case_rejects_missing_current_id
scenario_declare allows-shared-current-number-between-projects case_allows_shared_current_number_between_projects
scenario_declare trims-external-task-id-whitespace case_trims_external_task_id_whitespace
scenario_declare rejects-duplicate-future-id case_rejects_duplicate_future_id
scenario_declare rejects-duplicate-paused-id case_rejects_duplicate_paused_id
scenario_declare ignores-malformed-future-heading case_ignores_malformed_future_heading
scenario_declare allows-single-digit-future-id case_allows_single_digit_future_id
scenario_declare renders-project-namespaced-task-ids case_renders_project_namespaced_task_ids
scenario_declare rejects-foreign-task-namespace case_rejects_foreign_task_namespace
scenario_declare allows-shared-future-number-between-projects case_allows_shared_future_number_between_projects
scenario_declare explicit-none-primary-group case_explicit_none_primary_group
scenario_declare rejects-missing-primary-group case_rejects_missing_primary_group
scenario_declare rejects-duplicate-future-within-project case_rejects_duplicate_future_within_project
scenario_main "$@"
