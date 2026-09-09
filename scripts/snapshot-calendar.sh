#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="."
AT=""
PRUNE_ONLY=0
RETENTION_DAYS=14
die() { echo "ERROR: $*" >&2; exit 1; }
while [ $# -gt 0 ]; do
  case "$1" in
    --hub) HUB_DIR="${2:?--hub needs a value}"; shift 2 ;;
    --at) AT="${2:?--at needs a value}"; shift 2 ;;
    --prune-only) PRUNE_ONLY=1; shift ;;
    *) die "unknown option: $1" ;;
  esac
done
[ -n "$AT" ] || AT="$(date +%F-%H%M)"
case "$AT" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]) ;; *) die "--at must be YYYY-MM-DD-HHMM, got: $AT" ;; esac
AT_MONTH="${AT:5:2}"; AT_DAY="${AT:8:2}"; AT_HOUR="${AT:11:2}"; AT_MIN="${AT:13:2}"
case "$AT_MONTH" in 0[1-9]|1[0-2]) ;; *) die "--at has an impossible month: $AT" ;; esac
case "$AT_DAY" in 0[1-9]|[12][0-9]|3[01]) ;; *) die "--at has an impossible day: $AT" ;; esac
case "$AT_HOUR" in [01][0-9]|2[0-3]) ;; *) die "--at has an impossible hour: $AT" ;; esac
case "$AT_MIN" in [0-5][0-9]) ;; *) die "--at has an impossible minute: $AT" ;; esac
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
SNAP_DIR="$HUB_DIR/ai/tmp/calendar-snapshots"
FRICTION_DIR="$HUB_DIR/ai/tmp/workflow-friction"
mkdir -p "$SNAP_DIR" "$FRICTION_DIR"
DAY="${AT%-*}"
CUTOFF="$(date -j -v-"${RETENTION_DAYS}"d -f %Y-%m-%d "$DAY" +%F)" || die "cannot compute the retention cutoff for: $DAY"
prune_dir() {
  local dir="$1" f base filedate
  for f in "$dir"/*.txt; do
    [ -e "$f" ] || continue
    base="$(basename "$f" .txt)"; filedate="$(printf '%s' "$base" | cut -c1-10)"
    case "$filedate" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;; *) continue ;; esac
    [ "$filedate" \< "$CUTOFF" ] && rm -f "$f"
  done
}
prune_dir "$SNAP_DIR"; prune_dir "$FRICTION_DIR"
[ "$PRUNE_ONLY" -eq 1 ] && exit 0
TARGET="$SNAP_DIR/$AT.txt"; TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT INT TERM
bad_line() { die "bad event line: $1"; }
while IFS= read -r line || [ -n "$line" ]; do
  [ -n "$line" ] || continue
  case "$line" in [0-9][0-9]:[0-9][0-9]\|[0-9][0-9]:[0-9][0-9]\|*\|*) ;; *) bad_line "$line" ;; esac
  REST="${line#*|}"; REST="${REST#*|}"; TITLE="${REST%%|*}"; CAL="${REST#*|}"
  case "$CAL" in *\|*) bad_line "$line" ;; esac
  [ -n "$TITLE" ] && [ -n "$CAL" ] || bad_line "$line"
  printf '%s\n' "$line" >>"$TMP"
done
mv "$TMP" "$TARGET"; trap - EXIT INT TERM; printf '%s\n' "$TARGET"
