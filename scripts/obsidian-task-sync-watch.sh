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
[ -e "$RUNTIME/refresh.lock" ] && exit 0
"$SYNC" scan --hub "$HUB" --scope "$SCOPE" --vault "$VAULT"
