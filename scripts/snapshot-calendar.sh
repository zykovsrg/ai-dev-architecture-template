#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/lib/calendar-date.sh"
HUB_DIR="."; AT=""; DAY=""; LIST_ONLY=0; PRUNE_ONLY=0
RETENTION_SECONDS=$((14 * 86400))
die() { echo "ERROR: $*" >&2; exit 1; }
while [ $# -gt 0 ]; do
  case "$1" in
    --hub) HUB_DIR="${2:?--hub needs a value}"; shift 2 ;;
    --at) AT="${2:?--at needs a value}"; shift 2 ;;
    --list) LIST_ONLY=1; shift ;;
    --day) DAY="${2:?--day needs a value}"; shift 2 ;;
    --prune-only) PRUNE_ONLY=1; shift ;;
    *) die "unknown option: $1" ;;
  esac
done
if [ "$LIST_ONLY" -eq 1 ]; then
  [ -n "$DAY" ] || die "--list requires --day YYYY-MM-DD"
  valid_calendar_date "$DAY" || die "--day must be a real YYYY-MM-DD date"
elif [ "$PRUNE_ONLY" -eq 0 ]; then
  [ -n "$AT" ] || AT="$(date +%F-%H%M)"
  [[ "$AT" =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2})-([0-9]{2})([0-9]{2})$ ]] || die "--at must be YYYY-MM-DD-HHMM"
  DAY="${BASH_REMATCH[1]}"; HOUR="${BASH_REMATCH[2]}"; MINUTE="${BASH_REMATCH[3]}"
  valid_calendar_date "$DAY" || die "--at has an impossible date: $AT"
  [[ "$HOUR" =~ ^([01][0-9]|2[0-3])$ ]] || die "--at has an impossible hour: $AT"
  [[ "$MINUTE" =~ ^[0-5][0-9]$ ]] || die "--at has an impossible minute: $AT"
fi
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
SNAP_DIR="$HUB_DIR/ai/tmp/calendar-snapshots"
mkdir -p "$SNAP_DIR"
[ ! -L "$SNAP_DIR" ] || die "snapshot directory must not be a symlink"
if [ "$LIST_ONLY" -eq 1 ]; then
  find "$SNAP_DIR" -maxdepth 1 -type f \( -name "$DAY-[0-9][0-9][0-9][0-9].txt" -o -name "$DAY-[0-9][0-9][0-9][0-9]--captured-[0-9]*--*.txt" \) -print | sort
  exit 0
fi
now="$(date +%s)"
for file in "$SNAP_DIR"/*--captured-*--*.txt; do
  [ -e "$file" ] || continue
  base="$(basename "$file")"
  if [[ "$base" =~ --captured-([0-9]+)-- ]]; then
    captured="${BASH_REMATCH[1]}"
    [ "$captured" -lt $((now - RETENTION_SECONDS)) ] && rm -f "$file"
  fi
done
[ "$PRUNE_ONLY" -eq 1 ] && exit 0
stage="$(mktemp "$SNAP_DIR/.snapshot-input.XXXXXX")"
trap 'rm -f "$stage"' EXIT INT TERM
while IFS= read -r line || [ -n "$line" ]; do
  [ -n "$line" ] || continue
  [[ "$line" =~ ^[0-9]{2}:[0-9]{2}\|[0-9]{2}:[0-9]{2}\|[^|]+\|[^|]+$ ]] || die "bad event line: $line"
  printf '%s\n' "$line" >> "$stage"
done
target="$SNAP_DIR/${AT}--captured-${now}--${RANDOM}-${RANDOM}.txt"
while [ -e "$target" ]; do target="$SNAP_DIR/${AT}--captured-${now}--${RANDOM}-${RANDOM}.txt"; done
mv "$stage" "$target"
trap - EXIT INT TERM
printf '%s\n' "$target"
