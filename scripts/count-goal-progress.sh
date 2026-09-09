#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="."
GOAL_FILTER=""
AS_OF=""
FORMAT="text"

die() { echo "ERROR: $*" >&2; exit 1; }
while [ $# -gt 0 ]; do
  case "$1" in
    --hub) HUB_DIR="${2:?--hub needs a value}"; shift 2 ;;
    --goal) GOAL_FILTER="${2:?--goal needs a value}"; shift 2 ;;
    --as-of) AS_OF="${2:?--as-of needs a value}"; shift 2 ;;
    --format) FORMAT="${2:?--format needs a value}"; shift 2 ;;
    *) die "unknown option: $1" ;;
  esac
done

[ -n "$AS_OF" ] || AS_OF="$(date +%F)"
case "$FORMAT" in text|tsv) ;; *) die "unknown format: $FORMAT" ;; esac
case "$AS_OF" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;; *) die "--as-of must be YYYY-MM-DD, got: $AS_OF" ;; esac
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
ARCHI_FILE="$HUB_DIR/ai/archiprojects.md"
LOG_FILE="$HUB_DIR/ai/goal-log.md"
[ -f "$ARCHI_FILE" ] || die "missing $ARCHI_FILE"

parse_goals() {
  awk '
    /^```/ { if (inblock) { if (kind == "goal" && id != "" && id !~ /[<>]/) print id "\t" name "\t" status "\t" target "\t" unit "\t" due; inblock=0 } else { inblock=1; id=""; name=""; status=""; kind=""; target=""; unit=""; due="" }; next }
    inblock { line=$0; if (line !~ /:/) next; key=line; sub(/:.*/,"",key); gsub(/[ \t]/,"",key); val=line; sub(/^[^:]*:[ \t]*/,"",val); sub(/[ \t]+$/,"",val); if(key=="id")id=val; else if(key=="name")name=val; else if(key=="status")status=val; else if(key=="kind")kind=val; else if(key=="target")target=val; else if(key=="unit")unit=val; else if(key=="due")due=val }
  ' "$1"
}
GOALS_TSV="$(parse_goals "$ARCHI_FILE")"
DUP_GOAL_ID="$(printf '%s\n' "$GOALS_TSV" | awk -F'\t' '{if(seen[$1]++)print $1}' | head -n1)"
[ -z "$DUP_GOAL_ID" ] || die "duplicate goal_id in $ARCHI_FILE: $DUP_GOAL_ID"
goal_field() { printf '%s\n' "$GOALS_TSV" | awk -F'\t' -v id="$1" -v n="$2" '$1==id{print $n;found=1} END{exit found?0:1}'; }

read_log() {
  [ -f "$LOG_FILE" ] || return 0
  local line trimmed date goal amount col4 col5 rest first_row=1
  while IFS= read -r line || [ -n "$line" ]; do
    trimmed="${line#"${line%%[![:space:]]*}"}"; case "$trimmed" in '|'*) ;; *) continue ;; esac
    line="${trimmed#|}"; IFS='|' read -r date goal amount col4 col5 rest <<EOF_ROW
$line
EOF_ROW
    date="$(printf '%s' "${date:-}" | tr -d ' ')"; goal="$(printf '%s' "${goal:-}" | tr -d ' ')"; amount="$(printf '%s' "${amount:-}" | tr -d ' ')"
    if [ "$first_row" -eq 1 ]; then first_row=0; [ "$goal" = "goal_id" ] && continue; fi
    [[ "$date" =~ ^:?-{3,}:?$ ]] && continue
    [ -n "${col4:-}" ] && [ -n "${col5:-}" ] && [ -z "${rest:-}" ] || die "malformed row in $LOG_FILE: $line"
    case "$date" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;; *) die "bad date in $LOG_FILE: $date" ;; esac
    goal_field "$goal" 1 >/dev/null || die "unknown goal_id in $LOG_FILE: $goal"
    case "$amount" in ''|*[!0-9]*) die "amount must be a positive integer in $LOG_FILE: $amount" ;; esac
    [ "${#amount}" -le 15 ] || die "amount too large in $LOG_FILE: $amount"; [ "$amount" -gt 0 ] || die "amount must be a positive integer in $LOG_FILE: $amount"
    printf '%s\t%s\t%s\n' "$date" "$goal" "$amount"
  done <"$LOG_FILE"
}
epoch_of() { date -u -j -f '%Y-%m-%d %H:%M:%S' "$1 12:00:00" '+%s' 2>/dev/null || date -u -d "$1 12:00:00" '+%s' 2>/dev/null || die "cannot parse date: $1"; }
LOG_TSV="$(read_log)"; AS_OF_EPOCH="$(epoch_of "$AS_OF")"; DAY=86400
sum_between() { local goal="$1" from_epoch="$2" total=0 d g a ts; while IFS=$'\t' read -r d g a; do [ -n "${g:-}" ] && [ "$g" = "$goal" ] || continue; ts="$(epoch_of "$d")"; [ "$ts" -le "$AS_OF_EPOCH" ] && [ "$ts" -ge "$from_epoch" ] || continue; total=$((total+a)); done <<EOF_SUM
$LOG_TSV
EOF_SUM
printf '%s\n' "$total"; }
ru() { LC_ALL=C awk -v v="$1" 'BEGIN{printf "%.1f",v}' | tr '.' ','; }
report_goal() {
  local id="$1" name status target unit due achieved remaining days_left rate7 rate28 needed verdict
  name="$(goal_field "$id" 2)"; status="$(goal_field "$id" 3)"; target="$(goal_field "$id" 4)"; unit="$(goal_field "$id" 5)"; due="$(goal_field "$id" 6)"
  achieved="$(sum_between "$id" 0)"; remaining=$((target-achieved)); [ "$remaining" -lt 0 ] && remaining=0
  rate7="$(sum_between "$id" $((AS_OF_EPOCH-6*DAY)))"; rate28="$(LC_ALL=C awk -v v="$(sum_between "$id" $((AS_OF_EPOCH-27*DAY)))" 'BEGIN{print v/4}')"
  case "$due" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) days_left=$((( $(epoch_of "$due")-AS_OF_EPOCH)/DAY)); [ "$days_left" -lt 0 ] && days_left=0 ;; *) days_left="" ;; esac
  if [ -n "$days_left" ] && [ "$days_left" -gt 0 ]; then needed="$(LC_ALL=C awk -v r="$remaining" -v d="$days_left" 'BEGIN{print r/(d/7)}')"; else needed="$remaining"; fi
  verdict="$(LC_ALL=C awk -v a="$rate7" -v n="$needed" 'BEGIN { print (a >= n) ? "ok" : "slow" }')"
  if [ "$FORMAT" = tsv ]; then printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$id" "$achieved" "$target" "$unit" "$remaining" "$due" "${days_left:-—}" "$rate7" "$rate28" "$needed" "$status" "$verdict"; return; fi
  printf '%s — %s\n' "$id" "$name"; if [ -n "$days_left" ]; then printf 'выпущено %s / %s %s; осталось %s; срок %s (%s дн.)\n' "$achieved" "$target" "$unit" "$remaining" "$due" "$days_left"; else printf 'выпущено %s / %s %s; осталось %s; срока нет\n' "$achieved" "$target" "$unit" "$remaining"; fi
  printf 'темп: %s/нед за 7 дней, %s/нед за 28 дней\n' "$(ru "$rate7")" "$(ru "$rate28")"; if [ "$verdict" = ok ]; then printf 'нужно %s/нед — текущего темпа хватает\n' "$(ru "$needed")"; else printf 'нужно %s/нед — текущего темпа не хватает\n' "$(ru "$needed")"; fi
}
if [ -n "$GOAL_FILTER" ]; then goal_field "$GOAL_FILTER" 1 >/dev/null || die "unknown goal: $GOAL_FILTER"; report_goal "$GOAL_FILTER"; else printf '%s\n' "$GOALS_TSV" | while IFS=$'\t' read -r id _ status _; do [ -n "$id" ] && [ "$status" = active ] || continue; report_goal "$id"; [ "$FORMAT" = text ] && echo ""; done; fi
