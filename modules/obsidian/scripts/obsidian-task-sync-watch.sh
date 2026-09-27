#!/usr/bin/env bash
# Perform one local, non-writing scan for edits to the generated Obsidian board.
set -euo pipefail

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
is_absolute() { [[ "$1" = /* ]]; }
physical_dir() { cd "$1" && pwd -P; }

HUB='' SCOPE='' VAULT='' ONCE=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --hub|--scope|--vault)
      [ "$#" -ge 2 ] || die "missing value for $1"
      case "$1" in --hub) HUB=$2;; --scope) SCOPE=$2;; --vault) VAULT=$2;; esac
      shift 2
      ;;
    --once) ONCE=1; shift;;
    *) die "unknown argument: $1";;
  esac
done

[ "$ONCE" -eq 1 ] || die 'usage: --hub <absolute-path> --scope <absolute-path> --vault <absolute-path> --once'
[ -n "$HUB" ] && [ -n "$SCOPE" ] && [ -n "$VAULT" ] || die 'usage: --hub <absolute-path> --scope <absolute-path> --vault <absolute-path> --once'
is_absolute "$HUB" && is_absolute "$SCOPE" && is_absolute "$VAULT" || die 'hub, scope, and vault must be absolute paths'

require_safe_vault() {
  [ -d "$VAULT" ] && [ ! -L "$VAULT" ] || die 'vault must be a non-symlink directory'
  VAULT="$(physical_dir "$VAULT")"
  RUNTIME="$VAULT/.ai-architecture-sync"
  [ ! -e "$RUNTIME" ] || { [ -d "$RUNTIME" ] && [ ! -L "$RUNTIME" ]; } || die 'runtime directory is unsafe'
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SYNC="$SCRIPT_DIR/obsidian-task-sync.sh"
[ -f "$SYNC" ] && [ ! -L "$SYNC" ] || die 'missing or unsafe task sync command'

require_safe_vault
if [ ! -e "$RUNTIME" ] && [ ! -L "$RUNTIME" ]; then mkdir "$RUNTIME" 2>/dev/null || true; fi
[ -d "$RUNTIME" ] && [ ! -L "$RUNTIME" ] || die 'runtime directory is unsafe'
PROPOSAL="$RUNTIME/pending-proposal.json"

# The generator and watcher share one atomic directory lock. A plain check is
# not enough: the generator could create the lock after the check and replace
# the board while scan is still building its proposal.
REFRESH_LOCK="$RUNTIME/refresh.lock"
if ! mkdir "$REFRESH_LOCK" 2>/dev/null; then
  [ -d "$REFRESH_LOCK" ] && [ ! -L "$REFRESH_LOCK" ] && exit 0
  die 'refresh lock is unsafe'
fi
cleanup_watch_lock() { rmdir "$REFRESH_LOCK" 2>/dev/null || true; }
trap cleanup_watch_lock EXIT

# Each scan is still scoped to one project, so a pending proposal can be
# reviewed and applied by that project's agent. Stop at the first proposal;
# further scans would be refused until it is reviewed or dismissed.
while IFS= read -r project_id; do
  project_id="$(printf '%s' "$project_id" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  [ -n "$project_id" ] || continue
  "$SYNC" scan --project-id "$project_id" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT"
  [ ! -e "$PROPOSAL" ] && [ ! -L "$PROPOSAL" ] || break
done < "$SCOPE"
cleanup_watch_lock
trap - EXIT
