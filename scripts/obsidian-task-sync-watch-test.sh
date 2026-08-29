#!/usr/bin/env bash
# Focused concurrency contract for the proposal watcher.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WATCHER="$ROOT/scripts/obsidian-task-sync-watch.sh"
TMP_DIR="$(mktemp -d /private/tmp/obsidian-task-sync-watch.XXXXXX)"
WATCH_PID=''
cleanup() {
  [ -z "$WATCH_PID" ] || kill "$WATCH_PID" 2>/dev/null || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

HUB="$TMP_DIR/hub"
SCOPE="$HUB/scope.txt"
VAULT="$HUB/projects/ai-dev-architecture/obsidian-vault"
RUNTIME="$VAULT/.ai-architecture-sync"
REFRESH_LOCK="$RUNTIME/refresh.lock"
FIXTURE_BIN="$TMP_DIR/watcher-fixture"
STARTED="$TMP_DIR/scan-started"
CONTINUE="$TMP_DIR/scan-continue"

mkdir -p "$RUNTIME" "$FIXTURE_BIN"
printf '%s\n' 'ai-dev-architecture' > "$SCOPE"
cp "$WATCHER" "$FIXTURE_BIN/obsidian-task-sync-watch.sh"
cat > "$FIXTURE_BIN/obsidian-task-sync.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${AI_SYNC_TEST_STARTED:?}"
: "${AI_SYNC_TEST_CONTINUE:?}"
: "${AI_SYNC_TEST_RUNTIME:?}"
[ "${1:-}" = scan ] && [ "${2:-}" = --project-id ] && [ "${3:-}" = ai-dev-architecture ] || {
  printf '%s\n' 'watcher did not select its scoped project' >&2
  exit 95
}
touch "$AI_SYNC_TEST_STARTED"
while [ ! -e "$AI_SYNC_TEST_CONTINUE" ]; do sleep 0.01; done
printf '%s\n' '{"state":"ready","stale":true}' > "$AI_SYNC_TEST_RUNTIME/pending-proposal.json"
EOF
chmod +x "$FIXTURE_BIN/obsidian-task-sync-watch.sh" "$FIXTURE_BIN/obsidian-task-sync.sh"

AI_SYNC_TEST_STARTED="$STARTED" \
AI_SYNC_TEST_CONTINUE="$CONTINUE" \
AI_SYNC_TEST_RUNTIME="$RUNTIME" \
  "$FIXTURE_BIN/obsidian-task-sync-watch.sh" \
    --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --once &
WATCH_PID=$!

for _ in {1..500}; do
  [ -e "$STARTED" ] && break
  sleep 0.01
done
[ -e "$STARTED" ] || fail 'watcher scan did not start'

# A refresh that begins after the watcher's first observation must still be
# excluded until scan has committed (or declined) its proposal.
if mkdir "$REFRESH_LOCK" 2>/dev/null; then
  rmdir "$REFRESH_LOCK"
  touch "$CONTINUE"
  wait "$WATCH_PID"
  WATCH_PID=''
  fail 'architecture refresh acquired the shared lock during watcher scan'
fi

touch "$CONTINUE"
wait "$WATCH_PID"
WATCH_PID=''
[ ! -e "$REFRESH_LOCK" ] || fail 'watcher left the shared refresh lock behind'

printf '%s\n' 'PASS: watcher excludes architecture refresh during proposal scan'
