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
  $'Status: active\ndue: 2026-08-26\n\n## Goal\n\nCurrent architecture task' \
  $'### FT-20260826-001 — Idea task\n\nStatus: idea\n\n### FT-20260826-002 — Ready task\n\nStatus: ready\ndue: 2026-08-28\n\n### FT-20260826-003 — Blocked task\n\nStatus: blocked\n\n### FT-20260826-004 — Promoted task\n\nStatus: promoted\n\n### FT-20260826-005 — Dropped task\n\nStatus: dropped\n\n### FT-20260826-006 — Completed future task\n\nStatus: done' \
  $'### 2026-08-20 — Paused task\n\nStatus: paused'
add_project "waiting-project" "Waiting project" "active" \
  $'Status: waiting\n\n## Goal\n\nWaiting current task' $'No future tasks.' $'No paused tasks.'
add_project "review-project" "Review project" "active" \
  $'Status: review\n\n## Goal\n\nReview current task' $'No future tasks.' $'No paused tasks.'
add_project "done-project" "Done project" "completed" \
  $'Status: done\n\n## Goal\n\nDone current task' $'No future tasks.' $'No paused tasks.'

before_files="$(find "$VAULT" -type f -print | sort)"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/preview.txt"
[ "$before_files" = "$(find "$VAULT" -type f -print | sort)" ] || fail 'preview created files'
for column in Ideas Ready Active Waiting Blocked Review Paused Done; do assert_contains "$TMP_DIR/preview.txt" "## $column"; done
for title in 'Idea task' 'Ready task' 'Current architecture task' 'Waiting current task' 'Blocked task' 'Review current task' 'Paused task' 'Done current task'; do assert_contains "$TMP_DIR/preview.txt" "$title"; done
assert_contains "$TMP_DIR/preview.txt" '  - project: Architecture project'
assert_not_contains "$TMP_DIR/preview.txt" 'Promoted task'
assert_not_contains "$TMP_DIR/preview.txt" 'Dropped task'
assert_not_contains "$TMP_DIR/preview.txt" 'Completed future task'
assert_contains "$TMP_DIR/preview.txt" '--- projects overview ---'
assert_contains "$TMP_DIR/preview.txt" '| Project | Status | Current task | Ready | Waiting | Due |'
assert_contains "$TMP_DIR/preview.txt" '| Architecture project | active | Current architecture task | 1 | 0 | 2026-08-26 |'
assert_contains "$TMP_DIR/preview.txt" '| Waiting project | active | Waiting current task | 0 | 1 | — |'
assert_contains "$TMP_DIR/preview.txt" '"format_version": 2'

if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write > "$TMP_DIR/no-confirm.txt" 2>&1; then fail 'write without confirmation succeeded'; fi
assert_not_exists "$TASKS"; assert_not_exists "$OVERVIEW"; assert_not_exists "$MANIFEST"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/write.txt"
assert_file "$TASKS"; assert_file "$OVERVIEW"; assert_file "$MANIFEST"
/usr/bin/jq -e '.format_version == 2 and (.views.tasks_kanban.target == "Obsidian/Tasks-Kanban.md") and (.views.projects_overview.target == "Obsidian/Projects-Overview.md")' "$MANIFEST" >/dev/null || fail 'manifest contract is invalid'

printf '\nmanual task edit\n' >> "$TASKS"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/manual-task.txt" 2>&1; then fail 'manual task-board edit did not block write'; fi
assert_contains "$TMP_DIR/manual-task.txt" 'proposal pending'
rm -f "$TASKS" "$OVERVIEW" "$MANIFEST"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write >/dev/null
printf '\nmanual overview edit\n' >> "$OVERVIEW"
if "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write > "$TMP_DIR/manual-overview.txt" 2>&1; then fail 'manual overview edit did not block write'; fi
assert_contains "$TMP_DIR/manual-overview.txt" 'proposal pending'

echo 'PASS: Obsidian task Kanban and project overview contract'
