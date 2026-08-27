#!/usr/bin/env bash
# Contract tests for the non-writing Obsidian proposal scanner.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GENERATOR="$ROOT/scripts/generate-obsidian-projects-kanban.sh"
SYNC="$ROOT/scripts/obsidian-task-sync.sh"
WATCHER="$ROOT/scripts/obsidian-task-sync-watch.sh"
INSTALLER="$ROOT/scripts/install-obsidian-task-sync.sh"
TMP_DIR="$(mktemp -d /private/tmp/obsidian-task-sync.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
assert_file() { [ -f "$1" ] || fail "missing file: $1"; }
assert_not_exists() { [ ! -e "$1" ] || fail "unexpected path: $1"; }
assert_not_link() { [ ! -L "$1" ] || fail "unexpected symlink: $1"; }
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
REFRESH_LOCK="$RUNTIME/refresh.lock"
TEST_BIN="$TMP_DIR/test-bin"

mkdir -p "$HUB/ai/project-cards" "$VAULT/Obsidian"
mkdir -p "$TEST_BIN"
cat > "$TEST_BIN/mv" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

target="${!#}"
if [ "${AI_SYNC_TEST_MV_MODE:-}" = fail ] && [ "$target" = "$AI_SYNC_TEST_TASKS" ]; then
  printf '%s\n' 'forced generated board write failure' >&2
  exit 92
fi

/bin/mv "$@"

if [ "${AI_SYNC_TEST_MV_MODE:-}" = watch ] && [ "$target" = "$AI_SYNC_TEST_TASKS" ]; then
  [ -d "$AI_SYNC_TEST_REFRESH_LOCK" ] && [ ! -L "$AI_SYNC_TEST_REFRESH_LOCK" ] || {
    printf '%s\n' 'refresh lock was absent during generated board write' >&2
    exit 91
  }
  "$AI_SYNC_TEST_WATCHER" --hub "$AI_SYNC_TEST_HUB" --scope "$AI_SYNC_TEST_SCOPE" --vault "$AI_SYNC_TEST_VAULT" --once
  [ ! -e "$AI_SYNC_TEST_PROPOSAL" ] && [ ! -L "$AI_SYNC_TEST_PROPOSAL" ] || {
    printf '%s\n' 'watcher scanned a generated board write' >&2
    exit 93
  }
fi
EOF
chmod +x "$TEST_BIN/mv"
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
refresh_board() { SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture --replace-confirmed-board --confirm-generated-write >/dev/null; }
move_future_card_to_active() {
  local task_id="$1" title="$2" project="$3"
  CARD_ID="$task_id" perl -0pi -e 's{^- \[ \] [^\n]* \^\Q$ENV{CARD_ID}\E\n(?:  - [^\n]*\n)*}{}mg' "$TASKS"
  CARD_TEXT="$(printf '%s\n' "- [ ] $title ^$task_id" "  - project: $project")" perl -0pi -e 's{(## Active\n)}{$1 . "\n" . $ENV{CARD_TEXT}}e' "$TASKS"
}
prepare_promotion_fixture() {
  local status="$1" title="$2" task_id="$3" future_id="$4" future_title="$5"
  printf '%s\n' "Status: $status" "Task ID: $task_id" '' '## Goal' '' "$title" > "$ARCHITECTURE_PROJECT/ai/current-task.md"
  printf '%s\n' "### $future_id — $future_title" '' 'Status: ready' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
  printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
  refresh_board
  move_future_card_to_active "$future_id" "$future_title" 'Architecture project'
}
run_and_check() {
  source_hashes > "$TMP_DIR/source-before.txt"
  scan > "$TMP_DIR/scan.out"
  assert_file "$PROPOSAL"
  assert_contains "$PROPOSAL" "$1"
  assert_sources_unchanged
}

# The optional watcher only creates a local proposal. It must not alter canonical
# task files, skip a matching board, and respect a guarded architecture refresh.
source_hashes > "$TMP_DIR/watcher-matching-before.txt"
"$WATCHER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --once > "$TMP_DIR/watcher-matching.out"
assert_not_exists "$PROPOSAL"
assert_equal "$(cat "$TMP_DIR/watcher-matching-before.txt")" "$(source_hashes)" 'matching watcher scan changed canonical sources'

perl -0pi -e 's/Idea task \^FT-20260826-001/Watcher renamed idea ^FT-20260826-001/' "$TASKS"
source_hashes > "$TMP_DIR/watcher-changed-before.txt"
"$WATCHER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --once > "$TMP_DIR/watcher-changed.out"
assert_file "$PROPOSAL"
assert_contains "$PROPOSAL" '"operation": "rename"'
assert_equal "$(cat "$TMP_DIR/watcher-changed-before.txt")" "$(source_hashes)" 'watcher changed canonical sources'
"$SYNC" dismiss --vault "$VAULT"

# A guarded refresh owns a real lock while it replaces the task board. The mv
# wrapper runs the watcher after the generated board move, which verifies both
# that the watcher is suppressed during the write and that the lock is cleaned
# afterwards. A forced move failure covers cleanup through the EXIT trap.
reset_board
printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\n\n## Goal\n\nRefresh lifecycle task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
AI_SYNC_TEST_MV_MODE=watch AI_SYNC_TEST_TASKS="$TASKS" AI_SYNC_TEST_REFRESH_LOCK="$REFRESH_LOCK" AI_SYNC_TEST_WATCHER="$WATCHER" AI_SYNC_TEST_HUB="$HUB" AI_SYNC_TEST_SCOPE="$SCOPE" AI_SYNC_TEST_VAULT="$VAULT" AI_SYNC_TEST_PROPOSAL="$PROPOSAL" PATH="$TEST_BIN:$PATH" SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$TMP_DIR/refresh-lifecycle.out"
assert_contains "$TASKS" 'Refresh lifecycle task'
assert_not_exists "$REFRESH_LOCK"
assert_not_link "$REFRESH_LOCK"

printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\n\n## Goal\n\nFailed refresh lifecycle task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
if AI_SYNC_TEST_MV_MODE=fail AI_SYNC_TEST_TASKS="$TASKS" PATH="$TEST_BIN:$PATH" SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$TMP_DIR/refresh-lifecycle-failure.out" 2>&1; then
  fail 'guarded refresh accepted a forced generated board write failure'
fi
assert_contains "$TMP_DIR/refresh-lifecycle-failure.out" 'forced generated board write failure'
assert_not_exists "$REFRESH_LOCK"
assert_not_link "$REFRESH_LOCK"
printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\n\n## Goal\n\nCurrent task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture >/dev/null
reset_board

# Preview is read-only. Installing or unloading a user launchd job has its own
# explicit confirmation boundary and therefore must reject bare commands.
"$INSTALLER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/installer-preview.out"
assert_contains "$TMP_DIR/installer-preview.out" '<key>StartInterval</key>'
assert_contains "$TMP_DIR/installer-preview.out" '<integer>10</integer>'
assert_contains "$TMP_DIR/installer-preview.out" 'obsidian-task-sync-watch.sh'
rmdir "$RUNTIME"
mkdir -p "$TMP_DIR/runtime-symlink-target"
ln -s "$TMP_DIR/runtime-symlink-target" "$RUNTIME"
if "$INSTALLER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/installer-runtime-symlink.out" 2>&1; then
  fail 'installer accepted a symlinked runtime directory'
fi
assert_contains "$TMP_DIR/installer-runtime-symlink.out" 'runtime directory is unsafe'
rm -f "$RUNTIME"
mkdir -p "$RUNTIME"
if "$INSTALLER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --install > "$TMP_DIR/installer-install-without-confirm.out" 2>&1; then
  fail 'installer accepted install without explicit confirmation'
fi
assert_contains "$TMP_DIR/installer-install-without-confirm.out" '--confirm-launchd-install'
if "$INSTALLER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --uninstall > "$TMP_DIR/installer-uninstall-without-confirm.out" 2>&1; then
  fail 'installer accepted uninstall without explicit confirmation'
fi
assert_contains "$TMP_DIR/installer-uninstall-without-confirm.out" '--confirm-launchd-uninstall'

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

# A board delta cannot place multiple tasks from one project in Active. This
# fixture moves both future tasks together, so checking each operation alone is
# insufficient.
reset_board
perl -0pi -e 's/## Ideas/## Active/; s/## Ready/## Active/' "$TASKS"
source_hashes > "$TMP_DIR/multi-active-before.txt"
scan > "$TMP_DIR/multi-active-scan.out"
/usr/bin/jq -e '.state == "blocked" and ([.blocked_reasons[] | select(contains("more than one task in Active"))] | length == 1)' "$PROPOSAL" >/dev/null || fail 'multiple Active tasks for one project were not blocked'
assert_contains "$TMP_DIR/multi-active-scan.out" 'created '
assert_equal "$(cat "$TMP_DIR/multi-active-before.txt")" "$(source_hashes)" 'multi-Active scan changed canonical files'
if apply > "$TMP_DIR/multi-active-apply.out" 2>&1; then fail 'apply accepted blocked multiple-Active proposal'; fi
assert_contains "$TMP_DIR/multi-active-apply.out" 'proposal is blocked or malformed'
assert_file "$PROPOSAL"
rm -f "$PROPOSAL"

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

# Promotion writes current-task.md and paused-tasks.md as well as its future
# source. Both replacement targets must be captured in the proposal and make
# apply fail before any write if either changed after the scan.
for stale_target in current-task.md paused-tasks.md; do
  prepare_promotion_fixture active 'Stale protected current task' TASK-20260827-001 FT-20260827-101 'Stale target promotion'
  scan > "$TMP_DIR/stale-promotion-${stale_target}-scan.out"
  /usr/bin/jq -e --arg source "$ARCHITECTURE_PROJECT/ai/$stale_target" '[.affected_sources[] | select(.source_file == $source)] | length == 1' "$PROPOSAL" >/dev/null || fail "proposal did not hash promotion target: $stale_target"
  printf '\nManual stale edit\n' >> "$ARCHITECTURE_PROJECT/ai/$stale_target"
  source_hashes > "$TMP_DIR/stale-promotion-${stale_target}-before.txt"
  if apply > "$TMP_DIR/stale-promotion-${stale_target}-apply.out" 2>&1; then fail "stale promotion applied after $stale_target changed"; fi
  assert_contains "$TMP_DIR/stale-promotion-${stale_target}-apply.out" 'proposal is stale: canonical source changed'
  assert_equal "$(cat "$TMP_DIR/stale-promotion-${stale_target}-before.txt")" "$(source_hashes)" "stale promotion rewrote sources after $stale_target changed"
  rm -f "$PROPOSAL"
done

# An empty current task is absent from the manifest, but promotion still
# replaces its file. It must therefore be protected independently of cards.
printf '%s\n' 'No current task.' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' '### FT-20260827-102 — Empty current promotion' '' 'Status: ready' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
move_future_card_to_active FT-20260827-102 'Empty current promotion' 'Architecture project'
scan > "$TMP_DIR/empty-current-promotion-scan.out"
/usr/bin/jq -e --arg source "$ARCHITECTURE_PROJECT/ai/current-task.md" '[.affected_sources[] | select(.source_file == $source)] | length == 1' "$PROPOSAL" >/dev/null || fail 'proposal did not hash an empty current-task replacement target'
printf '\nManual stale edit\n' >> "$ARCHITECTURE_PROJECT/ai/current-task.md"
source_hashes > "$TMP_DIR/empty-current-promotion-before.txt"
if apply > "$TMP_DIR/empty-current-promotion-apply.out" 2>&1; then fail 'promotion applied after an empty current-task changed'; fi
assert_contains "$TMP_DIR/empty-current-promotion-apply.out" 'proposal is stale: canonical source changed'
assert_equal "$(cat "$TMP_DIR/empty-current-promotion-before.txt")" "$(source_hashes)" 'stale empty current promotion rewrote sources'
rm -f "$PROPOSAL"

# Two projects can promote in one proposal. Each replacement current task must
# receive its own valid TASK ID, before the generator is called.
prepare_promotion_fixture active 'Architecture previous task' TASK-20260827-010 FT-20260827-201 'Architecture simultaneous promotion'
printf '%s\n' 'Status: waiting' 'Task ID: TASK-20260827-011' '' '## Goal' '' 'Extra previous task' > "$EXTRA_PROJECT/ai/current-task.md"
printf '%s\n' '### FT-20260827-202 — Extra simultaneous promotion' '' 'Status: ready' > "$EXTRA_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$EXTRA_PROJECT/ai/paused-tasks.md"
refresh_board
move_future_card_to_active FT-20260827-201 'Architecture simultaneous promotion' 'Architecture project'
move_future_card_to_active FT-20260827-202 'Extra simultaneous promotion' 'Extra project'
scan > "$TMP_DIR/multiple-promotions-scan.out"
apply > "$TMP_DIR/multiple-promotions-apply.out"
architecture_promoted_id="$(sed -n 's/^Task ID: \(TASK-[0-9]\{8\}-[0-9]\{3\}\)$/\1/p' "$ARCHITECTURE_PROJECT/ai/current-task.md")"
extra_promoted_id="$(sed -n 's/^Task ID: \(TASK-[0-9]\{8\}-[0-9]\{3\}\)$/\1/p' "$EXTRA_PROJECT/ai/current-task.md")"
[[ "$architecture_promoted_id" =~ ^TASK-[0-9]{8}-[0-9]{3}$ ]] || fail 'architecture simultaneous promotion has an invalid TASK ID'
[[ "$extra_promoted_id" =~ ^TASK-[0-9]{8}-[0-9]{3}$ ]] || fail 'extra simultaneous promotion has an invalid TASK ID'
[ "$architecture_promoted_id" != "$extra_promoted_id" ] || fail 'simultaneous promotions reused one TASK ID'
assert_not_exists "$PROPOSAL"

# Replacing a current task must preserve every unfinished state as a paused
# record. Completed data must remain recorded rather than being overwritten.
preserve_counter=30
for prior_status in active ready in_progress waiting blocked review paused; do
  preserve_counter=$((preserve_counter + 1))
  printf -v prior_id 'TASK-20260827-%03d' "$preserve_counter"
  printf -v future_id 'FT-20260827-%03d' "$((preserve_counter + 100))"
  prior_title="Prior $prior_status task"
  prepare_promotion_fixture "$prior_status" "$prior_title" "$prior_id" "$future_id" "Promote after $prior_status"
  scan > "$TMP_DIR/preserve-${prior_status}-scan.out"
  apply > "$TMP_DIR/preserve-${prior_status}-apply.out"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "$prior_title"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "Task ID: $prior_id"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Status: paused'
  assert_not_exists "$PROPOSAL"
done

prepare_promotion_fixture completed 'Completed current task remains recorded' TASK-20260827-099 FT-20260827-399 'Promotion after completion'
scan > "$TMP_DIR/preserve-completed-scan.out"
apply > "$TMP_DIR/preserve-completed-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Completed current task remains recorded'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Task ID: TASK-20260827-099'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Status: completed'
assert_not_exists "$PROPOSAL"

printf 'PASS: Obsidian confirmed task sync contract\n'
