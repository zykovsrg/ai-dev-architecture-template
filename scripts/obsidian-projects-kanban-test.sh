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

HUB="$TMP_DIR/hub"
PROJECTS="$HUB/projects"
ARCHITECTURE_PROJECT="$PROJECTS/ai-dev-architecture"
VAULT="$ARCHITECTURE_PROJECT/obsidian-vault"
SCOPE="$HUB/scope.txt"
TASKS="$VAULT/Obsidian/Tasks-Kanban.md"
OVERVIEW="$VAULT/Obsidian/Projects-Overview.md"
MANIFEST="$VAULT/Obsidian/AI-Architecture.manifest.json"
mkdir -p "$HUB/ai/project-cards" "$PROJECTS" "$VAULT/Obsidian"
printf '%s\n' '# Project Registry' > "$HUB/ai/project-registry.md"

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

add_project "ai-dev-architecture" "Architecture project" "active" \
  $'Status: active\nTask ID: TASK-20260826-001\ndue: 2026-08-26\n\n## Goal\n\nCurrent architecture task' \
  $'### FT-20260826-001 — Idea task\n\nStatus: idea\n\n### FT-20260826-002 — Ready task\n\nStatus: ready\ndue: 2026-08-28\n\n### FT-20260826-003 — Blocked task\n\nStatus: blocked\n\n### FT-20260826-004 — Promoted task\n\nStatus: promoted\n\n### FT-20260826-005 — Dropped task\n\nStatus: dropped\n\n### FT-20260826-006 — Completed future task\n\nStatus: done' \
  $'### 2026-08-20 — Paused task\n\nTask ID: TASK-20260820-001\n\nStatus: paused'
add_project "waiting-project" "Waiting project" "active" \
  $'Status: waiting\nTask ID: TASK-20260826-002\n\n## Goal\n\nWaiting current task' $'No future tasks.' $'No paused tasks.'
add_project "review-project" "Review project" "active" \
  $'Status: review\nTask ID: TASK-20260826-003\n\n## Goal\n\nReview current task' $'No future tasks.' $'No paused tasks.'
add_project "done-project" "Done project" "completed" \
  $'Status: done\nTask ID: TASK-20260826-004\n\n## Goal\n\nDone current task' $'No future tasks.' $'No paused tasks.'

before_files="$(find "$VAULT" -type f -print | sort)"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/preview.txt"
[ "$before_files" = "$(find "$VAULT" -type f -print | sort)" ] || fail 'preview created files'
for column in Ideas Ready Active Waiting Blocked Review Paused Done; do assert_contains "$TMP_DIR/preview.txt" "## $column"; done
for title in 'Idea task' 'Ready task' 'Current architecture task' 'Waiting current task' 'Blocked task' 'Review current task' 'Paused task' 'Done current task'; do assert_contains "$TMP_DIR/preview.txt" "$title"; done
assert_contains "$TMP_DIR/preview.txt" '  - project: Architecture project'
assert_contains "$TMP_DIR/preview.txt" '- [ ] Current architecture task ^ai-dev-architecture--TASK-20260826-001'
assert_contains "$TMP_DIR/preview.txt" '- [ ] Idea task ^ai-dev-architecture--FT-20260826-001'
assert_contains "$TMP_DIR/preview.txt" '- [ ] Paused task ^ai-dev-architecture--TASK-20260820-001'
assert_not_contains "$TMP_DIR/preview.txt" 'Promoted task'
assert_not_contains "$TMP_DIR/preview.txt" 'Dropped task'
assert_not_contains "$TMP_DIR/preview.txt" 'Completed future task'
assert_contains "$TMP_DIR/preview.txt" '--- projects overview ---'
assert_contains "$TMP_DIR/preview.txt" '| Project | Status | Current task | Ready | Waiting | Due |'
assert_contains "$TMP_DIR/preview.txt" '| Architecture project | active | Current architecture task | 1 | 0 | 2026-08-26 |'
assert_contains "$TMP_DIR/preview.txt" '| Waiting project | active | Waiting current task | 0 | 1 | — |'
assert_contains "$TMP_DIR/preview.txt" '"format_version": 3'

if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write > "$TMP_DIR/no-confirm.txt" 2>&1; then fail 'write without confirmation succeeded'; fi
assert_not_exists "$TASKS"; assert_not_exists "$OVERVIEW"; assert_not_exists "$MANIFEST"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/write.txt"
assert_file "$TASKS"; assert_file "$OVERVIEW"; assert_file "$MANIFEST"
/usr/bin/jq -e '.format_version == 3 and (.views.tasks_kanban.target == "Obsidian/Tasks-Kanban.md") and (.views.projects_overview.target == "Obsidian/Projects-Overview.md") and ([.tasks[] | has("task_id") and has("project_id") and has("source_file") and has("source_sha256")] | all)' "$MANIFEST" >/dev/null || fail 'manifest contract is invalid'
/usr/bin/jq -e '.tasks | length == 8' "$MANIFEST" >/dev/null || fail 'manifest task count is invalid'
current_sha="$(shasum -a 256 "$ARCHITECTURE_PROJECT/ai/current-task.md" | awk '{print $1}')"
/usr/bin/jq -e --arg sha "$current_sha" '[.tasks[] | select(.task_id == "TASK-20260826-001") | .source_sha256] == [$sha]' "$MANIFEST" >/dev/null || fail 'manifest source hash is not the source file hash'
future_sha="$(shasum -a 256 "$ARCHITECTURE_PROJECT/ai/future-tasks.md" | awk '{print $1}')"
/usr/bin/jq -e --arg sha "$future_sha" '[.tasks[] | select(.task_id == "FT-20260826-001") | .source_sha256] == [$sha]' "$MANIFEST" >/dev/null || fail 'future task source hash is not the source file hash'
paused_sha="$(shasum -a 256 "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" | awk '{print $1}')"
/usr/bin/jq -e --arg sha "$paused_sha" '[.tasks[] | select(.task_id == "TASK-20260820-001") | .source_sha256] == [$sha]' "$MANIFEST" >/dev/null || fail 'paused task source hash is not the source file hash'

printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\ndue: 2026-08-26\n\n## Goal\n\nRefreshed architecture task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$TMP_DIR/refresh.out"
assert_contains "$TASKS" 'Refreshed architecture task'

# Replacing the generated view set is one transaction: a failed move at any
# point must leave all three previously published files byte-for-byte intact.
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
cp "$TASKS" "$TMP_DIR/published-tasks"
cp "$OVERVIEW" "$TMP_DIR/published-overview"
cp "$MANIFEST" "$TMP_DIR/published-manifest"
printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\ndue: 2026-08-26\n\n## Goal\n\nTransactional architecture task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
for fail_at in 1 2 3; do
  state="$TMP_DIR/mv-state-$fail_at"
  if PATH="$TMP_DIR/fake-bin:$PATH" MV_FAIL_STATE="$state" MV_FAIL_AT="$fail_at" SOURCE_DATE_EPOCH=1700000000 \
    "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$TMP_DIR/transaction-$fail_at.out" 2>&1; then
    fail "generated view transaction succeeded when mv $fail_at failed"
  fi
  cmp -s "$TASKS" "$TMP_DIR/published-tasks" || fail "task board changed after mv $fail_at failed"
  cmp -s "$OVERVIEW" "$TMP_DIR/published-overview" || fail "project overview changed after mv $fail_at failed"
  cmp -s "$MANIFEST" "$TMP_DIR/published-manifest" || fail "manifest changed after mv $fail_at failed"
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

sed -i '' 's/"format_version": 3/"format_version": 2/' "$MANIFEST"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/v2-manifest.txt" 2>&1; then fail 'v2 manifest did not block write'; fi
assert_contains "$TMP_DIR/v2-manifest.txt" 'manifest v2 requires a fresh confirmed rebuild'
rm -f "$TASKS" "$OVERVIEW" "$MANIFEST"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write >/dev/null

printf '\nmanual task edit\n' >> "$TASKS"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/manual-task.txt" 2>&1; then fail 'manual task-board edit did not block write'; fi
assert_contains "$TMP_DIR/manual-task.txt" 'proposal pending'
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write --replace-confirmed-board > "$TMP_DIR/unguarded-replace.txt" 2>&1; then fail 'unguarded board replacement succeeded'; fi
assert_contains "$TMP_DIR/unguarded-replace.txt" '--replace-confirmed-board requires --write --refresh-from-architecture'
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture --replace-confirmed-board > "$TMP_DIR/unconfirmed-replace.txt" 2>&1; then fail 'unconfirmed board replacement succeeded'; fi
assert_contains "$TMP_DIR/unconfirmed-replace.txt" '--replace-confirmed-board requires --write --refresh-from-architecture --confirm-generated-write'
rm -f "$TASKS" "$OVERVIEW" "$MANIFEST"
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

# The same number twice inside one project is still a real collision.
printf '%s\n' $'### FT-20260826-050 — Shared number here\n\nStatus: idea\n\n### FT-20260826-050 — Same number again\n\nStatus: idea' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/same-project-duplicate.txt" 2>&1; then
  fail 'duplicate task ID inside one project did not block preview'
fi
assert_contains "$TMP_DIR/same-project-duplicate.txt" 'duplicate task ID'
printf '%s\n' $'No future tasks.' > "$PROJECTS/waiting-project/ai/future-tasks.md"

echo 'PASS: Obsidian task Kanban and project overview contract'
