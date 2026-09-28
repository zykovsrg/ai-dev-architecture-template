#!/usr/bin/env bash
set -euo pipefail

# Covers the calendar server venv step of sync-calendar-policy.sh: creation
# with a chosen interpreter, an existing venv being left untouched, the
# failure path removing a half-made venv, and --dry-run wording. Uses a
# stubbed HUB_CALENDAR_PYTHON so it needs no real Python >=3.11 and no
# network. HUB_CALENDAR_SKIP_BRIDGE=1 keeps the macOS bridge build out of
# scope for this test.

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SYNC="$ROOT/scripts/sync-calendar-policy.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
WORK="$(cd "$WORK" && pwd -P)"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

make_source() {
  local dest="$WORK/$1"
  mkdir -p "$dest/scripts" "$dest/modules/calendar/policy"
  cp -R "$ROOT/policy/src" "$dest/modules/calendar/policy/src"
  cp -R "$ROOT/policy/bridge" "$dest/modules/calendar/policy/bridge"
  cp "$ROOT/policy/pyproject.toml" "$dest/modules/calendar/policy/pyproject.toml"
  printf '%s\n' "$dest"
}

make_hub() {
  local hub="$WORK/$1"
  mkdir -p "$hub"
  printf '%s\n' "$hub"
}

# A stub "python" interpreter: `-c ...` reports a satisfying version, `-m venv
# DIR` creates DIR/bin/python as a second stub that logs any `-m pip install`
# invocation to $STUB_LOG and exits with $PIP_EXIT (default 0).
make_python_stub() {
  local path="$1" log="$2" pip_exit="${3:-0}"
  cat > "$path" <<STUB
#!/usr/bin/env bash
if [ "\$1" = "-c" ]; then
  exit 0
fi
if [ "\$1" = "-m" ] && [ "\$2" = "venv" ]; then
  dir="\$3"
  mkdir -p "\$dir/bin"
  cat > "\$dir/bin/python" <<INNER
#!/usr/bin/env bash
if [ "\\\$1" = "-m" ] && [ "\\\$2" = "pip" ]; then
  printf '%s\\n' "\\\$*" >> "$log"
  exit $pip_exit
fi
exit 0
INNER
  chmod +x "\$dir/bin/python"
  exit 0
fi
exit 1
STUB
  chmod +x "$path"
}

source_dir="$(make_source source-1)"

# 1. Fresh install with no existing venv creates one and installs editable.
hub1="$(make_hub hub-1)"
log1="$WORK/pip-1.log"
python_stub1="$WORK/python-stub-1"
make_python_stub "$python_stub1" "$log1" 0
HUB_CALENDAR_SKIP_BRIDGE=1 HUB_CALENDAR_PYTHON="$python_stub1" \
  bash "$SYNC" --source "$source_dir" --hub "$hub1" >/dev/null

tool1="$hub1/tools/apple-calendar-policy"
[ -x "$tool1/.venv/bin/python" ] || fail "venv python was not created"
[ -f "$log1" ] || fail "pip was never invoked"
grep -Fq -- "-m pip install --quiet -e $tool1" "$log1" \
  || fail "pip was not called with -e on the tool dir: $(cat "$log1")"

# 2. A second run must keep the existing venv and must not call pip again.
: > "$log1"
out2="$(HUB_CALENDAR_SKIP_BRIDGE=1 HUB_CALENDAR_PYTHON="$python_stub1" \
  bash "$SYNC" --source "$source_dir" --hub "$hub1")"
printf '%s\n' "$out2" | grep -Fq "Existing .venv is kept: $tool1/.venv" \
  || fail "rerun did not report the venv as kept: $out2"
[ ! -s "$log1" ] || fail "rerun called pip again: $(cat "$log1")"

# 3. Failure path: pip fails during a fresh install. The half-made venv is
# removed and the whole install fails.
hub3="$(make_hub hub-3)"
log3="$WORK/pip-3.log"
python_stub3="$WORK/python-stub-3"
make_python_stub "$python_stub3" "$log3" 1
if HUB_CALENDAR_SKIP_BRIDGE=1 HUB_CALENDAR_PYTHON="$python_stub3" \
     bash "$SYNC" --source "$source_dir" --hub "$hub3" >/dev/null 2>"$WORK/err3"; then
  fail "install succeeded despite a failing pip"
fi
tool3="$hub3/tools/apple-calendar-policy"
[ ! -e "$tool3/.venv" ] || fail "a half-made venv survived the failure"
grep -Fq "ERROR" "$WORK/err3" || fail "no ERROR was printed on failure: $(cat "$WORK/err3")"

# 4. --dry-run reports "would create" for a fresh hub and "is kept" for one
# that already has a venv; it writes nothing.
hub4="$(make_hub hub-4)"
out4="$(HUB_CALENDAR_SKIP_BRIDGE=1 HUB_CALENDAR_PYTHON="$python_stub1" \
  bash "$SYNC" --source "$source_dir" --hub "$hub4" --dry-run)"
printf '%s\n' "$out4" | grep -Fq "Would create $hub4/tools/apple-calendar-policy/.venv" \
  || fail "dry run did not announce venv creation: $out4"
[ ! -e "$hub4/tools" ] || fail "dry run created files"

out1_dry="$(HUB_CALENDAR_SKIP_BRIDGE=1 HUB_CALENDAR_PYTHON="$python_stub1" \
  bash "$SYNC" --source "$source_dir" --hub "$hub1" --dry-run)"
printf '%s\n' "$out1_dry" | grep -Fq "Existing .venv is kept: $tool1/.venv" \
  || fail "dry run did not report an existing venv as kept: $out1_dry"

# 5. HUB_CALENDAR_SKIP_VENV=1 skips the step entirely and says so.
hub5="$(make_hub hub-5)"
out5="$(HUB_CALENDAR_SKIP_BRIDGE=1 HUB_CALENDAR_SKIP_VENV=1 \
  bash "$SYNC" --source "$source_dir" --hub "$hub5")"
printf '%s\n' "$out5" | grep -Fq "Calendar server venv step skipped: HUB_CALENDAR_SKIP_VENV=1." \
  || fail "skip was not reported: $out5"
[ ! -e "$hub5/tools/apple-calendar-policy/.venv" ] || fail "venv was created despite the skip"

printf 'PASS: calendar server venv is created, kept, cleaned up on failure, and skippable.\n'
