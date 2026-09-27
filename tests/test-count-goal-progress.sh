#!/usr/bin/env bash
set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")/.." && pwd -P)/scripts/count-goal-progress.sh"
FAILED=0

pass() { echo "ok   - $1"; }
fail() { echo "FAIL - $1"; [ -n "${2:-}" ] && echo "       $2"; FAILED=1; }

make_hub() {
  local dir
  dir="$(mktemp -d)"
  mkdir -p "$dir/ai"
  cat >"$dir/ai/archiprojects.md" <<'ARCHI'
# Archiprojects

## Schema

## <archiproject-id>

```yaml
id: <archiproject-id>
name: <human name>
status: <status>
kind: goal
target: <target>
unit: <unit>
due: YYYY-MM-DD or none
```

## hadassah

```yaml
id: hadassah
name: Хадасса
status: active
kind: group
```

## promo-32

```yaml
id: promo-32
name: 32 промо-страницы
status: active
kind: goal
target: 32
unit: pages
due: 2026-09-30
```
ARCHI
  cat >"$dir/ai/goal-log.md" <<'LOG'
# Goal Log

| дата | goal_id | сколько | проект | заметка |
| --- | --- | --- | --- | --- |
| 2026-08-20 | promo-32 | 9 | — | задел на старте счётчика |
| 2026-09-05 | promo-32 | 2 | release-page-endoscopy-center | эндоскопия |
| 2026-09-06 | promo-32 | 1 | release-page-stroke-center | инсульт |
LOG
  echo "$dir"
}

make_pace_hub() {
  local due="$1"
  local dir
  dir="$(mktemp -d)"
  mkdir -p "$dir/ai"
  cat >"$dir/ai/archiprojects.md" <<ARCHI
# Archiprojects

## pace-test

\`\`\`yaml
id: pace-test
name: Pace test
status: active
kind: goal
target: 100
unit: units
due: $due
\`\`\`
ARCHI
  cat >"$dir/ai/goal-log.md" <<'LOG'
# Goal Log

| дата | goal_id | сколько | проект | заметка |
| --- | --- | --- | --- | --- |
LOG
  echo "$dir"
}

# --- parsing ---
HUB="$(make_hub)"
out="$(bash "$SCRIPT" --hub "$HUB" --as-of 2026-09-07 --format tsv 2>&1)"

# Check exactly one line of output
line_count="$(printf '%s\n' "$out" | wc -l | tr -d ' ')"
if [ "$line_count" != "1" ]; then
  fail "only kind: goal blocks are counted, schema placeholder skipped" "expected 1 line, got $line_count: $out"
else
  # Verify content: id, target, unit, due in the 12-field report row
  id="$(printf '%s\n' "$out" | cut -f1)"
  target="$(printf '%s\n' "$out" | cut -f3)"
  unit="$(printf '%s\n' "$out" | cut -f4)"
  due="$(printf '%s\n' "$out" | cut -f6)"

  if [ "$id" = "promo-32" ] && [ "$target" = "32" ] && \
     [ "$unit" = "pages" ] && [ "$due" = "2026-09-30" ]; then
    pass "only kind: goal blocks are counted, schema placeholder skipped"
  else
    fail "only kind: goal blocks are counted, schema placeholder skipped" \
      "got: id=$id, target=$target, unit=$unit, due=$due"
  fi
fi
rm -rf "$HUB"

# --- validation ---
expect_failure() {
  local label="$1" logline="$2" needle="$3" hub out rc
  hub="$(make_hub)"
  printf '%s\n' "$logline" >>"$hub/ai/goal-log.md"
  out="$(bash "$SCRIPT" --hub "$hub" --as-of 2026-09-07 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "$needle"; then
    pass "$label"
  else
    fail "$label" "rc=$rc out=$out"
  fi
  rm -rf "$hub"
}

expect_failure "unknown goal_id is rejected" \
  "| 2026-09-06 | no-such-goal | 1 | — | — |" "no-such-goal"
expect_failure "a group id is not a goal" \
  "| 2026-09-06 | hadassah | 1 | — | — |" "hadassah"
expect_failure "malformed date is rejected" \
  "| 06.09.2026 | promo-32 | 1 | — | — |" "06.09.2026"
expect_failure "non-positive amount is rejected" \
  "| 2026-09-06 | promo-32 | 0 | — | — |" "amount must be a positive integer"
expect_failure "short row is rejected" \
  "| 2026-09-06 | promo-32 |" "malformed row"
expect_failure "empty date is rejected" \
  "| | promo-32 | 1 | — | — |" "bad date"

# --- counting ---
HUB="$(make_hub)"
out="$(bash "$SCRIPT" --hub "$HUB" --goal promo-32 --as-of 2026-09-07 2>&1)"
printf '%s' "$out" | grep -q "выпущено 12 / 32 pages" \
  && pass "counts amounts up to --as-of" \
  || fail "counts amounts up to --as-of" "$out"
printf '%s' "$out" | grep -q "осталось 20" \
  && pass "reports remaining" \
  || fail "reports remaining" "$out"
printf '%s' "$out" | grep -q "не хватает" \
  && pass "reports that the pace is short" \
  || fail "reports that the pace is short" "$out"

out="$(bash "$SCRIPT" --hub "$HUB" --goal promo-32 --as-of 2026-09-04 2>&1)"
printf '%s' "$out" | grep -q "выпущено 9 / 32 pages" \
  && pass "--as-of excludes later entries" \
  || fail "--as-of excludes later entries" "$out"

out="$(bash "$SCRIPT" --hub "$HUB" --goal promo-32 --as-of 2026-09-07 --format tsv 2>&1)"
[ "$(printf '%s' "$out" | awk -F'\t' '{print $2"/"$5"/"$12}')" = "12/20/slow" ] \
  && pass "tsv exposes achieved, remaining and verdict" \
  || fail "tsv exposes achieved, remaining and verdict" "$out"
rm -rf "$HUB"

# --- rate7 window boundary (7 days ending on --as-of) ---
HUB="$(make_pace_hub "2099-01-01")"
{
  echo "| 2026-09-01 | pace-test | 5 | — | 6 days before as-of, inside window |"
  echo "| 2026-08-31 | pace-test | 100 | — | 7 days before as-of, outside window |"
} >>"$HUB/ai/goal-log.md"
out="$(bash "$SCRIPT" --hub "$HUB" --goal pace-test --as-of 2026-09-07 --format tsv 2>&1)"
rate7="$(printf '%s' "$out" | awk -F'\t' '{print $8}')"
[ "$rate7" = "5" ] \
  && pass "rate7 sums exactly the 7-day window ending on --as-of" \
  || fail "rate7 sums exactly the 7-day window ending on --as-of" "$out (rate7=$rate7)"
rm -rf "$HUB"

# --- rate28 window and its division by four ---
HUB="$(make_pace_hub "2099-01-01")"
{
  echo "| 2026-08-11 | pace-test | 8 | — | 27 days before as-of, inside window |"
  echo "| 2026-08-10 | pace-test | 100 | — | 28 days before as-of, outside window |"
} >>"$HUB/ai/goal-log.md"
out="$(bash "$SCRIPT" --hub "$HUB" --goal pace-test --as-of 2026-09-07 --format tsv 2>&1)"
rate28="$(printf '%s' "$out" | awk -F'\t' '{print $9}')"
[ "$rate28" = "2" ] \
  && pass "rate28 sums the 28-day window and divides by four" \
  || fail "rate28 sums the 28-day window and divides by four" "$out (rate28=$rate28)"
rm -rf "$HUB"

# --- verdict boundary: rate7 == needed_rate exactly -> ok ---
HUB="$(make_pace_hub "2026-09-14")"
{
  echo "| 2026-08-01 | pace-test | 80 | — | outside the 7-day window |"
  echo "| 2026-09-05 | pace-test | 10 | — | inside the 7-day window |"
} >>"$HUB/ai/goal-log.md"
out="$(bash "$SCRIPT" --hub "$HUB" --goal pace-test --as-of 2026-09-07 --format tsv 2>&1)"
fields="$(printf '%s' "$out" | awk -F'\t' '{print $2"/"$5"/"$8"/"$10"/"$12}')"
[ "$fields" = "90/10/10/10/ok" ] \
  && pass "verdict is ok when rate7 equals needed_rate exactly" \
  || fail "verdict is ok when rate7 equals needed_rate exactly" "$out (fields=$fields)"
rm -rf "$HUB"

# --- one unit less progress in the same fixture -> slow ---
HUB="$(make_pace_hub "2026-09-14")"
{
  echo "| 2026-08-01 | pace-test | 80 | — | outside the 7-day window |"
  echo "| 2026-09-05 | pace-test | 9 | — | one unit less than the boundary fixture |"
} >>"$HUB/ai/goal-log.md"
out="$(bash "$SCRIPT" --hub "$HUB" --goal pace-test --as-of 2026-09-07 --format tsv 2>&1)"
fields="$(printf '%s' "$out" | awk -F'\t' '{print $2"/"$5"/"$8"/"$10"/"$12}')"
[ "$fields" = "89/11/9/11/slow" ] \
  && pass "verdict is slow one unit below the boundary" \
  || fail "verdict is slow one unit below the boundary" "$out (fields=$fields)"
rm -rf "$HUB"


# --- log entry on final line with no trailing newline is not dropped ---
HUB="$(make_hub)"
printf '| 2026-09-02 | promo-32 | 7 | p | b |' >>"$HUB/ai/goal-log.md"
out="$(bash "$SCRIPT" --hub "$HUB" --goal promo-32 --as-of 2026-09-07 2>&1)"
printf '%s' "$out" | grep -q "выпущено 19 / 32 pages" \
  && pass "final log line without trailing newline is still counted" \
  || fail "final log line without trailing newline is still counted" "$out"
rm -rf "$HUB"

# --- indented row is parsed, not silently skipped ---
HUB="$(make_hub)"
printf '  | 2026-09-06 | promo-32 | 5 | p | b |\n' >>"$HUB/ai/goal-log.md"
out="$(bash "$SCRIPT" --hub "$HUB" --goal promo-32 --as-of 2026-09-07 2>&1)"
printf '%s' "$out" | grep -q "выпущено 17 / 32 pages" \
  && pass "row indented by leading whitespace is parsed normally" \
  || fail "row indented by leading whitespace is parsed normally" "$out"
rm -rf "$HUB"

# --- header-like row is only skipped as the actual first row ---
HUB="$(make_hub)"
printf '| notadate | goal_id | -3 | p | b |\n' >>"$HUB/ai/goal-log.md"
out="$(bash "$SCRIPT" --hub "$HUB" --goal promo-32 --as-of 2026-09-07 2>&1)"; rc=$?
[ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "bad date" \
  && pass "header-cell values are rejected as data when not the first row" \
  || fail "header-cell values are rejected as data when not the first row" "rc=$rc out=$out"
rm -rf "$HUB"

# --- short row missing the final column is rejected ---
expect_failure "short row with only four columns is rejected" \
  "| 2026-09-06 | promo-32 | 5 | p" "malformed row"

# --- oversized amount is rejected before the numeric comparison overflows ---
expect_failure "oversized amount is rejected cleanly" \
  "| 2026-09-06 | promo-32 | 99999999999999999999 | p | b |" "amount too large"

# --- duplicated goal id in the registry dies with a clear error ---
HUB="$(make_hub)"
cat >>"$HUB/ai/archiprojects.md" <<'ARCHI'

## promo-32-dup

```yaml
id: promo-32
name: Duplicate
status: active
kind: goal
target: 10
unit: pages
due: 2026-09-30
```
ARCHI
out="$(bash "$SCRIPT" --hub "$HUB" --goal promo-32 --as-of 2026-09-07 2>&1)"; rc=$?
[ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "duplicate goal_id.*promo-32" \
  && pass "duplicated goal id in the registry is rejected with a clear error" \
  || fail "duplicated goal id in the registry is rejected with a clear error" "rc=$rc out=$out"
rm -rf "$HUB"

# --- tsv format always uses a dot decimal separator, regardless of locale ---
HUB="$(make_pace_hub "2099-01-01")"
echo "| 2026-09-01 | pace-test | 34 | — | forces a fractional rate28 |" >>"$HUB/ai/goal-log.md"
# stderr is kept apart: a runner without de_DE.UTF-8 prints a setlocale warning there.
out="$(LC_ALL=de_DE.UTF-8 bash "$SCRIPT" --hub "$HUB" --goal pace-test --as-of 2026-09-07 --format tsv 2>"$HUB/stderr")"
rate28="$(printf '%s' "$out" | awk -F'\t' '{print $9}')"
[ "$rate28" = "8.5" ] \
  && pass "tsv format uses a dot decimal separator under a comma locale" \
  || fail "tsv format uses a dot decimal separator under a comma locale" "$out (rate28=$rate28)"
rm -rf "$HUB"

# --- Russian text mode renders the comma decimal correctly under a comma locale ---
HUB="$(make_pace_hub "2099-01-01")"
echo "| 2026-09-01 | pace-test | 34 | — | forces a fractional rate28 |" >>"$HUB/ai/goal-log.md"
out="$(LC_ALL=de_DE.UTF-8 bash "$SCRIPT" --hub "$HUB" --goal pace-test --as-of 2026-09-07 2>&1)"
printf '%s' "$out" | grep -q '8,5/нед за 28 дней' \
  && ! printf '%s' "$out" | grep -qi 'invalid number' \
  && pass "text mode renders comma decimal correctly under de_DE.UTF-8 locale" \
  || fail "text mode renders comma decimal correctly under de_DE.UTF-8 locale" "$out"
rm -rf "$HUB"

# --- pace window is unaffected by the October DST transition ---
HUB="$(make_pace_hub "2099-01-01")"
echo "| 2026-10-22 | pace-test | 7 | — | 6 days before as-of, across DST |" >>"$HUB/ai/goal-log.md"
out_utc="$(TZ=UTC bash "$SCRIPT" --hub "$HUB" --goal pace-test --as-of 2026-10-28 --format tsv 2>&1)"
out_berlin="$(TZ=Europe/Berlin bash "$SCRIPT" --hub "$HUB" --goal pace-test --as-of 2026-10-28 --format tsv 2>&1)"
rate7_utc="$(printf '%s' "$out_utc" | awk -F'\t' '{print $8}')"
rate7_berlin="$(printf '%s' "$out_berlin" | awk -F'\t' '{print $8}')"
[ "$rate7_utc" = "7" ] && [ "$rate7_berlin" = "7" ] \
  && pass "rate7 window is stable across the October DST transition, UTC vs Europe/Berlin" \
  || fail "rate7 window is stable across the October DST transition, UTC vs Europe/Berlin" \
    "utc=$rate7_utc berlin=$rate7_berlin"
rm -rf "$HUB"

exit "$FAILED"
