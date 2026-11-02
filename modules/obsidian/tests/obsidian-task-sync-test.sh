#!/usr/bin/env bash
# Независимые контракты локальной синхронизации; без реальных сервисов.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
source "$ROOT/tests/helpers/shell-scenarios.sh"
SANDBOX="$(mktemp -d /private/tmp/obsidian-task-sync.XXXXXX)"
BASE_PATH="$PATH"
cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT
fail() { printf 'fixture error: %s\n' "$*" >&2; exit 3; }
subject() {
  local expected="$1" accepted="$2" diagnostic="$3" observed
  shift 3
  scenario_accept_exit "$accepted" "$diagnostic"
  scenario_exec observed "$@"
  scenario_assert_exit "$expected" "$observed"
}
assert_file() { subject 0 1 '' test -f "$1"; }
assert_not_exists() { subject 0 1 '' test ! -e "$1"; }
assert_not_link() { subject 0 1 '' test ! -L "$1"; }
assert_contains() { subject 0 1 '' grep -Fq -- "$2" "$1"; }
assert_not_contains() { subject 1 1 '' grep -Fq -- "$2" "$1"; }
assert_equal() { subject 0 1 '' test "$1" = "$2"; }
oracle_jq() {
  local accepted=0
  if [ "${1:-}" = -e ]; then accepted=1; fi
  subject 0 "$accepted" '' /usr/bin/jq "$@"
}
oracle_find() { subject 0 0 '' find "$@"; }
oracle_cat() { subject 0 0 '' cat "$@"; }
hash_fixture() { subject 0 0 '' bash -c 'set -euo pipefail; shasum -a 256 "$1" | cut -d" " -f1' _ "$1"; }
hash_text() { subject 0 0 '' bash -c 'set -euo pipefail; shasum -a 256 | cut -d" " -f1'; }
source_hashes() { subject 0 0 '' bash -c 'set -euo pipefail; find "$1" -path "*/ai/*.md" -type f -exec shasum -a 256 {} + | sort' _ "$PROJECTS"; }
assert_hashes() { source_hashes > "$TMP_DIR/hashes-now"; subject 0 1 '' cmp -s "$1" "$TMP_DIR/hashes-now"; }
read_json() { local __target="$1"; shift; subject 0 0 '' /usr/bin/jq "$@" > "$TMP_DIR/json-value"; printf -v "$__target" '%s' "$(< "$TMP_DIR/json-value")"; }
read_hash() { local __target="$1" __hash; subject 0 0 '' shasum -a 256 "$2" > "$TMP_DIR/hash-value"; __hash="$(< "$TMP_DIR/hash-value")"; printf -v "$__target" '%s' "${__hash%% *}"; }
scan() { subject 0 0 '' "$SYNC" scan --project-id "${1:-ai-dev-architecture}" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT"; }
scan_reject() { local code="$1" diagnostic="$2"; shift 2; subject "$code" "$code" "$diagnostic" "$SYNC" scan --project-id "${1:-ai-dev-architecture}" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT"; }
apply() { local project_id="${1:-ai-dev-architecture}" proposal_hash; read_json proposal_hash -r '.proposal_sha256' "$PROPOSAL"; subject 0 0 '' "$SYNC" apply --project-id "$project_id" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --confirm-proposal "$proposal_hash"; }
apply_reject() { local code="$1" diagnostic="$2" project_id="${3:-ai-dev-architecture}" proposal_hash; read_json proposal_hash -r '.proposal_sha256' "$PROPOSAL"; subject "$code" "$code" "$diagnostic" "$SYNC" apply --project-id "$project_id" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --confirm-proposal "$proposal_hash"; }
refresh_board() { subject 0 0 '' env SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture --replace-confirmed-board --confirm-generated-write >/dev/null; }
refresh_reject() { local code="$1" diagnostic="$2"; subject "$code" "$code" "$diagnostic" env SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture --replace-confirmed-board --confirm-generated-write; }
add_project() {
  local id="$1" name="$2" current="$3" future="$4" paused="$5" project
  project="$PROJECTS/$id"
  mkdir -p "$project/ai"
  printf '%s\n' "$current" > "$project/ai/current-task.md"
  printf '%s\n' "$future" > "$project/ai/future-tasks.md"
  printf '%s\n' "$paused" > "$project/ai/paused-tasks.md"
  printf '%s\n' "# Project Card" "" "Project ID: $id" "Name: $name" "Status: active" 'primary_archiproject: dela' > "$HUB/ai/project-cards/$id.md"
  printf '\n## %s\nName: %s\nStatus: active\nPath: %s\nCard: ai/project-cards/%s.md\n' "$id" "$name" "$project" "$id" >> "$HUB/ai/project-registry.md"
  printf '%s\n' "$id" >> "$SCOPE"
}


new_case() {
TMP_DIR="$(mktemp -d "$SANDBOX/case.XXXXXX")"
TMP_DIR="$(cd "$TMP_DIR" && pwd -P)"
mkdir -p "$TMP_DIR/home" "$TMP_DIR/tmp"
unset AI_SYNC_TEST_STAGE_SOURCE AI_SYNC_TEST_STAGE_MARKER
export HOME="$TMP_DIR/home" TMPDIR="$TMP_DIR/tmp"
STAGE="$TMP_DIR/stage"
bash "$ROOT/modules/obsidian/tests/stage-scripts.sh" "$STAGE"
GENERATOR="$STAGE/generate-obsidian-projects-kanban.sh"
SYNC="$STAGE/obsidian-task-sync.sh"
WATCHER="$STAGE/obsidian-task-sync-watch.sh"
INSTALLER="$STAGE/install-obsidian-task-sync.sh"
HUB="$TMP_DIR/hub"
PROJECTS="$HUB/projects"
ARCHITECTURE_PROJECT="$PROJECTS/ai-dev-architecture"
EXTRA_PROJECT="$PROJECTS/extra-project"
VAULT="$ARCHITECTURE_PROJECT/obsidian-vault"
SCOPE="$HUB/scope.txt"
ARCHITECTURE_BOARD="$VAULT/Obsidian/Projects/ai-dev-architecture/Kanban.md"
EXTRA_BOARD="$VAULT/Obsidian/Projects/extra-project/Kanban.md"
# Most legacy fixtures exercise architecture tasks.  Keeping this short alias
# makes their intent clear while the explicit multi-board fixtures below cover
# the new cross-project contract.
TASKS="$ARCHITECTURE_BOARD"
MANIFEST="$VAULT/Obsidian/AI-Architecture.manifest.json"
RUNTIME="$VAULT/.ai-architecture-sync"
PROPOSAL="$RUNTIME/pending-proposal.json"
REFRESH_LOCK="$RUNTIME/refresh.lock"
TEST_BIN="$TMP_DIR/test-bin"

mkdir -p "$HUB/ai/project-cards" "$VAULT/Obsidian"
mkdir -p "$TEST_BIN"
printf '%s\n' '# Archiprojects' '' '## dela' 'name: Дела' 'status: active' 'kind: group' > "$HUB/ai/archiprojects.md"
cat > "$TEST_BIN/mv" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

target="${!#}"
if [ "${AI_SYNC_TEST_MV_MODE:-}" = fail ] && [ "$target" = "$AI_SYNC_TEST_TASKS" ]; then
  if [ -n "${AI_SYNC_TEST_REACHED_SOURCE:-}" ]; then
    grep -Fq -- 'Rolled back rename' "$AI_SYNC_TEST_REACHED_SOURCE" || {
      printf 'rollback fixture did not reach the canonical replacement\n' >&2
      exit 95
    }
    printf 'canonical-replaced\n' > "$AI_SYNC_TEST_REACHED_MARKER"
  fi
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
cat > "$TEST_BIN/shasum" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

for argument in "$@"; do
  if [ -n "${AI_SYNC_TEST_FORBID_HASH_PATH:-}" ] && [ "$argument" = "$AI_SYNC_TEST_FORBID_HASH_PATH" ]; then
    printf '%s\n' "unexpected hash of $argument" >> "$AI_SYNC_TEST_HASH_LOG"
    printf 'forbidden fixture hash\n' >&2
    exit 94
  fi
done

/usr/bin/shasum "$@"
EOF
chmod +x "$TEST_BIN/shasum"
printf '%s\n' '# Project Registry' > "$HUB/ai/project-registry.md"

cat > "$TEST_BIN/launchctl" <<'NO_REAL_LAUNCHCTL'
#!/bin/sh
printf '%s\n' "$*" >> "${AI_SYNC_TEST_LAUNCH_LOG:?}"
exit 0
NO_REAL_LAUNCHCTL
chmod +x "$TEST_BIN/launchctl"
cat > "$TEST_BIN/cp" <<'STAGE_OBSERVER'
#!/usr/bin/env bash
set -euo pipefail
/bin/cp "$@"
if [ "$#" -eq 2 ] && [ -n "${AI_SYNC_TEST_STAGE_SOURCE:-}" ] && [ "$1" = "$AI_SYNC_TEST_STAGE_SOURCE" ] && [[ "$2" == *'.current-task.md.apply.'* ]]; then
  cmp -s "$1" "$2" || { printf 'staging fixture copy differs\n' >&2; exit 96; }
  printf 'current-task.md\n' > "$AI_SYNC_TEST_STAGE_MARKER"
fi
STAGE_OBSERVER
chmod +x "$TEST_BIN/cp"
export AI_SYNC_TEST_LAUNCH_LOG="$TMP_DIR/launchctl-calls"
export PATH="$TEST_BIN:$BASE_PATH"

add_project "ai-dev-architecture" "Architecture project" \
  $'Status: active\nTask ID: TASK-20260826-001\n\n## Goal\n\nCurrent task' \
  $'### FT-20260826-001 — Idea task\n\nStatus: idea\n\n### FT-20260826-002 — Ready task\n\nStatus: ready\ndue: 2026-08-28' \
  $'### 2026-08-20 — Paused task\n\nTask ID: TASK-20260820-001\n\nStatus: paused'
add_project "extra-project" "Extra project" \
  $'Status: waiting\nTask ID: TASK-20260826-010\n\n## Goal\n\nExtra current task' \
  'No future tasks.' 'No paused tasks.'

subject 0 0 '' env SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --confirm-generated-write >/dev/null
cp "$ARCHITECTURE_BOARD" "$TMP_DIR/original-architecture-board.md"
cp "$EXTRA_BOARD" "$TMP_DIR/original-extra-board.md"

# Начальная генерация готовит fixture. Проверяемый refresh начинается без lock.
rm -rf "$REFRESH_LOCK"
}
reset_board() {
  cp "$TMP_DIR/original-architecture-board.md" "$ARCHITECTURE_BOARD"
  cp "$TMP_DIR/original-extra-board.md" "$EXTRA_BOARD"
  rm -f "$PROPOSAL"
}
assert_sources_unchanged() { assert_hashes "$TMP_DIR/source-before.txt"; }
# The board anchor is the project and the task ID together, so a fixture card
# must be addressed by that pair, not by the task ID alone.
fixture_project_id() {
  case "$1" in
    'Architecture project') printf 'ai-dev-architecture';;
    'Extra project') printf 'extra-project';;
    *) fail "unknown fixture project: $1";;
  esac
}
fixture_board() {
  case "$1" in
    'Architecture project') printf '%s' "$ARCHITECTURE_BOARD";;
    'Extra project') printf '%s' "$EXTRA_BOARD";;
    *) fail "unknown fixture project: $1";;
  esac
}
move_card_to_column() {
  local task_id="$1" title="$2" project="$3" column="$4" due="${5:-}" card key board
  key="$(fixture_project_id "$project")--$task_id"
  board="$(fixture_board "$project")"
  # The generated board has no trailing newline, so the last column heading
  # would otherwise never match the insertion pattern.
  perl -0pi -e 's/(?<!\n)\z/\n/' "$board"
  CARD_ID="$key" perl -0pi -e 's{^- \[[ xX]\] [^\n]* \^\Q$ENV{CARD_ID}\E\n(?:  - [^\n]*\n)*}{}mg' "$board"
  card="$(printf '%s\n' "- [ ] $title ^$key" "  - project: $project")"
  [ -z "$due" ] || card="$(printf '%s\n' "$card" "  - 📅 $due")"
  CARD_TEXT="$card" COLUMN="$column" perl -0pi -e 's{(^## \Q$ENV{COLUMN}\E\n)}{$1 . "\n" . $ENV{CARD_TEXT}}me' "$board"
}
move_future_card_to_active() { move_card_to_column "$1" "$2" "$3" Active; }
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
assert_blocked() {
  reset_board
  eval "$1"
  source_hashes > "$TMP_DIR/source-before.txt"
  scan > "$TMP_DIR/blocked.out"
  assert_file "$PROPOSAL"
  oracle_jq -e '.state == "blocked"' "$PROPOSAL" >/dev/null
  assert_sources_unchanged
}

prepare_transition_fixture() {
  printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-500' '' '## Goal' '' 'Transition guard current task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
  printf '%s\n' '### FT-20260827-501 — Future transition guard' '' 'Status: ready' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
  printf '%s\n' '### 2026-08-20 — Paused transition guard' '' 'Task ID: TASK-20260820-500' '' 'Status: paused' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
  refresh_board
}
assert_scan_blocked() {
  local label="$1" needle="$2"
  source_hashes > "$TMP_DIR/source-before.txt"
  scan > "$TMP_DIR/transition-${label}-scan.out"
  assert_file "$PROPOSAL"
  oracle_jq -e --arg needle "$needle" '.state == "blocked" and ([.blocked_reasons[] | select(contains($needle))] | length >= 1)' "$PROPOSAL" >/dev/null
  assert_sources_unchanged
  rm -f "$PROPOSAL"
}


case_1() {
scenario_begin
new_case
DIAGNOSTIC=$''
# A selected-project scan is isolated: a change to a second board stays outside
# both the proposal and every hash/read operation. The pending proposal is also
# inseparable from that selected project at apply time.
reset_board
perl -0pi -e 's/Idea task \^ai-dev-architecture--FT-20260826-001/Renamed architecture idea ^ai-dev-architecture--FT-20260826-001/' "$ARCHITECTURE_BOARD"
move_card_to_column TASK-20260826-010 'Extra current task' 'Extra project' Blocked
source_hashes > "$TMP_DIR/multi-board-before.txt"
HASH_LOG="$TMP_DIR/scoped-hash.log"
subject 0 94 $'forbidden fixture hash\n' env AI_SYNC_TEST_FORBID_HASH_PATH="$EXTRA_BOARD" AI_SYNC_TEST_HASH_LOG="$HASH_LOG" "$SYNC" scan --project-id ai-dev-architecture --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" > "$TMP_DIR/multi-board-scan.out"
assert_file "$PROPOSAL"
oracle_jq -e '
  .project_id == "ai-dev-architecture" and
  (.board_sha256 | keys) == ["ai-dev-architecture"] and
  ([.operations[] | .project_id] | unique) == ["ai-dev-architecture"] and
  ([.operations[] | select(.operation == "rename")] | length) == 1
' "$PROPOSAL" >/dev/null
assert_not_exists "$HASH_LOG"
assert_hashes "$TMP_DIR/multi-board-before.txt"
scenario_pass
}

case_2() {
scenario_begin
new_case
DIAGNOSTIC=$'error: proposal is blocked or malformed\n'
perl -0pi -e 's/Idea task \^ai-dev-architecture--FT-20260826-001/Renamed architecture idea ^ai-dev-architecture--FT-20260826-001/' "$TASKS"
scan >/dev/null
read_json proposal_hash -r '.proposal_sha256' "$PROPOSAL"
subject 1 1 "$DIAGNOSTIC" env "$SYNC" apply --project-id extra-project --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --confirm-proposal "$proposal_hash" > "$TMP_DIR/wrong-project-apply.out" 2>&1
assert_contains "$TMP_DIR/wrong-project-apply.out" 'proposal is blocked or malformed'
subject 0 0 '' env "$SYNC" dismiss --vault "$VAULT"
scenario_pass
}

case_3() {
scenario_begin
new_case
DIAGNOSTIC=$''
# Anchors are scoped to the manifest board, not merely to any known project.
reset_board
perl -0pi -e 's/\^ai-dev-architecture--FT-20260826-001/^extra-project--FT-20260826-001/' "$ARCHITECTURE_BOARD"
scan > "$TMP_DIR/wrong-board-anchor.out"
oracle_jq -e '.state == "blocked" and ([.blocked_reasons[] | select(contains("anchor project does not match board"))] | length == 1)' "$PROPOSAL" >/dev/null
subject 0 0 '' env "$SYNC" dismiss --vault "$VAULT"
scenario_pass
}

case_4() {
scenario_begin
new_case
DIAGNOSTIC=$'error: invalid project board target: Obsidian/Projects/ai-dev-architecture/Other.md\n'
# The manifest is the only authority for board targets; an arbitrary sibling
# path must not be scanned or bound to a proposal.
reset_board
cp "$MANIFEST" "$TMP_DIR/manifest-before-unlisted-board.json"
cp "$ARCHITECTURE_BOARD" "$VAULT/Obsidian/Projects/ai-dev-architecture/Other.md"
oracle_jq --arg target 'Obsidian/Projects/ai-dev-architecture/Other.md' '(.project_boards[] | select(.project_id == "ai-dev-architecture") | .target) = $target' "$MANIFEST" > "$TMP_DIR/unlisted-board-manifest.json"
mv "$TMP_DIR/unlisted-board-manifest.json" "$MANIFEST"
scan_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/unlisted-board-scan.out" 2>&1
assert_contains "$TMP_DIR/unlisted-board-scan.out" 'invalid project board target'
cp "$TMP_DIR/manifest-before-unlisted-board.json" "$MANIFEST"
reset_board
scenario_pass
}

case_5() {
scenario_begin
new_case
DIAGNOSTIC=$''
# The optional watcher only creates a local proposal. It must not alter canonical
# task files, skip a matching board, and respect a guarded architecture refresh.
source_hashes > "$TMP_DIR/watcher-matching-before.txt"
subject 0 0 '' env "$WATCHER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --once > "$TMP_DIR/watcher-matching.out"
assert_not_exists "$PROPOSAL"
assert_hashes "$TMP_DIR/watcher-matching-before.txt"
scenario_pass
}

case_6() {
scenario_begin
new_case
DIAGNOSTIC=$''
perl -0pi -e 's/Idea task \^ai-dev-architecture--FT-20260826-001/Watcher renamed idea ^ai-dev-architecture--FT-20260826-001/' "$TASKS"
source_hashes > "$TMP_DIR/watcher-changed-before.txt"
subject 0 0 '' env "$WATCHER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --once > "$TMP_DIR/watcher-changed.out"
assert_file "$PROPOSAL"
assert_contains "$PROPOSAL" '"operation": "rename"'
assert_hashes "$TMP_DIR/watcher-changed-before.txt"
subject 0 0 '' env "$SYNC" dismiss --vault "$VAULT"
scenario_pass
}

case_7() {
scenario_begin
new_case
DIAGNOSTIC=$''
# Refresh still publishes a generated board transaction.  Watcher exclusion is
# covered in the dedicated watcher contract; this fixture only checks that a
# normal refresh and a failed generated move leave no stale runtime lock.
reset_board
printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\n\n## Goal\n\nRefresh lifecycle task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
subject 0 0 '' env SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$TMP_DIR/refresh-lifecycle.out"
assert_contains "$TASKS" 'Refresh lifecycle task'
assert_not_exists "$REFRESH_LOCK"
assert_not_link "$REFRESH_LOCK"
scenario_pass
}

case_8() {
scenario_begin
new_case
DIAGNOSTIC=$'forced generated board write failure\n'
printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\n\n## Goal\n\nRefresh lifecycle task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
refresh_board
printf '%s\n' $'Status: active\nTask ID: TASK-20260826-001\n\n## Goal\n\nFailed refresh lifecycle task' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
subject 92 92 "$DIAGNOSTIC" env AI_SYNC_TEST_MV_MODE=fail AI_SYNC_TEST_TASKS="$TASKS" PATH="$TEST_BIN:$PATH" SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture > "$TMP_DIR/refresh-lifecycle-failure.out" 2>&1
assert_contains "$TMP_DIR/refresh-lifecycle-failure.out" 'forced generated board write failure'
assert_not_exists "$REFRESH_LOCK"
assert_not_link "$REFRESH_LOCK"
scenario_pass
}

case_9() {
scenario_begin
new_case
DIAGNOSTIC=$''
# Preview is read-only. Installing or unloading a user launchd job has its own
# explicit confirmation boundary and therefore must reject bare commands.
subject 0 0 '' env "$INSTALLER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/installer-preview.out"
assert_contains "$TMP_DIR/installer-preview.out" '<key>StartInterval</key>'
assert_contains "$TMP_DIR/installer-preview.out" '<integer>10</integer>'
assert_contains "$TMP_DIR/installer-preview.out" 'obsidian-task-sync-watch.sh'
scenario_pass
}

case_10() {
scenario_begin
new_case
DIAGNOSTIC=$'error: runtime directory is unsafe\n'
mkdir -p "$RUNTIME"
rmdir "$RUNTIME"
mkdir -p "$TMP_DIR/runtime-symlink-target"
ln -s "$TMP_DIR/runtime-symlink-target" "$RUNTIME"
subject 1 1 "$DIAGNOSTIC" env "$INSTALLER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --preview > "$TMP_DIR/installer-runtime-symlink.out" 2>&1
assert_contains "$TMP_DIR/installer-runtime-symlink.out" 'runtime directory is unsafe'
rm -f "$RUNTIME"
mkdir -p "$RUNTIME"
scenario_pass
}

case_11() {
scenario_begin
new_case
DIAGNOSTIC=$'error: install requires --confirm-launchd-install\n'
subject 1 1 "$DIAGNOSTIC" env "$INSTALLER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --install > "$TMP_DIR/installer-install-without-confirm.out" 2>&1
assert_contains "$TMP_DIR/installer-install-without-confirm.out" '--confirm-launchd-install'
scenario_pass
}

case_12() {
scenario_begin
new_case
DIAGNOSTIC=$'error: uninstall requires --confirm-launchd-uninstall\n'
subject 1 1 "$DIAGNOSTIC" env "$INSTALLER" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --uninstall > "$TMP_DIR/installer-uninstall-without-confirm.out" 2>&1
assert_contains "$TMP_DIR/installer-uninstall-without-confirm.out" '--confirm-launchd-uninstall'
scenario_pass
}

case_13() {
scenario_begin
new_case
DIAGNOSTIC=$''
# A known card is identified exclusively by its generated Obsidian block ID.
reset_board
perl -0pi -e 's/Idea task \^ai-dev-architecture--FT-20260826-001/Renamed idea ^ai-dev-architecture--FT-20260826-001/' "$TASKS"
run_and_check '"operation": "rename"'
subject 0 0 '' env "$SYNC" status --vault "$VAULT" > "$TMP_DIR/status.out"
assert_contains "$TMP_DIR/status.out" '"proposal_sha256"'
subject 0 0 '' env "$SYNC" dismiss --vault "$VAULT"
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_14() {
scenario_begin
new_case
DIAGNOSTIC=$''
reset_board
perl -0pi -e 's/## Ideas\n\n- \[ \] Idea task \^ai-dev-architecture--FT-20260826-001/## Ready\n\n- [ ] Idea task ^ai-dev-architecture--FT-20260826-001/' "$TASKS"
run_and_check '"operation": "set_status"'
scenario_pass
}

case_15() {
scenario_begin
new_case
DIAGNOSTIC=$''
reset_board
perl -0pi -e 's/(Idea task \^ai-dev-architecture--FT-20260826-001\n  - project: Architecture project)/$1\n  - 📅 2026-09-01/' "$TASKS"
run_and_check '"operation": "set_due"'
scenario_pass
}

case_16() {
scenario_begin
new_case
DIAGNOSTIC=$''
reset_board
cat >> "$EXTRA_BOARD" <<'EOF'

## Ideas

- [ ] New future task
  - project: Extra project
  - 📅 2026-09-02
EOF
source_hashes > "$TMP_DIR/source-before.txt"
scan extra-project > "$TMP_DIR/extra-create-scan.out"
assert_file "$PROPOSAL"
assert_contains "$PROPOSAL" '"operation": "create_future"'
assert_sources_unchanged
scenario_pass
}

case_17() {
scenario_begin
new_case
DIAGNOSTIC=$''
assert_blocked "perl -0pi -e 's/ \^ai-dev-architecture--FT-20260826-001//' \"$TASKS\""
scenario_pass
}

case_18() {
scenario_begin
new_case
DIAGNOSTIC=$''
assert_blocked "cat >> \"$TASKS\" <<'EOF'

## Ideas

- [ ] Duplicate task ^ai-dev-architecture--FT-20260826-001
  - project: Architecture project
EOF"
scenario_pass
}

case_19() {
scenario_begin
new_case
DIAGNOSTIC=$''
assert_blocked "cat >> \"$TASKS\" <<'EOF'

## Unknown

- [ ] Unsupported column task
  - project: Architecture project
EOF"
scenario_pass
}

case_20() {
scenario_begin
new_case
DIAGNOSTIC=$''
assert_blocked "cat >> \"$TASKS\" <<'EOF'

## Ideas

- [ ] Unknown project task
  - project: Unknown project
EOF"
scenario_pass
}

case_21() {
scenario_begin
new_case
DIAGNOSTIC=$'error: proposal is blocked or malformed\n'
# A board delta cannot place multiple tasks from one project in Active. This
# fixture moves both future tasks together, so checking each operation alone is
# insufficient.
reset_board
perl -0pi -e 's/## Ideas/## Active/; s/## Ready/## Active/' "$TASKS"
source_hashes > "$TMP_DIR/multi-active-before.txt"
scan > "$TMP_DIR/multi-active-scan.out"
oracle_jq -e '.state == "blocked" and ([.blocked_reasons[] | select(contains("more than one task in Active"))] | length == 1)' "$PROPOSAL" >/dev/null
assert_contains "$TMP_DIR/multi-active-scan.out" 'created '
assert_hashes "$TMP_DIR/multi-active-before.txt"
apply_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/multi-active-apply.out" 2>&1
assert_contains "$TMP_DIR/multi-active-apply.out" 'proposal is blocked or malformed'
assert_file "$PROPOSAL"
rm -f "$PROPOSAL"
scenario_pass
}

case_22() {
scenario_begin
new_case
DIAGNOSTIC=$'error: confirmation does not match proposal\n'
# Apply is the sole reverse writer and needs the exact fresh proposal hash.
reset_board
perl -0pi -e 's/Idea task \^ai-dev-architecture--FT-20260826-001/Renamed idea \^ai-dev-architecture--FT-20260826-001/' "$TASKS"
scan > "$TMP_DIR/apply-scan.out"
source_hashes > "$TMP_DIR/wrong-confirm-before.txt"
subject 1 1 "$DIAGNOSTIC" env "$SYNC" apply --project-id ai-dev-architecture --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --confirm-proposal "$(printf '0%.0s' {1..64})" > "$TMP_DIR/wrong-confirm.out" 2>&1
assert_file "$PROPOSAL"
assert_contains "$TMP_DIR/wrong-confirm.out" 'confirmation does not match proposal'
assert_hashes "$TMP_DIR/wrong-confirm-before.txt"
scenario_pass
}

case_23() {
scenario_begin
new_case
DIAGNOSTIC=$''
perl -0pi -e 's/Idea task \^ai-dev-architecture--FT-20260826-001/Renamed idea ^ai-dev-architecture--FT-20260826-001/' "$TASKS"
scan >/dev/null
apply >/dev/null
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" 'Renamed idea'
assert_contains "$TASKS" 'Renamed idea ^ai-dev-architecture--FT-20260826-001'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_24() {
scenario_begin
new_case
DIAGNOSTIC=$'error: manifest source is not a registered task file: TASK-20260826-001\n'
# A manifest is editable input. A lexical path below ai/ may use ../ to target
# a same-named file outside the registered project task memory. Scan must
# reject it before hashing or reading that external file.
reset_board
ESCAPED_SOURCE="$ARCHITECTURE_PROJECT/current-task.md"
ESCAPED_MANIFEST_SOURCE="$ARCHITECTURE_PROJECT/ai/../current-task.md"
cp "$MANIFEST" "$TMP_DIR/manifest-before-escape.json"
printf '%s\n' 'Status: active' 'Task ID: TASK-20260826-001' '' '## Goal' '' 'Current task' > "$ESCAPED_SOURCE"
read_hash escaped_sha "$ESCAPED_SOURCE"
oracle_jq --arg source "$ESCAPED_MANIFEST_SOURCE" --arg sha "$escaped_sha" '
  (.tasks[] | select(.task_id == "TASK-20260826-001") | .source_file) = $source |
  (.tasks[] | select(.task_id == "TASK-20260826-001") | .source_sha256) = $sha
' "$MANIFEST" > "$TMP_DIR/escaped-manifest.json"
mv "$TMP_DIR/escaped-manifest.json" "$MANIFEST"
perl -0pi -e 's/Current task \^ai-dev-architecture--TASK-20260826-001/Escaped manifest rename ^ai-dev-architecture--TASK-20260826-001/' "$TASKS"
HASH_LOG="$TMP_DIR/escaped-manifest-hash.log"
AI_SYNC_TEST_FORBID_HASH_PATH="$ESCAPED_SOURCE" AI_SYNC_TEST_HASH_LOG="$HASH_LOG" PATH="$TEST_BIN:$PATH" scan_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/escaped-manifest-scan.out" 2>&1
assert_contains "$TMP_DIR/escaped-manifest-scan.out" 'manifest source is not a registered task file'
assert_not_exists "$HASH_LOG"
assert_not_exists "$PROPOSAL"
rm -f "$ESCAPED_SOURCE"
cp "$TMP_DIR/manifest-before-escape.json" "$MANIFEST"
refresh_board
scenario_pass
}

case_25() {
scenario_begin
new_case
printf -v DIAGNOSTIC 'error: proposal is stale: canonical source changed: %s/ai/future-tasks.md\n' "$ARCHITECTURE_PROJECT"
perl -0pi -e 's/Idea task/Renamed idea/' "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
refresh_board
cp "$ARCHITECTURE_BOARD" "$TMP_DIR/original-architecture-board.md"
cp "$EXTRA_BOARD" "$TMP_DIR/original-extra-board.md"
# A source edit after scan makes the proposal stale and keeps both source and proposal.
SOURCE_BACKUP="$TMP_DIR/future-before-stale.md"
cp "$ARCHITECTURE_PROJECT/ai/future-tasks.md" "$SOURCE_BACKUP"
reset_board
perl -0pi -e 's/Renamed idea \^ai-dev-architecture--FT-20260826-001/Stale source edit ^ai-dev-architecture--FT-20260826-001/' "$TASKS"
scan > "$TMP_DIR/stale-source-scan.out"
printf '\nManual canonical change\n' >> "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
source_hashes > "$TMP_DIR/stale-source-before.txt"
apply_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/stale-source-apply.out" 2>&1
assert_file "$PROPOSAL"
assert_contains "$TMP_DIR/stale-source-apply.out" 'proposal is stale: canonical source changed'
assert_hashes "$TMP_DIR/stale-source-before.txt"
cp "$SOURCE_BACKUP" "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
scenario_pass
}

case_26() {
scenario_begin
new_case
DIAGNOSTIC=$'error: proposal is stale: board changed: ai-dev-architecture\n'
perl -0pi -e 's/Idea task/Renamed idea/' "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
refresh_board
cp "$ARCHITECTURE_BOARD" "$TMP_DIR/original-architecture-board.md"
cp "$EXTRA_BOARD" "$TMP_DIR/original-extra-board.md"
# A board edit after scan makes the proposal stale and keeps the proposal.
reset_board
perl -0pi -e 's/Renamed idea \^ai-dev-architecture--FT-20260826-001/Stale board edit ^ai-dev-architecture--FT-20260826-001/' "$TASKS"
scan > "$TMP_DIR/stale-board-scan.out"
# A selected proposal binds only its own board. Changing that selected board
# after scan must make apply reject the proposal.
printf '\nManual board change after scan\n' >> "$TASKS"
source_hashes > "$TMP_DIR/stale-board-before.txt"
apply_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/stale-board-apply.out" 2>&1
assert_file "$PROPOSAL"
assert_contains "$TMP_DIR/stale-board-apply.out" 'proposal is stale: board changed'
assert_hashes "$TMP_DIR/stale-board-before.txt"
rm -f "$PROPOSAL"
subject 0 0 '' env SOURCE_DATE_EPOCH=1700000000 "$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture --replace-confirmed-board --confirm-generated-write >/dev/null
scenario_pass
}

case_27() {
scenario_begin
new_case
DIAGNOSTIC=$'calendar-confirmation-required: dated task changes must use the joint task-and-calendar preview\n'
# A dated set_due change must be refused: it needs the joint task-and-calendar
# confirmation, not the plain task-only proposal confirmation.
source_hashes > "$TMP_DIR/due-refusal-before.txt"
perl -0pi -e 's/📅 2026-08-28/📅 2026-09-01/' "$TASKS"
scan > "$TMP_DIR/due-scan.out"
apply_reject 3 "$DIAGNOSTIC" > "$TMP_DIR/due-apply.out" 2>&1
assert_contains "$TMP_DIR/due-apply.out" 'calendar-confirmation-required'
assert_hashes "$TMP_DIR/due-refusal-before.txt"
assert_file "$PROPOSAL"
rm -f "$PROPOSAL"
refresh_board
scenario_pass
}

case_28() {
scenario_begin
new_case
DIAGNOSTIC=$''
perl -0pi -e 's/Idea task/Renamed idea/' "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
refresh_board
cp "$ARCHITECTURE_BOARD" "$TMP_DIR/original-architecture-board.md"
cp "$EXTRA_BOARD" "$TMP_DIR/original-extra-board.md"
# A single proposal may rename, reschedule, and promote a future task. Promotion
# must consume the staged source record and carry the changed values into current.
perl -0pi -e 's{(## Ideas\n\n)- \[ \] Renamed idea \^ai-dev-architecture--FT-20260826-001\n  - project: Architecture project\n\n}{$1}' "$TASKS"
perl -0pi -e 's{(## Active\n)}{$1\n- [ ] Promoted renamed idea ^ai-dev-architecture--FT-20260826-001\n  - project: Architecture project\n} ' "$TASKS"
scan > "$TMP_DIR/combined-promote-scan.out"
assert_contains "$PROPOSAL" '"operation": "rename"'
assert_contains "$PROPOSAL" '"operation": "promote_to_current"'
apply > "$TMP_DIR/combined-promote-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Task ID: FT-20260826-001'
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Promoted renamed idea'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Task ID: TASK-20260826-001'
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" 'Status: promoted'
assert_contains "$TASKS" 'Promoted renamed idea ^ai-dev-architecture--FT-20260826-001'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_29() {
scenario_begin
new_case
DIAGNOSTIC=$''
# A valid unblocked card is appended to the project's canonical future tasks.
cat >> "$EXTRA_BOARD" <<'EOF'

## Ideas

- [ ] Applied new future task
  - project: Extra project
EOF
scan extra-project > "$TMP_DIR/create-scan.out"
apply extra-project > "$TMP_DIR/create-apply.out"
assert_contains "$EXTRA_PROJECT/ai/future-tasks.md" 'Applied new future task'
assert_contains "$EXTRA_BOARD" 'Applied new future task'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_30() {
scenario_begin
new_case
printf -v DIAGNOSTIC 'error: proposal is stale: canonical source changed: %s/ai/current-task.md\n' "$ARCHITECTURE_PROJECT"
stale_target=current-task.md
  prepare_promotion_fixture active 'Stale protected current task' TASK-20260827-001 FT-20260827-101 'Stale target promotion'
  scan > "$TMP_DIR/stale-promotion-${stale_target}-scan.out"
  oracle_jq -e --arg source "$ARCHITECTURE_PROJECT/ai/$stale_target" '[.affected_sources[] | select(.source_file == $source)] | length == 1' "$PROPOSAL" >/dev/null
  printf '\nManual stale edit\n' >> "$ARCHITECTURE_PROJECT/ai/$stale_target"
  source_hashes > "$TMP_DIR/stale-promotion-${stale_target}-before.txt"
  apply_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/stale-promotion-${stale_target}-apply.out" 2>&1
  assert_contains "$TMP_DIR/stale-promotion-${stale_target}-apply.out" 'proposal is stale: canonical source changed'
  assert_hashes "$TMP_DIR/stale-promotion-${stale_target}-before.txt"
  rm -f "$PROPOSAL"
scenario_pass
}

case_31() {
scenario_begin
new_case
printf -v DIAGNOSTIC 'error: proposal is stale: canonical source changed: %s/ai/paused-tasks.md\n' "$ARCHITECTURE_PROJECT"
stale_target=paused-tasks.md
  prepare_promotion_fixture active 'Stale protected current task' TASK-20260827-001 FT-20260827-101 'Stale target promotion'
  scan > "$TMP_DIR/stale-promotion-${stale_target}-scan.out"
  oracle_jq -e --arg source "$ARCHITECTURE_PROJECT/ai/$stale_target" '[.affected_sources[] | select(.source_file == $source)] | length == 1' "$PROPOSAL" >/dev/null
  printf '\nManual stale edit\n' >> "$ARCHITECTURE_PROJECT/ai/$stale_target"
  source_hashes > "$TMP_DIR/stale-promotion-${stale_target}-before.txt"
  apply_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/stale-promotion-${stale_target}-apply.out" 2>&1
  assert_contains "$TMP_DIR/stale-promotion-${stale_target}-apply.out" 'proposal is stale: canonical source changed'
  assert_hashes "$TMP_DIR/stale-promotion-${stale_target}-before.txt"
  rm -f "$PROPOSAL"
scenario_pass
}

case_32() {
scenario_begin
new_case
printf -v DIAGNOSTIC 'error: proposal is stale: canonical source changed: %s/ai/current-task.md\n' "$ARCHITECTURE_PROJECT"
# An empty current task is absent from the manifest, but promotion still
# replaces its file. It must therefore be protected independently of cards.
printf '%s\n' 'No current task.' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' '### FT-20260827-102 — Empty current promotion' '' 'Status: ready' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
move_future_card_to_active FT-20260827-102 'Empty current promotion' 'Architecture project'
scan > "$TMP_DIR/empty-current-promotion-scan.out"
oracle_jq -e --arg source "$ARCHITECTURE_PROJECT/ai/current-task.md" '[.affected_sources[] | select(.source_file == $source)] | length == 1' "$PROPOSAL" >/dev/null
printf '\nManual stale edit\n' >> "$ARCHITECTURE_PROJECT/ai/current-task.md"
source_hashes > "$TMP_DIR/empty-current-promotion-before.txt"
apply_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/empty-current-promotion-apply.out" 2>&1
assert_contains "$TMP_DIR/empty-current-promotion-apply.out" 'proposal is stale: canonical source changed'
assert_hashes "$TMP_DIR/empty-current-promotion-before.txt"
rm -f "$PROPOSAL"
scenario_pass
}

case_33() {
scenario_begin
new_case
DIAGNOSTIC=$''
# A scoped proposal promotes only its selected project's task.
prepare_promotion_fixture active 'Architecture previous task' TASK-20260827-010 FT-20260827-201 'Architecture simultaneous promotion'
printf '%s\n' 'Status: waiting' 'Task ID: TASK-20260827-011' '' '## Goal' '' 'Extra previous task' > "$EXTRA_PROJECT/ai/current-task.md"
printf '%s\n' '### FT-20260827-202 — Extra simultaneous promotion' '' 'Status: ready' > "$EXTRA_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$EXTRA_PROJECT/ai/paused-tasks.md"
refresh_board
move_future_card_to_active FT-20260827-201 'Architecture simultaneous promotion' 'Architecture project'
scan > "$TMP_DIR/multiple-promotions-scan.out"
oracle_jq -e --arg prefix "$ARCHITECTURE_PROJECT/ai/" 'all(.affected_sources[]; (.source_file | startswith($prefix)))' "$PROPOSAL" >/dev/null
apply > "$TMP_DIR/multiple-promotions-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Task ID: FT-20260827-201'
assert_contains "$EXTRA_PROJECT/ai/current-task.md" 'Task ID: TASK-20260827-011'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_34() {
scenario_begin
new_case
DIAGNOSTIC=$''
prior_status=active
prior_id=TASK-20260827-031
future_id=FT-20260827-131
  prior_title="Prior $prior_status task"
  prepare_promotion_fixture "$prior_status" "$prior_title" "$prior_id" "$future_id" "Promote after $prior_status"
  scan > "$TMP_DIR/preserve-${prior_status}-scan.out"
  apply > "$TMP_DIR/preserve-${prior_status}-apply.out"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "$prior_title"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "Task ID: $prior_id"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Status: paused'
  assert_not_exists "$PROPOSAL"
scenario_pass
}

case_35() {
scenario_begin
new_case
DIAGNOSTIC=$''
prior_status=ready
prior_id=TASK-20260827-031
future_id=FT-20260827-131
  prior_title="Prior $prior_status task"
  prepare_promotion_fixture "$prior_status" "$prior_title" "$prior_id" "$future_id" "Promote after $prior_status"
  scan > "$TMP_DIR/preserve-${prior_status}-scan.out"
  apply > "$TMP_DIR/preserve-${prior_status}-apply.out"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "$prior_title"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "Task ID: $prior_id"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Status: paused'
  assert_not_exists "$PROPOSAL"
scenario_pass
}

case_36() {
scenario_begin
new_case
DIAGNOSTIC=$''
prior_status=in_progress
prior_id=TASK-20260827-031
future_id=FT-20260827-131
  prior_title="Prior $prior_status task"
  prepare_promotion_fixture "$prior_status" "$prior_title" "$prior_id" "$future_id" "Promote after $prior_status"
  scan > "$TMP_DIR/preserve-${prior_status}-scan.out"
  apply > "$TMP_DIR/preserve-${prior_status}-apply.out"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "$prior_title"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "Task ID: $prior_id"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Status: paused'
  assert_not_exists "$PROPOSAL"
scenario_pass
}

case_37() {
scenario_begin
new_case
DIAGNOSTIC=$''
prior_status=waiting
prior_id=TASK-20260827-031
future_id=FT-20260827-131
  prior_title="Prior $prior_status task"
  prepare_promotion_fixture "$prior_status" "$prior_title" "$prior_id" "$future_id" "Promote after $prior_status"
  scan > "$TMP_DIR/preserve-${prior_status}-scan.out"
  apply > "$TMP_DIR/preserve-${prior_status}-apply.out"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "$prior_title"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "Task ID: $prior_id"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Status: paused'
  assert_not_exists "$PROPOSAL"
scenario_pass
}

case_38() {
scenario_begin
new_case
DIAGNOSTIC=$''
prior_status=blocked
prior_id=TASK-20260827-031
future_id=FT-20260827-131
  prior_title="Prior $prior_status task"
  prepare_promotion_fixture "$prior_status" "$prior_title" "$prior_id" "$future_id" "Promote after $prior_status"
  scan > "$TMP_DIR/preserve-${prior_status}-scan.out"
  apply > "$TMP_DIR/preserve-${prior_status}-apply.out"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "$prior_title"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "Task ID: $prior_id"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Status: paused'
  assert_not_exists "$PROPOSAL"
scenario_pass
}

case_39() {
scenario_begin
new_case
DIAGNOSTIC=$''
prior_status=review
prior_id=TASK-20260827-031
future_id=FT-20260827-131
  prior_title="Prior $prior_status task"
  prepare_promotion_fixture "$prior_status" "$prior_title" "$prior_id" "$future_id" "Promote after $prior_status"
  scan > "$TMP_DIR/preserve-${prior_status}-scan.out"
  apply > "$TMP_DIR/preserve-${prior_status}-apply.out"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "$prior_title"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "Task ID: $prior_id"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Status: paused'
  assert_not_exists "$PROPOSAL"
scenario_pass
}

case_40() {
scenario_begin
new_case
DIAGNOSTIC=$''
prior_status=paused
prior_id=TASK-20260827-031
future_id=FT-20260827-131
  prior_title="Prior $prior_status task"
  prepare_promotion_fixture "$prior_status" "$prior_title" "$prior_id" "$future_id" "Promote after $prior_status"
  scan > "$TMP_DIR/preserve-${prior_status}-scan.out"
  apply > "$TMP_DIR/preserve-${prior_status}-apply.out"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "$prior_title"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" "Task ID: $prior_id"
  assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Status: paused'
  assert_not_exists "$PROPOSAL"
scenario_pass
}

case_41() {
scenario_begin
new_case
DIAGNOSTIC=$''
prepare_promotion_fixture completed 'Completed current task remains recorded' TASK-20260827-099 FT-20260827-399 'Promotion after completion'
scan > "$TMP_DIR/preserve-completed-scan.out"
apply > "$TMP_DIR/preserve-completed-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Completed current task remains recorded'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Task ID: TASK-20260827-099'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Status: completed'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_42() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Waiting
  prepare_transition_fixture
  move_card_to_column FT-20260827-501 'Future transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "future-$guarded_column" 'unsupported status transition for future task'
scenario_pass
}

case_43() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Review
  prepare_transition_fixture
  move_card_to_column FT-20260827-501 'Future transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "future-$guarded_column" 'unsupported status transition for future task'
scenario_pass
}

case_44() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Done
  prepare_transition_fixture
  move_card_to_column FT-20260827-501 'Future transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "future-$guarded_column" 'unsupported status transition for future task'
scenario_pass
}

case_45() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Paused
  prepare_transition_fixture
  move_card_to_column FT-20260827-501 'Future transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "future-$guarded_column" 'unsupported status transition for future task'
scenario_pass
}

case_46() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Ideas
  prepare_transition_fixture
  move_card_to_column TASK-20260820-500 'Paused transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "paused-$guarded_column" 'unsupported status transition for paused task'
scenario_pass
}

case_47() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Ready
  prepare_transition_fixture
  move_card_to_column TASK-20260820-500 'Paused transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "paused-$guarded_column" 'unsupported status transition for paused task'
scenario_pass
}

case_48() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Active
  prepare_transition_fixture
  move_card_to_column TASK-20260820-500 'Paused transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "paused-$guarded_column" 'unsupported status transition for paused task'
scenario_pass
}

case_49() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Waiting
  prepare_transition_fixture
  move_card_to_column TASK-20260820-500 'Paused transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "paused-$guarded_column" 'unsupported status transition for paused task'
scenario_pass
}

case_50() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Blocked
  prepare_transition_fixture
  move_card_to_column TASK-20260820-500 'Paused transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "paused-$guarded_column" 'unsupported status transition for paused task'
scenario_pass
}

case_51() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Review
  prepare_transition_fixture
  move_card_to_column TASK-20260820-500 'Paused transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "paused-$guarded_column" 'unsupported status transition for paused task'
scenario_pass
}

case_52() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Done
  prepare_transition_fixture
  move_card_to_column TASK-20260820-500 'Paused transition guard' 'Architecture project' "$guarded_column"
  assert_scan_blocked "paused-$guarded_column" 'unsupported status transition for paused task'
scenario_pass
}

case_53() {
scenario_begin
new_case
DIAGNOSTIC=$''
prepare_transition_fixture
move_card_to_column TASK-20260820-500 'Paused transition guard' 'Architecture project' Paused 2026-09-09
assert_scan_blocked 'paused-due' 'due dates are not supported for paused task'
scenario_pass
}

case_54() {
scenario_begin
new_case
DIAGNOSTIC=$'forced generated board write failure\nerror: generated view refresh failed; canonical records were rolled back and the proposal was kept\n'
# A failing generator must not leave the canonical records already replaced.
# Apply is atomic: either every named source and the board change, or neither.
prepare_transition_fixture
move_card_to_column FT-20260827-501 'Rolled back rename' 'Architecture project' Ready
scan > "$TMP_DIR/rollback-scan.out"
oracle_jq -e '.state == "ready"' "$PROPOSAL" >/dev/null
source_hashes > "$TMP_DIR/rollback-before.txt"
AI_SYNC_TEST_MV_MODE=fail AI_SYNC_TEST_TASKS="$TASKS" AI_SYNC_TEST_REACHED_SOURCE="$ARCHITECTURE_PROJECT/ai/future-tasks.md" AI_SYNC_TEST_REACHED_MARKER="$TMP_DIR/rollback-reached" PATH="$TEST_BIN:$PATH" apply_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/rollback-apply.out" 2>&1
assert_contains "$TMP_DIR/rollback-apply.out" 'forced generated board write failure'
assert_contains "$TMP_DIR/rollback-apply.out" 'canonical records were rolled back'
assert_hashes "$TMP_DIR/rollback-before.txt"
oracle_find "$ARCHITECTURE_PROJECT/ai" -name '.*.backup.*' -print -quit > "$TMP_DIR/found-path"
subject 0 1 '' test ! -s "$TMP_DIR/found-path"
assert_file "$PROPOSAL"
rm -f "$PROPOSAL"
assert_contains "$TMP_DIR/rollback-reached" canonical-replaced
scenario_pass
}

case_55() {
scenario_begin
new_case
DIAGNOSTIC=$'error: scope must be inside hub\n'
# The watcher installer must reject an inconsistent hub, scope, and vault triple
# with the same checks the generator and the synchronizer already apply.
printf '%s\n' 'ai-dev-architecture' > "$TMP_DIR/outside-scope.txt"
subject 1 1 "$DIAGNOSTIC" env "$INSTALLER" --hub "$HUB" --scope "$TMP_DIR/outside-scope.txt" --vault "$VAULT" --preview > "$TMP_DIR/installer-outside-scope.out" 2>&1
assert_contains "$TMP_DIR/installer-outside-scope.out" 'scope must be inside hub'
scenario_pass
}

case_56() {
scenario_begin
new_case
DIAGNOSTIC=$'error: vault must be the local vault under ai-dev-architecture/obsidian-vault\n'
mkdir -p "$TMP_DIR/foreign-vault"
subject 1 1 "$DIAGNOSTIC" env "$INSTALLER" --hub "$HUB" --scope "$SCOPE" --vault "$TMP_DIR/foreign-vault" --preview > "$TMP_DIR/installer-foreign-vault.out" 2>&1
assert_contains "$TMP_DIR/installer-foreign-vault.out" 'vault must be the local'
scenario_pass
}

case_57() {
scenario_begin
new_case
DIAGNOSTIC=$'error: vault must be the local vault under ai-dev-architecture/obsidian-vault\n'
subject 1 1 "$DIAGNOSTIC" env "$INSTALLER" --hub "$HUB" --scope "$SCOPE" --vault "$ARCHITECTURE_PROJECT" --preview > "$TMP_DIR/installer-wrong-vault.out" 2>&1
scenario_pass
}

case_58() {
scenario_begin
new_case
DIAGNOSTIC=$''
# An untouched project ships the shipped template as its current task: an empty
# status and a placeholder ID. Promotion replaces that empty slot while keeping
# the legacy future ID readable.
printf '%s\n' 'Status: empty' 'Task ID: TASK-YYYYMMDD-NNN' '' '## Goal' '' 'Что нужно изменить.' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' '### FT-20260827-601 — Promotion into an empty slot' '' 'Status: ready' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
move_card_to_column FT-20260827-601 'Promotion into an empty slot' 'Architecture project' Active
scan > "$TMP_DIR/empty-status-promotion-scan.out"
apply > "$TMP_DIR/empty-status-promotion-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Promotion into an empty slot'
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Task ID: FT-20260827-601'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_59() {
scenario_begin
new_case
DIAGNOSTIC=$''
# Two new cards in one proposal must receive two different future task IDs.
prepare_transition_fixture
perl -0pi -e 's/(?<!\n)\z/\n/' "$TASKS"
cat >> "$TASKS" <<'EOF'

## Ideas

- [ ] First simultaneous new card
  - project: Architecture project
- [ ] Second simultaneous new card
  - project: Architecture project
EOF
scan > "$TMP_DIR/two-new-cards-scan.out"
oracle_jq -e '.state == "ready" and ([.operations[] | select(.operation == "create_future")] | length == 2) and ([.operations[] | select(.operation == "create_future") | .task_id] | unique | length == 2)' "$PROPOSAL" >/dev/null
apply > "$TMP_DIR/two-new-cards-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" 'First simultaneous new card'
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" 'Second simultaneous new card'
subject 0 1 '' bash -euo pipefail -c 'grep -Eo "^### TASK-ai-dev-architecture-[0-9]{8}-[0-9]{3} — (First|Second) simultaneous new card$" "$1" | cut -d" " -f2 | sort -u | grep -c .' _ "$ARCHITECTURE_PROJECT/ai/future-tasks.md" > "$TMP_DIR/distinct-count"
assert_equal 2 "$(< "$TMP_DIR/distinct-count")"
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_60() {
scenario_begin
new_case
DIAGNOSTIC=$''
# A current task has no Ideas state, so that move must be blocked at scan.
prepare_transition_fixture
move_card_to_column TASK-20260827-500 'Transition guard current task' 'Architecture project' Ideas
assert_scan_blocked 'current-Ideas' 'unsupported status transition for current task'
scenario_pass
}

case_61() {
scenario_begin
new_case
DIAGNOSTIC=$''
# Renaming a paused card must actually rewrite the canonical heading, including
# a title that itself contains the heading separator.
printf '%s\n' 'No current task.' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' '### 2026-08-20 — Alpha — Beta' '' 'Task ID: TASK-20260820-700' '' 'Status: paused' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
assert_contains "$TASKS" 'Alpha — Beta ^ai-dev-architecture--TASK-20260820-700'
perl -0pi -e 's/Alpha — Beta \^ai-dev-architecture--TASK-20260820-700/Renamed paused task ^ai-dev-architecture--TASK-20260820-700/' "$TASKS"
scan > "$TMP_DIR/paused-rename-scan.out"
apply > "$TMP_DIR/paused-rename-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" '### 2026-08-20 — Renamed paused task'
assert_not_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Alpha — Beta'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_62() {
scenario_begin
new_case
DIAGNOSTIC=$''
# Renaming the current task must replace its goal line, not prepend a new one,
# even when extra blank lines follow the Goal heading.
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-800' '' '## Goal' '' '' 'Original goal line' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
perl -0pi -e 's/Original goal line \^ai-dev-architecture--TASK-20260827-800/Renamed current goal ^ai-dev-architecture--TASK-20260827-800/' "$TASKS"
scan > "$TMP_DIR/current-rename-scan.out"
apply > "$TMP_DIR/current-rename-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Renamed current goal'
assert_not_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Original goal line'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_63() {
scenario_begin
new_case
printf -v DIAGNOSTIC 'error: renderable current task must have a goal line: %s/ai/current-task.md\n' "$ARCHITECTURE_PROJECT"
# A renderable current task with no goal line must be refused at generation.
# Inventing a placeholder title made every later scan propose a rename the user
# never made, and applying it destroyed the following section.
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-900' '' '## Goal' '' '## Done criteria' '' '- something' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/empty-goal-refresh.out" 2>&1
assert_contains "$TMP_DIR/empty-goal-refresh.out" 'must have a goal line'
scenario_pass
}

case_64() {
scenario_begin
new_case
DIAGNOSTIC=$''
# A well-formed board proposes nothing. A phantom rename would appear here.
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-901' '' '## Goal' '' 'Well formed goal' '' '## Done criteria' '' '- something' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
refresh_board
scan > "$TMP_DIR/no-phantom-scan.out"
assert_contains "$TMP_DIR/no-phantom-scan.out" 'board matches canonical task records'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_65() {
scenario_begin
new_case
printf -v DIAGNOSTIC 'error: proposal is stale: canonical source changed: %s/ai/future-tasks.md\n' "$ARCHITECTURE_PROJECT"
prepare_promotion_fixture active 'Staging prior task' TASK-20260827-901 FT-20260827-902 'Staging future'
scan >/dev/null
# current сортируется раньше future и должен реально попасть в staged copy.
printf '\nManual canonical change\n' >> "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
source_hashes > "$TMP_DIR/staging-before.txt"
export AI_SYNC_TEST_STAGE_SOURCE="$ARCHITECTURE_PROJECT/ai/current-task.md" AI_SYNC_TEST_STAGE_MARKER="$TMP_DIR/stage-reached"
apply_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/temp-leak-apply.out" 2>&1
oracle_find "$PROJECTS" -path '*/ai/*' -name '.*.apply.*' -print -quit > "$TMP_DIR/found-path"
subject 0 1 '' test ! -s "$TMP_DIR/found-path"
assert_contains "$TMP_DIR/stage-reached" current-task.md
assert_hashes "$TMP_DIR/staging-before.txt"
assert_file "$PROPOSAL"
scenario_pass
}

case_66() {
scenario_begin
new_case
DIAGNOSTIC=$''
# Replacing the current task must not destroy its recorded working state. The
# paused record has to keep the whole replaced body, not just its title.
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-910' '' '## Goal' '' 'Task with a recorded body' '' '## Relevant files' '' '- scripts/example.sh' '' '## Agent handoff' '' 'Open risks: the tricky migration' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' '### FT-20260827-911 — Promotion over a recorded body' '' 'Status: ready' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
move_card_to_column FT-20260827-911 'Promotion over a recorded body' 'Architecture project' Active
scan > "$TMP_DIR/preserve-body-scan.out"
apply > "$TMP_DIR/preserve-body-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Task with a recorded body'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" '- scripts/example.sh'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Open risks: the tricky migration'
subject 1 1 '' grep -Eq '^## ' "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Promotion over a recorded body'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_67() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Ready
  prepare_transition_fixture
  move_card_to_column TASK-20260827-500 'Transition guard current task' 'Architecture project' "$guarded_column"
  assert_scan_blocked "current-$guarded_column" 'unsupported status transition for current task'
scenario_pass
}

case_68() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Waiting
  prepare_transition_fixture
  move_card_to_column TASK-20260827-500 'Transition guard current task' 'Architecture project' "$guarded_column"
  assert_scan_blocked "current-$guarded_column" 'unsupported status transition for current task'
scenario_pass
}

case_69() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Paused
  prepare_transition_fixture
  move_card_to_column TASK-20260827-500 'Transition guard current task' 'Architecture project' "$guarded_column"
  assert_scan_blocked "current-$guarded_column" 'unsupported status transition for current task'
scenario_pass
}

case_70() {
scenario_begin
new_case
DIAGNOSTIC=$''
guarded_column=Done
  prepare_transition_fixture
  move_card_to_column TASK-20260827-500 'Transition guard current task' 'Architecture project' "$guarded_column"
  assert_scan_blocked "current-$guarded_column" 'unsupported status transition for current task'
scenario_pass
}

case_71() {
scenario_begin
new_case
DIAGNOSTIC=$''
# A board edit the synchronizer cannot model must block, not be reverted in
# silence by the rebuild that follows apply.
prepare_transition_fixture
perl -0pi -e 's/- \[ \] (Transition guard current task \^ai-dev-architecture--TASK-20260827-500)/- [x] $1/' "$TASKS"
assert_scan_blocked 'checkbox' 'card checkbox does not match its canonical state'
scenario_pass
}

case_72() {
scenario_begin
new_case
DIAGNOSTIC=$''
prepare_transition_fixture
perl -0pi -e 's/(Transition guard current task \^ai-dev-architecture--TASK-20260827-500\n  - project: Architecture project\n)/$1  - note: my manual annotation\n/' "$TASKS"
assert_scan_blocked 'unknown-field' 'card has an unsupported field'
scenario_pass
}

case_73() {
scenario_begin
new_case
DIAGNOSTIC=$''
# The replaced body is free-form text. No line inside it may be read back as a
# record field, a heading, or a second Task ID.
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-920' '' '## Goal' '' 'Task with a hostile body' '' '## Agent handoff' '' 'Status: blocked' 'Task ID: TASK-20260825-002' '' '### Not a record' '' '```bash' '#!/usr/bin/env bash' '```' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' '### FT-20260827-921 — Promotion over a hostile body' '' 'Status: ready' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
move_card_to_column FT-20260827-921 'Promotion over a hostile body' 'Architecture project' Active
scan > "$TMP_DIR/hostile-body-scan.out"
apply > "$TMP_DIR/hostile-body-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Task with a hostile body'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" '#!/usr/bin/env bash'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Task ID: TASK-20260825-002'
assert_contains "$TASKS" 'Task with a hostile body ^ai-dev-architecture--TASK-20260827-920'
scan > "$TMP_DIR/hostile-body-rescan.out"
assert_contains "$TMP_DIR/hostile-body-rescan.out" 'board matches canonical task records'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_74() {
scenario_begin
new_case
DIAGNOSTIC=$''
# A goal line may legitimately begin with a Markdown character.
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-930' '' '## Goal' '' '#1 приоритет' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
perl -0pi -e 's/#1 приоритет \^ai-dev-architecture--TASK-20260827-930/Обычный заголовок ^ai-dev-architecture--TASK-20260827-930/' "$TASKS"
scan > "$TMP_DIR/hash-goal-scan.out"
apply > "$TMP_DIR/hash-goal-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Обычный заголовок'
assert_not_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" '#1 приоритет'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_75() {
scenario_begin
new_case
DIAGNOSTIC=$'error: task title must not contain a tab: Tab	inside title\n'
# A tab in a title would split the record separator and make the scanner
# propose a rename and a due-date change on every run.
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-940' '' '## Goal' '' 'Tab	inside title' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/tab-title-refresh.out" 2>&1
assert_contains "$TMP_DIR/tab-title-refresh.out" 'must not contain a tab'
scenario_pass
}

case_76() {
scenario_begin
new_case
printf -v DIAGNOSTIC 'error: task source must not contain a carriage return: %s/ai/current-task.md\n' "$ARCHITECTURE_PROJECT"
printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
# A carriage return would drop the task from the board with no diagnostic.
printf 'Status: active\r\nTask ID: TASK-20260827-941\r\n\r\n## Goal\r\n\r\nCarriage return task\r\n' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
refresh_reject 1 "$DIAGNOSTIC" > "$TMP_DIR/crlf-refresh.out" 2>&1
assert_contains "$TMP_DIR/crlf-refresh.out" 'carriage return'
scenario_pass
}

case_77() {
scenario_begin
new_case
DIAGNOSTIC=$''
# Trailing whitespace must not survive into a generated record, or the tool
# proposes a rename against a heading it wrote itself.
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-950' '' '## Goal' '' 'Trailing space title ' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' '### FT-20260827-951 — Promotion over a trailing space ' '' 'Status: ready' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
assert_contains "$TASKS" 'Trailing space title ^ai-dev-architecture--TASK-20260827-950'
assert_contains "$TASKS" 'Promotion over a trailing space ^ai-dev-architecture--FT-20260827-951'
move_card_to_column FT-20260827-951 'Promotion over a trailing space' 'Architecture project' Active
scan > "$TMP_DIR/trailing-space-scan.out"
oracle_jq -e '[.operations[] | select(.operation == "rename")] | length == 0' "$PROPOSAL" >/dev/null
apply > "$TMP_DIR/trailing-space-apply.out"
scan > "$TMP_DIR/trailing-space-rescan.out"
assert_contains "$TMP_DIR/trailing-space-rescan.out" 'board matches canonical task records'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_78() {
scenario_begin
new_case
DIAGNOSTIC=$'missing_goal\nerror: invalid canonical task record: TASK-20260827-960\n'
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-960' '' '## Goal ' '' 'Shape goal' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
perl -0pi -e 's/Shape goal \^ai-dev-architecture--TASK-20260827-960/Renamed shape goal ^ai-dev-architecture--TASK-20260827-960/' "$TASKS"
scan_reject 1 "$DIAGNOSTIC" >/dev/null
scenario_pass
}

case_79() {
scenario_begin
new_case
DIAGNOSTIC=$''
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-960' '' '## Goal' 'Shape goal' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
perl -0pi -e 's/Shape goal \^ai-dev-architecture--TASK-20260827-960/Renamed shape goal ^ai-dev-architecture--TASK-20260827-960/' "$TASKS"
scan >/dev/null
apply >/dev/null
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Renamed shape goal'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_80() {
scenario_begin
new_case
DIAGNOSTIC=$''
goal_space=$'\v'
  printf 'Status: active\nTask ID: TASK-20260827-961\n\n## Goal%s\n\nWhitespace goal\n' "$goal_space" > "$ARCHITECTURE_PROJECT/ai/current-task.md"
  printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
  printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
  refresh_board
  perl -0pi -e 's/Whitespace goal \^ai-dev-architecture--TASK-20260827-961/Renamed whitespace goal ^ai-dev-architecture--TASK-20260827-961/' "$TASKS"
  scan > "$TMP_DIR/goal-whitespace-scan.out"
  apply > "$TMP_DIR/goal-whitespace-apply.out"
  assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Renamed whitespace goal'
  assert_not_exists "$PROPOSAL"
scenario_pass
}

case_81() {
scenario_begin
new_case
DIAGNOSTIC=$''
goal_space=$'\f'
  printf 'Status: active\nTask ID: TASK-20260827-961\n\n## Goal%s\n\nWhitespace goal\n' "$goal_space" > "$ARCHITECTURE_PROJECT/ai/current-task.md"
  printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
  printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
  refresh_board
  perl -0pi -e 's/Whitespace goal \^ai-dev-architecture--TASK-20260827-961/Renamed whitespace goal ^ai-dev-architecture--TASK-20260827-961/' "$TASKS"
  scan > "$TMP_DIR/goal-whitespace-scan.out"
  apply > "$TMP_DIR/goal-whitespace-apply.out"
  assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Renamed whitespace goal'
  assert_not_exists "$PROPOSAL"
scenario_pass
}

case_82() {
scenario_begin
new_case
DIAGNOSTIC=$''
# A new Obsidian card receives its permanent project-namespaced ID in the
# confirmed proposal. Its allocation must ignore unregistered project memory.
id_date="$(date -u +%Y%m%d)"
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-970' '' '## Goal' '' 'Current before stable promotion' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' 'No future tasks.' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
printf '%s\n' 'Status: waiting' 'Task ID: TASK-20260827-971' '' '## Goal' '' 'Extra current before allocation' > "$EXTRA_PROJECT/ai/current-task.md"
printf '%s\n' 'No future tasks.' > "$EXTRA_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$EXTRA_PROJECT/ai/paused-tasks.md"
mkdir -p "$PROJECTS/unregistered-shadow/ai"
printf '%s\n' "### TASK-ai-dev-architecture-${id_date}-999 — Must not affect allocation" '' 'Status: idea' > "$PROJECTS/unregistered-shadow/ai/future-tasks.md"
printf '%s\n' "Status: active" "Task ID: TASK-extra-project-${id_date}-999" '' '## Goal' '' 'Must not be read' > "$PROJECTS/unregistered-shadow/ai/current-task.md"
printf '%s\n' 'No paused tasks.' > "$PROJECTS/unregistered-shadow/ai/paused-tasks.md"
refresh_board
perl -0pi -e 's/(?<!\n)\z/\n/' "$TASKS"
perl -0pi -e 's/(?<!\n)\z/\n/' "$EXTRA_BOARD"
NEW_ARCH_CARD="$(printf '%s\n' '- [ ] Stable architecture future' '  - project: Architecture project')" \
  perl -0pi -e 's{(^## Ideas\n)}{$1 . "\n" . $ENV{NEW_ARCH_CARD} . "\n"}me' "$TASKS"
scan > "$TMP_DIR/namespaced-create-scan.out"
architecture_stable_id="TASK-ai-dev-architecture-${id_date}-001"
 oracle_jq -e --arg architecture_id "$architecture_stable_id" '
  .state == "ready" and
  ([.operations[] | select(.operation == "create_future") | .task_id]) == [$architecture_id]
' "$PROPOSAL" >/dev/null
apply > "$TMP_DIR/namespaced-create-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" "### $architecture_stable_id — Stable architecture future"
assert_contains "$TASKS" "Stable architecture future ^ai-dev-architecture--$architecture_stable_id"
assert_not_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" "${id_date}-999"
scenario_pass
}

case_83() {
scenario_begin
new_case
DIAGNOSTIC=$''
id_date="$(date -u +%Y%m%d)"
architecture_stable_id="TASK-ai-dev-architecture-${id_date}-001"
printf '%s\n' 'Status: active' 'Task ID: TASK-20260827-970' '' '## Goal' '' 'Current before stable promotion' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' "### $architecture_stable_id — Stable architecture future" '' 'Status: idea' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' 'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
refresh_board
# Promotion keeps exactly the same ID. The proposal must name every canonical
# source change: preserve the old current record, replace current, and mark the
# promoted future record. A generic set_status operation is not an exact diff.
move_card_to_column "$architecture_stable_id" 'Stable architecture future' 'Architecture project' Active
scan > "$TMP_DIR/stable-promotion-scan.out"
oracle_jq -e \
  --arg promoted_id "$architecture_stable_id" \
  --arg old_id 'TASK-20260827-970' \
  --arg future "$ARCHITECTURE_PROJECT/ai/future-tasks.md" \
  --arg current "$ARCHITECTURE_PROJECT/ai/current-task.md" \
  --arg paused "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" '
  .state == "ready" and
  ([.operations[] | select(.operation == "set_status" and .task_id == $promoted_id)] | length) == 0 and
  ([.operations[] | select(
    .operation == "promote_to_current" and
    .task_id == $promoted_id and
    .from == "idea" and .to == "active" and
    .replaced_current.task_id == $old_id and
    .replaced_current.from_status == "active" and
    .replaced_current.to_status == "paused" and
    ([.source_changes[] | select(.action == "mark_future_promoted" and .source_file == $future and .task_id == $promoted_id)] | length) == 1 and
    ([.source_changes[] | select(.action == "append_paused_record" and .source_file == $paused and .task_id == $old_id)] | length) == 1 and
    ([.source_changes[] | select(.action == "replace_current" and .source_file == $current and .from_task_id == $old_id and .to_task_id == $promoted_id)] | length) == 1
  )] | length) == 1
' "$PROPOSAL" >/dev/null
apply > "$TMP_DIR/stable-promotion-apply.out"
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" "Task ID: $architecture_stable_id"
assert_contains "$ARCHITECTURE_PROJECT/ai/current-task.md" 'Stable architecture future'
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" "### $architecture_stable_id — Stable architecture future"
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" 'Status: promoted'
assert_contains "$ARCHITECTURE_PROJECT/ai/paused-tasks.md" 'Task ID: TASK-20260827-970'
assert_contains "$TASKS" "Stable architecture future ^ai-dev-architecture--$architecture_stable_id"
subject 0 1 '' grep -Ec "Stable architecture future \^ai-dev-architecture--$architecture_stable_id$" "$TASKS" > "$TMP_DIR/stable-count"
assert_equal 1 "$(< "$TMP_DIR/stable-count")"
scan > "$TMP_DIR/stable-promotion-rescan.out"
assert_contains "$TMP_DIR/stable-promotion-rescan.out" 'board matches canonical task records'
assert_not_exists "$PROPOSAL"
scenario_pass
}

case_84() {
scenario_begin
new_case
DIAGNOSTIC=$''
# Legacy FT numbers were allocated inside one project, so two projects may hold
# the same number. Each card must still resolve to exactly one canonical record,
# and an edit must reach that project's file and no other.
printf '%s\n' $'Status: active\nTask ID: TASK-20260828-001\n\n## Goal\n\nShared number current' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' $'### FT-20260828-050 — Shared number here\n\nStatus: idea' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' $'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
printf '%s\n' $'### FT-20260828-050 — Shared number there\n\nStatus: idea' > "$EXTRA_PROJECT/ai/future-tasks.md"
refresh_board
assert_contains "$TASKS" '- [ ] Shared number here ^ai-dev-architecture--FT-20260828-050'
assert_contains "$EXTRA_BOARD" '- [ ] Shared number there ^extra-project--FT-20260828-050'
scan > "$TMP_DIR/shared-number-rescan.out"
assert_contains "$TMP_DIR/shared-number-rescan.out" 'board matches canonical task records'
assert_not_exists "$PROPOSAL"

perl -0pi -e 's/Shared number there \^extra-project--FT-20260828-050/Renamed only there ^extra-project--FT-20260828-050/' "$EXTRA_BOARD"
scan extra-project > "$TMP_DIR/shared-number-scan.out"
oracle_jq -e '
  .state == "ready" and
  (.operations == [{
    "operation": "rename",
    "task_id": "FT-20260828-050",
    "project_id": "extra-project",
    "from": "Shared number there",
    "to": "Renamed only there"
  }])
' "$PROPOSAL" >/dev/null
read_hash shared_other_before "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
apply extra-project > "$TMP_DIR/shared-number-apply.out"
assert_contains "$EXTRA_PROJECT/ai/future-tasks.md" '### FT-20260828-050 — Renamed only there'
assert_contains "$ARCHITECTURE_PROJECT/ai/future-tasks.md" '### FT-20260828-050 — Shared number here'
read_hash shared_other_after "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
assert_equal "$shared_other_before" "$shared_other_after"
scenario_pass
}

case_85() {
scenario_begin
new_case
DIAGNOSTIC=$'error: proposal is blocked or malformed\n'
printf '%s\n' $'Status: active\nTask ID: TASK-20260828-001\n\n## Goal\n\nShared number current' > "$ARCHITECTURE_PROJECT/ai/current-task.md"
printf '%s\n' $'### FT-20260828-050 — Shared number here\n\nStatus: idea' > "$ARCHITECTURE_PROJECT/ai/future-tasks.md"
printf '%s\n' $'No paused tasks.' > "$ARCHITECTURE_PROJECT/ai/paused-tasks.md"
printf '%s\n' $'### FT-20260828-050 — Shared number there\n\nStatus: idea' > "$EXTRA_PROJECT/ai/future-tasks.md"
refresh_board
perl -0pi -e 's/Shared number here \^ai-dev-architecture--FT-20260828-050/Rename without project ^ai-dev-architecture--FT-20260828-050/' "$TASKS"
scan > "$TMP_DIR/missing-project-id-scan.out"
oracle_jq 'del(.proposal_sha256) | .operations = [.operations[] | del(.project_id)]' "$PROPOSAL" > "$TMP_DIR/tampered-payload.json"
oracle_jq '{state:.state,project_id:.project_id,board_sha256:.board_sha256,manifest_sha256:.manifest_sha256,affected_sources:.affected_sources,operations:.operations,blocked_reasons:.blocked_reasons}' "$TMP_DIR/tampered-payload.json" > "$TMP_DIR/tampered-formatted"
printf '%s' "$(< "$TMP_DIR/tampered-formatted")" > "$TMP_DIR/tampered-canonical"
read_hash tampered_sha "$TMP_DIR/tampered-canonical"
oracle_jq --arg sha "$tampered_sha" '. + {proposal_sha256:$sha}' "$TMP_DIR/tampered-payload.json" > "$PROPOSAL"
source_hashes > "$TMP_DIR/missing-project-id-before.txt"
subject 1 1 "$DIAGNOSTIC" "$SYNC" apply --project-id ai-dev-architecture --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --confirm-proposal "$tampered_sha" > "$TMP_DIR/missing-project-id-apply.out" 2>&1
assert_hashes "$TMP_DIR/missing-project-id-before.txt"
assert_file "$PROPOSAL"
scenario_pass
}

scenario_declare scan-isolates-selected-project case_1
scenario_declare apply-rejects-other-project-proposal case_2
scenario_declare blocks-anchor-from-wrong-board case_3
scenario_declare rejects-unlisted-board-target case_4
scenario_declare watcher-skips-matching-board case_5
scenario_declare watcher-creates-rename-proposal-only case_6
scenario_declare refresh-releases-lock-after-success case_7
scenario_declare refresh-releases-lock-after-failed-move case_8
scenario_declare installer-preview-only case_9
scenario_declare installer-rejects-runtime-symlink case_10
scenario_declare installer-install-requires-confirmation case_11
scenario_declare installer-uninstall-requires-confirmation case_12
scenario_declare scan-rename-status-dismiss-lifecycle case_13
scenario_declare scan-detects-future-status-change case_14
scenario_declare scan-detects-future-due-addition case_15
scenario_declare scan-detects-new-extra-future-card case_16
scenario_declare blocks-known-card-without-anchor case_17
scenario_declare blocks-duplicate-card-anchor case_18
scenario_declare blocks-unsupported-column case_19
scenario_declare blocks-unknown-project-card case_20
scenario_declare blocks-multiple-active-tasks case_21
scenario_declare rejects-wrong-proposal-confirmation case_22
scenario_declare confirmed-rename-updates-canonical-and-board case_23
scenario_declare rejects-manifest-source-escape-before-hashing case_24
scenario_declare rejects-stale-canonical-source case_25
scenario_declare rejects-stale-selected-board case_26
scenario_declare dated-due-requires-calendar-confirmation case_27
scenario_declare combined-rename-and-promotion-uses-staged-record case_28
scenario_declare confirmed-create-future case_29
scenario_declare promotion-protects-stale-current-task case_30
scenario_declare promotion-protects-stale-paused-tasks case_31
scenario_declare promotion-protects-empty-current-target case_32
scenario_declare promotion-isolates-selected-project case_33
scenario_declare promotion-preserves-prior-active case_34
scenario_declare promotion-preserves-prior-ready case_35
scenario_declare promotion-preserves-prior-in-progress case_36
scenario_declare promotion-preserves-prior-waiting case_37
scenario_declare promotion-preserves-prior-blocked case_38
scenario_declare promotion-preserves-prior-review case_39
scenario_declare promotion-preserves-prior-paused case_40
scenario_declare promotion-preserves-prior-completed case_41
scenario_declare blocks-future-transition-to-waiting case_42
scenario_declare blocks-future-transition-to-review case_43
scenario_declare blocks-future-transition-to-done case_44
scenario_declare blocks-future-transition-to-paused case_45
scenario_declare blocks-paused-transition-to-ideas case_46
scenario_declare blocks-paused-transition-to-ready case_47
scenario_declare blocks-paused-transition-to-active case_48
scenario_declare blocks-paused-transition-to-waiting case_49
scenario_declare blocks-paused-transition-to-blocked case_50
scenario_declare blocks-paused-transition-to-review case_51
scenario_declare blocks-paused-transition-to-done case_52
scenario_declare blocks-paused-due-date case_53
scenario_declare apply-rolls-back-canonical-on-generator-failure case_54
scenario_declare installer-rejects-scope-outside-hub case_55
scenario_declare installer-rejects-foreign-vault case_56
scenario_declare installer-rejects-wrong-vault-subdirectory case_57
scenario_declare promotion-replaces-empty-template-current case_58
scenario_declare two-new-cards-get-distinct-ids case_59
scenario_declare blocks-current-transition-to-ideas case_60
scenario_declare renames-paused-heading-with-separator case_61
scenario_declare renames-current-goal-after-blank-lines case_62
scenario_declare generator-rejects-current-without-goal-line case_63
scenario_declare matching-board-has-no-phantom-rename case_64
scenario_declare refused-apply-leaves-no-staged-files case_65
scenario_declare promotion-preserves-full-prior-body case_66
scenario_declare blocks-current-transition-to-ready case_67
scenario_declare blocks-current-transition-to-waiting case_68
scenario_declare blocks-current-transition-to-paused case_69
scenario_declare blocks-current-transition-to-done case_70
scenario_declare blocks-checkbox-only-edit case_71
scenario_declare blocks-unknown-card-field case_72
scenario_declare promotion-preserves-hostile-body-as-text case_73
scenario_declare renames-hash-prefixed-goal case_74
scenario_declare generator-rejects-tab-title case_75
scenario_declare generator-rejects-carriage-return-source case_76
scenario_declare promotion-normalizes-trailing-title-space case_77
scenario_declare scan-rejects-space-after-goal-heading case_78
scenario_declare renames-goal-without-blank-line case_79
scenario_declare renames-goal-heading-vertical-tab case_80
scenario_declare renames-goal-heading-form-feed case_81
scenario_declare new-id-ignores-unregistered-memory case_82
scenario_declare promotion-keeps-id-and-exact-source-diff case_83
scenario_declare shared-legacy-number-resolves-project-locally case_84
scenario_declare apply-rejects-operation-without-project-id case_85
scenario_main "$@"
