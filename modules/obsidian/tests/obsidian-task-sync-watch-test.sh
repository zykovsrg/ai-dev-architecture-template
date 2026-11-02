#!/usr/bin/env bash
# Только временный дочерний процесс: ограниченные ожидания и обязательный wait.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
source "$ROOT/tests/helpers/shell-scenarios.sh"
RUN_DIR="$(mktemp -d /private/tmp/obsidian-task-sync-watch.XXXXXX)"
trap 'rm -rf "$RUN_DIR"' EXIT

watcher_holds_refresh_lock_through_scan() {
  scenario_begin
  local tmp hub scope vault runtime started continue rc
  tmp="$(mktemp -d "$RUN_DIR/case.XXXXXX")"
  mkdir -p "$tmp/home" "$tmp/tmp"
  export HOME="$tmp/home" TMPDIR="$tmp/tmp"
  hub="$tmp/hub"; scope="$hub/scope.txt"
  vault="$hub/projects/ai-dev-architecture/obsidian-vault"
  runtime="$vault/.ai-architecture-sync"
  started="$tmp/scan-started"; continue="$tmp/scan-continue"
  mkdir -p "$runtime" "$tmp/stage"
  bash "$ROOT/modules/obsidian/tests/stage-scripts.sh" "$tmp/stage"
  printf '%s\n' ai-dev-architecture > "$scope"
  cat > "$tmp/stage/obsidian-task-sync.sh" <<'FIXTURE'
#!/usr/bin/env bash
set -euo pipefail
[ "${1:-}" = scan ] && [ "${2:-}" = --project-id ] && [ "${3:-}" = ai-dev-architecture ] || {
  printf '%s\n' 'watcher did not select its scoped project' >&2; exit 95;
}
touch "$AI_SYNC_TEST_STARTED"
for ((i=0; i<500; i++)); do
  if [ -e "$AI_SYNC_TEST_CONTINUE" ]; then
    printf '%s\n' '{"state":"ready","stale":true}' > "$AI_SYNC_TEST_RUNTIME/pending-proposal.json"
    exit 0
  fi
  sleep 0.01
done
printf '%s\n' 'synthetic scan continuation timed out' >&2
exit 96
FIXTURE
  chmod +x "$tmp/stage/obsidian-task-sync.sh"
  # Код 1 с пустым stderr означает только нарушение проверяемого свойства.
  # Авария, ошибка запуска и тайм-аут получают код 3 и диагностическое сообщение.
  scenario_accept_exit 1 ''
  scenario_exec rc python3 - "$tmp/stage/obsidian-task-sync-watch.sh" "$hub" "$scope" "$vault" "$runtime" "$started" "$continue" <<'CHECK'
import os,pathlib,signal,subprocess,sys,time
watcher,hub,scope,vault,runtime,started,release=sys.argv[1:]
started=pathlib.Path(started); release=pathlib.Path(release); lock=pathlib.Path(runtime)/'refresh.lock'
env=dict(os.environ,AI_SYNC_TEST_STARTED=str(started),AI_SYNC_TEST_CONTINUE=str(release),AI_SYNC_TEST_RUNTIME=runtime)
child=None
def interrupted(signum, frame):
    raise RuntimeError('watcher fixture interrupted by signal '+str(signum))
signal.signal(signal.SIGTERM,interrupted)
signal.signal(signal.SIGINT,interrupted)
try:
    child=subprocess.Popen(['bash',watcher,'--hub',hub,'--scope',scope,'--vault',vault,'--once'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    deadline=time.monotonic()+6
    while not started.exists():
        if child.poll() is not None:
            out,err=child.communicate(); sys.stdout.buffer.write(out); sys.stderr.buffer.write(err)
            raise RuntimeError('watcher stopped before synthetic scan started')
        if time.monotonic()>=deadline: raise RuntimeError('synthetic scan startup timed out')
        time.sleep(.01)
    held=True
    try:
        lock.mkdir()
    except FileExistsError:
        held=lock.is_dir() and not lock.is_symlink()
    else:
        held=False; lock.rmdir()
    release.touch()
    out,err=child.communicate(timeout=6)
    sys.stdout.buffer.write(out); sys.stderr.buffer.write(err)
    if child.returncode!=0 or err:
        raise RuntimeError('watcher command did not complete with exit 0 and empty stderr')
    # Оба утверждения относятся к одному жизненному циклу блокировки.
    result=0 if held and not lock.exists() and not lock.is_symlink() else 1
except Exception as error:
    print('watcher fixture infrastructure: '+str(error),file=sys.stderr)
    result=3
finally:
    if child is not None:
        try: release.touch()
        except OSError as error:
            print('watcher fixture cleanup: '+str(error),file=sys.stderr)
            result=3
        # Завершить также искусственный scan, если watcher аварийно вышел раньше него.
        try: os.killpg(child.pid,signal.SIGTERM)
        except ProcessLookupError: pass
        try: child.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            try: os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            child.communicate(timeout=1)
        child.wait()
        try: os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError: pass
sys.exit(result)
CHECK
  scenario_assert_exit 0 "$rc"
  scenario_pass
}
scenario_declare watcher-holds-refresh-lock-through-scan watcher_holds_refresh_lock_through_scan
scenario_main "$@"
