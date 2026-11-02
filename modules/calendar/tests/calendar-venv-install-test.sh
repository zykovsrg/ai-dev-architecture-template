#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SOURCE="$(cd "$ROOT/../.." && pwd -P)"
SYNC="$ROOT/scripts/sync-calendar-policy.sh"
source "$SOURCE/tests/helpers/shell-scenarios.sh"
WORK="$(mktemp -d "${TMPDIR:-/private/tmp}/calendar-venv-scenarios.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
WORK="$(cd "$WORK" && pwd -P)"

expect_ok() {
  local code
  scenario_accept_exit 1 ''
  scenario_exec code "$@"
  scenario_assert_exit 0 "$code"
}

make_fixture() {
  local name="$1" pip_exit="${2:-0}"
  source_dir="$WORK/$name-source"; hub="$WORK/$name-hub"; tool="$hub/tools/apple-calendar-policy"
  python_stub="$WORK/$name-python"; pip_log="$WORK/$name-pip.log"
  mkdir -p "$source_dir/modules/calendar/policy" "$hub"
  cp -R "$ROOT/policy/src" "$ROOT/policy/bridge" "$source_dir/modules/calendar/policy/"
  cp "$ROOT/policy/pyproject.toml" "$source_dir/modules/calendar/policy/pyproject.toml"
  cat > "$python_stub" <<STUB
#!/usr/bin/env bash
set -euo pipefail
if [ "\$1" = -c ]; then exit 0; fi
if [ "\$1" = -m ] && [ "\$2" = venv ]; then
  dir="\$3"
  mkdir -p "\$dir/bin"
  cat > "\$dir/bin/python" <<'INNER'
#!/usr/bin/env bash
if [ "\$1" = -m ] && [ "\$2" = pip ]; then
  printf '%s\\n' "\$*" >> "$pip_log"
  exit $pip_exit
fi
exit 0
INNER
  chmod +x "\$dir/bin/python"
  exit 0
fi
exit 1
STUB
  chmod +x "$python_stub"
}

install_subject() {
  local code
  scenario_accept_exit 1 ''
  scenario_exec code env HUB_CALENDAR_SKIP_BRIDGE=1 HUB_CALENDAR_SKIP_VENV=0 HUB_CALENDAR_PYTHON="$python_stub" \
    bash "$SYNC" --source "$source_dir" --hub "$hub" "$@" >"$WORK/install.out"
  scenario_assert_exit 0 "$code"
}

creates_environment() {
  scenario_begin
  make_fixture create
  install_subject
  expect_ok test -x "$tool/.venv/bin/python"
  expect_ok test -f "$pip_log"
  expect_ok grep -Fq -- "-m pip install --quiet -e $tool" "$pip_log"
  scenario_pass
}

preserves_existing_environment() {
  scenario_begin
  make_fixture keep
  install_subject
  : > "$pip_log"
  install_subject
  expect_ok grep -Fq "Existing .venv is kept: $tool/.venv" "$WORK/install.out"
  expect_ok test ! -s "$pip_log"
  scenario_pass
}

cleans_failed_environment() {
  local code expected
  scenario_begin
  make_fixture failure 1
  printf -v expected 'ERROR: could not install the calendar server into its venv.\nFinish it by hand:\n  <python3.11+> -m venv "%s/.venv"\n  "%s/.venv/bin/python" -m pip install -e "%s"\nERROR: calendar server venv was not created\n' "$tool" "$tool" "$tool"
  scenario_accept_exit 1 "$expected"
  scenario_exec code env HUB_CALENDAR_SKIP_BRIDGE=1 HUB_CALENDAR_SKIP_VENV=0 HUB_CALENDAR_PYTHON="$python_stub" \
    bash "$SYNC" --source "$source_dir" --hub "$hub" >"$WORK/failure.out"
  scenario_assert_exit 1 "$code"
  expect_ok test ! -e "$tool/.venv"
  scenario_pass
}

dry_run_new_environment() {
  scenario_begin
  make_fixture dry-new
  install_subject --dry-run
  expect_ok grep -Fq "Would create $tool/.venv" "$WORK/install.out"
  expect_ok test ! -e "$hub/tools"
  expect_ok test ! -e "$pip_log"
  scenario_pass
}

dry_run_existing_environment() {
  scenario_begin
  make_fixture dry-existing
  install_subject
  : > "$pip_log"
  install_subject --dry-run
  expect_ok grep -Fq "Existing .venv is kept: $tool/.venv" "$WORK/install.out"
  expect_ok test ! -s "$pip_log"
  scenario_pass
}

explicit_skip() {
  local code
  scenario_begin
  make_fixture skip
  scenario_exec code env HUB_CALENDAR_SKIP_BRIDGE=1 HUB_CALENDAR_SKIP_VENV=1 HUB_CALENDAR_PYTHON="$python_stub" \
    bash "$SYNC" --source "$source_dir" --hub "$hub" >"$WORK/skip.out"
  scenario_assert_exit 0 "$code"
  expect_ok grep -Fq 'Calendar server venv step skipped: HUB_CALENDAR_SKIP_VENV=1.' "$WORK/skip.out"
  expect_ok test ! -e "$tool/.venv"
  expect_ok test ! -e "$pip_log"
  scenario_pass
}

scenario_declare venv-create-and-install-editable creates_environment
scenario_declare venv-rerun-keeps-environment preserves_existing_environment
scenario_declare venv-failed-pip-removes-environment cleans_failed_environment
scenario_declare venv-dry-run-new-environment dry_run_new_environment
scenario_declare venv-dry-run-existing-environment dry_run_existing_environment
scenario_declare venv-explicit-skip explicit_skip
scenario_main "$@"
