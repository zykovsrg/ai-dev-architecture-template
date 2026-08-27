#!/usr/bin/env bash
# Contract tests for the non-writing Obsidian proposal scanner.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GENERATOR="$ROOT/scripts/generate-obsidian-projects-kanban.sh"
SYNC="$ROOT/scripts/obsidian-task-sync.sh"
TMP_DIR="$(mktemp -d /private/tmp/obsidian-task-sync.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
assert_file() { [ -f "$1" ] || fail "missing file: $1"; }
assert_not_exists() { [ ! -e "$1" ] || fail "unexpected path: $1"; }
assert_contains() { grep -Fq -- "$2" "$1" || fail "expected '$2' in $1"; }
assert_equal() { [ "$1" = "$2" ] || fail "$3"; }

HUB="$TMP_DIR/hub"
PROJECTS="$HUB/projects"
ARCHITECTURE_PROJECT="$PROJECTS/ai-dev-architecture"
EXTRA_PROJECT="$PROJECTS/extra-project"
VAULT="$ARCHITECTURE_PROJECT/obsidian-vault"
SCOPE="$HUB/scope.txt"
TASKS="$VAULT/Obsidian/Tasks-Kanban.md"
MANIFEST="$VAULT/Obsidian/AI-Architecture.manifest.json"
RUNTIME="$VAULT/.ai-architecture-sync"
PROPOSAL="$RUNTIME/pending-proposal.json"

mkdir -p "$HUB/ai/project-cards" "$VAULT/Obsidian"
printf '%s\n' '# Project Registry' > "$HUB/ai/project-registry.md"

add_project() {
  local id="$1" name="$2" current="$3" future="$4" paused="$5" project
  project="$PROJECTS/$id"
  mkdir -p "$project/ai"
  printf '%s\n' "$current" > "$project/ai/current-task.md"
  printf '%s\n' "$future" > "$project/ai/future-tasks.md"
  printf '%s\n' "$paused" > "$project/ai/paused-tasks.md"
  printf '%s\n' "# Project Card" "" "Project ID: $id" "Name: $name" "Status: active" > "$HUB/ai/project-cards/$id.md"
  printf '\n## %s\nName: %s\nStatus: active\nPath: %s\nCard: ai/project-cards/%s.md\n' "$id" "$name" "$project" "$id" >> "$HUB/ai/project-registry.md"
  printf '%s\n' "$id" >> "$SCOPE"
}

add_project "ai-dev-architecture" "Architecture project" \
  $'Status: active\nTask ID: TASK-20260826-001\n\n## Goal\n\nCurrent task' \
  $'### FT-20260826-001 — Idea task\n\nStatus: idea\n\n### FT-20260826-002 — Ready task\n\nStatus: ready\ndue: 2026-08-28' \
  $'### 2026-08-20 — Paused task\n\nTask ID: TASK-20260820-001\n\nStatus: paused'
add_project "extra-project" "Extra project" \
  $'Status: waiting\nTask ID: TASK-20260826-010\n\n## Goal\n\nExtra current task' \
  'No future tasks.' 'No paused tasks.'

SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write >/dev/null
cp "$TASKS" "$TMP_DIR/original-board.md"

reset_board() {
  cp "$TMP_DIR/original-board.md" "$TASKS"
  rm -f "$PROPOSAL"
}
source_hashes() { find "$PROJECTS" -path '*/ai/*.md' -type f -exec shasum -a 256 {} + | sort; }
scan() { "$SYNC" scan --hub "$HUB" --scope "$SCOPE" --vault "$VAULT"; }
apply() {
  local proposal_hash
  proposal_hash="$(/usr/bin/jq -r '.proposal_sha256' "$PROPOSAL")"
  "$SYNC" apply --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --confirm-proposal "$proposal_hash"
}
assert_sources_unchanged() { assert_equal "$(cat "$TMP_DIR/source-before.txt")" "$(source_hashes)" 'scanner changed canonical source files'; }
run_and_check() {
  source_hashes > "$TMP_DIR/source-before.txt"
  scan > "$TMP_DIR/scan.out"
  assert_file "$PROPOSAL"
  assert_contains "$PROPOSAL" "$1"
  assert_sources_unchanged
}

# A known card is identified exclusively by its generated Obsidian block ID.
reset_board
perl -0pi -e 's/Idea task \^FT-20260826-001/Renamed idea ^FT-20260826-001/' "$TASKS"
run_and_check '"operation": "rename"'
"$SYNC" status --vault "$VAULT" > "$TMP_DIR/status.out"
assert_contains "$TMP_DIR/status.out" '"proposal_sha256"'
"$SYNC" dismiss --vault "$VAULT"
assert_not_exists "$PROPOSAL"

reset_board
perl -0pi -e 's/## Ideas\n\n- \[ \] Idea task \^FT-20260826-001/## Ready\n\n- [ ] Idea task ^FT-20260826-001/' "$TASKS"
run_and_check '"operation": "set_status"'

reset_board
perl -0pi -e 's/(Idea task \^FT-20260826-001\n  - project: Architecture project)/$1\n  - 📅 2026-09-01/' "$TASKS"
run_and_check '"operation": "set_due"'

reset_board
cat >> "$TASKS" <<'EOF'

## Ideas

- [ ] New future task
  - project: Extra project
  - 📅 2026-09-02
EOF
run_and_check '"operation": "create_future"'

assert_blocked() {
  reset_board
  eval "$1"
  source_hashes > "$TMP_DIR/source-before.txt"
  scan > "$TMP_DIR/blocked.out"
  assert_file "$PROPOSAL"
  /usr/bin/jq -e '.state == "blocked"' "$PROPOSAL" >/dev/null || fail 'invalid board did not create blocked proposal'
  assert_sources_unchanged
}

assert_blocked "perl -0pi -e 's/ \^FT-20260826-001//' \"$TASKS\""
assert_blocked "cat >> \"$TASKS\" <<'EOF'

## Ideas

- [ ] Duplicate task ^FT-20260826-001
  - project: Architecture project
EOF"
assert_blocked "cat >> \"$TASKS\" <<'EOF'

## Unknown

- [ ] Unsupported column task
  - project: Architecture project
EOF"
assert_blocked "cat >> \"$TASKS\" <<'EOF'

## Ideas

- [ ] Unknown project task
  - project: Unknown project
EOF"

# Apply is the sole reverse writer and needs the exact fresh proposal hash.
reset_board
perl -0pi -e 's/Idea task \^FT-20260826-001/Renamed idea \^FT-20260826-001/' "$TASKS"
scan > "$TMP_DIR/apply-scan.out"
source_hashes > "$TMP_DIR/wrong-confirm-before.txt"
if "$SYNC" apply --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --confirm-proposal "$(printf '0%.0s' {1..64})" > "$TMP_DIR/wrong-confirm.out" 2>&1; then fail 'apply accepted a different proposal hash'; fi
assert_file "$PROPOSAL"
assert_contains "$TMP_DIR/wrong-confirm.out" 'confirmation does not match proposal'
assert_equal "$(cat "$TMP_DIR/wrong-confirm-before.txt")" "$(source_hashes)" 'wrong confirmation changed canonical files'
apply > "$TMP_DIR/apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" 'Renamed idea'
assert_contains "$TASKS" 'Renamed idea ^FT-20260826-001'
assert_not_exists "$PROPOSAL"

# A source edit after scan makes the proposal stale and keeps both source and proposal.
SOURCE_BACKUP="$TMP_DIR/future-before-stale.md"
cp "$ARCHITECTURE_PROJECT/ai/future-tasks.md" "$SOURCE_BACKUP"
reset_board
perl -0pi -e 's/Renamed idea \^FT-20260826-001/Stale source edit ^FT-20260826-001/' "$TASKS"
scan > "$TMP_DIR/stale-source-scan.out"
printf '\nManual canonical change\n' >> "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
source_hashes > "$TMP_DIR/stale-source-before.txt"
if apply > "$TMP_DIR/stale-source-apply.out" 2>&1; then fail 'stale source proposal applied'; fi
assert_file "$PROPOSAL"
assert_contains "$TMP_DIR/stale-source-apply.out" 'proposal is stale: canonical source changed'
assert_equal "$(cat "$TMP_DIR/stale-source-before.txt")" "$(source_hashes)" 'stale source apply changed canonical files'
cp "$SOURCE_BACKUP" "$ARCHITECTURE_PROJECT/ai/future-tasks.md"

# A board edit after scan makes the proposal stale and keeps the proposal.
reset_board
perl -0pi -e 's/Renamed idea \^FT-20260826-001/Stale board edit ^FT-20260826-001/' "$TASKS"
scan > "$TMP_DIR/stale-board-scan.out"
printf '\nManual board change after scan\n' >> "$TASKS"
source_hashes > "$TMP_DIR/stale-board-before.txt"
if apply > "$TMP_DIR/stale-board-apply.out" 2>&1; then fail 'stale board proposal applied'; fi
assert_file "$PROPOSAL"
assert_contains "$TMP_DIR/stale-board-apply.out" 'proposal is stale: board changed'
assert_equal "$(cat "$TMP_DIR/stale-board-before.txt")" "$(source_hashes)" 'stale board apply changed canonical files'
rm -f "$PROPOSAL"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture --replace-confirmed-board --confirm-generated-write >/dev/null

# Applying a due-date change rewrites only the named future record and view.
perl -0pi -e 's/📅 2026-08-28/📅 2026-09-01/' "$TASKS"
scan > "$TMP_DIR/due-scan.out"
apply > "$TMP_DIR/due-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" 'due: 2026-09-01'
assert_contains "$TASKS" '📅 2026-09-01'
assert_not_exists "$PROPOSAL"

# A single proposal may rename, reschedule, and promote a future task. Promotion
# must consume the staged source record and carry the changed values into current.
perl -0pi -e 's{(## Ideas\n\n)- \[ \] Renamed idea \^FT-20260826-001\n  - project: Architecture project\n\n}{$1}' "$TASKS"
perl -0pi -e 's{(## Active\n)}{$1\n- [ ] Promoted renamed idea ^FT-20260826-001\n  - project: Architecture project\n  - 📅 2026-09-03\n} ' "$TASKS"
scan > "$TMP_DIR/combined-promote-scan.out"
assert_contains "$PROPOSAL" '"operation": "rename"'
assert_contains "$PROPOSAL" '"operation": "set_due"'
assert_contains "$PROPOSAL" '"operation": "set_status"'
apply > "$TMP_DIR/combined-promote-apply.out"
grep -Eq '^Task ID: TASK-[0-9]{8}-[0-9]{3}$' "$ARCHITECTURE_PROJECT/ai/current-task.md" || fail 'promoted current task did not receive a TASK ID'
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Promoted renamed idea'
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'due: 2026-09-03'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Task ID: TASK-20260826-001'
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" 'Status: promoted'
assert_contains "$TASKS" 'Promoted renamed idea ^TASK-'
assert_not_exists "$PROPOSAL"

# A valid unblocked card is appended to the project's canonical future tasks.
cat >> "$TASKS" <<'EOF'

## Ideas

- [ ] Applied new future task
  - project: Extra project
  - 📅 2026-09-02
EOF
scan > "$TMP_DIR/create-scan.out"
apply > "$TMP_DIR/create-apply.out"
assert_contains "$EXTRA_PROJECT/ai/future-tasks.md" 'Applied new future task'
assert_contains "$TASKS" 'Applied new future task'
assert_not_exists "$PROPOSAL"

printf 'PASS: Obsidian confirmed task sync contract\n'
