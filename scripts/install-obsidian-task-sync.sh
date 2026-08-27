#!/usr/bin/env bash
# Manage the optional user-level launchd timer that runs the local proposal scan.
set -euo pipefail

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
is_absolute() { [[ "$1" = /* ]]; }
physical_dir() { cd "$1" && pwd -P; }
xml_escape() { local value="$1"; value=${value//&/\&amp;}; value=${value//</\&lt;}; value=${value//>/\&gt;}; value=${value//\"/\&quot;}; value=${value//\'/\&apos;}; printf '%s' "$value"; }

HUB='' SCOPE='' VAULT='' MODE='' CONFIRM_INSTALL=0 CONFIRM_UNINSTALL=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --hub|--scope|--vault)
      [ "$#" -ge 2 ] || die "missing value for $1"
      case "$1" in --hub) HUB=$2;; --scope) SCOPE=$2;; --vault) VAULT=$2;; esac
      shift 2
      ;;
    --preview|--install|--status|--uninstall)
      [ -z "$MODE" ] || die 'choose exactly one mode'
      MODE=${1#--}
      shift
      ;;
    --confirm-launchd-install) CONFIRM_INSTALL=1; shift;;
    --confirm-launchd-uninstall) CONFIRM_UNINSTALL=1; shift;;
    *) die "unknown argument: $1";;
  esac
done

[ -n "$MODE" ] && [ -n "$HUB" ] && [ -n "$SCOPE" ] && [ -n "$VAULT" ] || die 'usage: --hub <absolute-path> --scope <absolute-path> --vault <absolute-path> (--preview|--install|--status|--uninstall)'
is_absolute "$HUB" && is_absolute "$SCOPE" && is_absolute "$VAULT" || die 'hub, scope, and vault must be absolute paths'
[ -d "$HUB" ] && [ ! -L "$HUB" ] || die 'hub must be a non-symlink directory'
[ -f "$SCOPE" ] && [ ! -L "$SCOPE" ] || die 'scope must be a regular non-symlink file'
[ -d "$VAULT" ] && [ ! -L "$VAULT" ] || die 'vault must be a non-symlink directory'
HUB="$(physical_dir "$HUB")"
SCOPE="$(cd "$(dirname "$SCOPE")" && pwd -P)/$(basename "$SCOPE")"
VAULT="$(physical_dir "$VAULT")"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
WATCHER="$SCRIPT_DIR/obsidian-task-sync-watch.sh"
[ -f "$WATCHER" ] && [ ! -L "$WATCHER" ] || die 'missing or unsafe watcher command'

LABEL='com.ai-dev-architecture.obsidian-task-sync'
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$LABEL.plist"
RUNTIME="$VAULT/.ai-architecture-sync"
[ ! -e "$RUNTIME" ] && [ ! -L "$RUNTIME" ] || { [ -d "$RUNTIME" ] && [ ! -L "$RUNTIME" ]; } || die 'runtime directory is unsafe'
LOG_PATH="$RUNTIME/obsidian-task-sync-watch.log"
UID_VALUE="$(id -u)"

plist() {
  cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$(xml_escape "$WATCHER")</string>
    <string>--hub</string>
    <string>$(xml_escape "$HUB")</string>
    <string>--scope</string>
    <string>$(xml_escape "$SCOPE")</string>
    <string>--vault</string>
    <string>$(xml_escape "$VAULT")</string>
    <string>--once</string>
  </array>
  <key>StartInterval</key>
  <integer>10</integer>
  <key>StandardOutPath</key>
  <string>$(xml_escape "$LOG_PATH")</string>
  <key>StandardErrorPath</key>
  <string>$(xml_escape "$LOG_PATH")</string>
</dict>
</plist>
EOF
}

case "$MODE" in
  preview)
    printf 'Preview only; no launchd job will be installed. Target: %s\n\n' "$PLIST_PATH"
    plist
    ;;
  install)
    [ "$CONFIRM_INSTALL" -eq 1 ] || die 'install requires --confirm-launchd-install'
    [ "$CONFIRM_UNINSTALL" -eq 0 ] || die 'install does not accept --confirm-launchd-uninstall'
    [ ! -e "$LAUNCH_AGENTS_DIR" ] || { [ -d "$LAUNCH_AGENTS_DIR" ] && [ ! -L "$LAUNCH_AGENTS_DIR" ]; } || die 'LaunchAgents directory is unsafe'
    mkdir -p "$LAUNCH_AGENTS_DIR"
    if [ ! -e "$RUNTIME" ] && [ ! -L "$RUNTIME" ]; then mkdir "$RUNTIME" || die 'cannot create safe runtime directory'; fi
    [ -d "$RUNTIME" ] && [ ! -L "$RUNTIME" ] || die 'runtime directory is unsafe'
    [ ! -e "$PLIST_PATH" ] || { [ -f "$PLIST_PATH" ] && [ ! -L "$PLIST_PATH" ]; } || die 'plist path is unsafe'
    tmp_plist="$(mktemp "$LAUNCH_AGENTS_DIR/.${LABEL}.XXXXXX")"
    trap 'rm -f "$tmp_plist"' EXIT
    plist > "$tmp_plist"
    mv -f "$tmp_plist" "$PLIST_PATH"
    launchctl bootstrap "gui/$UID_VALUE" "$PLIST_PATH"
    trap - EXIT
    printf 'installed %s\n' "$PLIST_PATH"
    ;;
  status)
    [ "$CONFIRM_INSTALL" -eq 0 ] && [ "$CONFIRM_UNINSTALL" -eq 0 ] || die 'status accepts no confirmation flag'
    if [ -f "$PLIST_PATH" ] && [ ! -L "$PLIST_PATH" ]; then
      printf 'plist: installed at %s\n' "$PLIST_PATH"
    else
      printf 'plist: not installed\n'
    fi
    if launchctl print "gui/$UID_VALUE/$LABEL" >/dev/null 2>&1; then
      printf 'launchd: loaded\n'
    else
      printf 'launchd: not loaded\n'
    fi
    ;;
  uninstall)
    [ "$CONFIRM_UNINSTALL" -eq 1 ] || die 'uninstall requires --confirm-launchd-uninstall'
    [ "$CONFIRM_INSTALL" -eq 0 ] || die 'uninstall does not accept --confirm-launchd-install'
    [ ! -e "$PLIST_PATH" ] || { [ -f "$PLIST_PATH" ] && [ ! -L "$PLIST_PATH" ]; } || die 'plist path is unsafe'
    if launchctl print "gui/$UID_VALUE/$LABEL" >/dev/null 2>&1; then
      launchctl bootout "gui/$UID_VALUE" "$PLIST_PATH"
    fi
    rm -f -- "$PLIST_PATH"
    printf 'uninstalled %s\n' "$PLIST_PATH"
    ;;
esac
