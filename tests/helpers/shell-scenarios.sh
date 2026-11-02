# Явные сценарии проверок оболочки с устойчивыми идентификаторами.
#
# Подключение: `source "$ROOT/tests/helpers/shell-scenarios.sh"`, затем
# `scenario_declare <id> <функция>` для каждого сценария и `scenario_main "$@"`.
#
# Обычный запуск без аргументов выполняет все сценарии по порядку, как раньше.
# `--scenario <id>` выполняет один сценарий; `--list-scenarios` только объявляет их.
#
# Строгий сборщик задаёт SCENARIO_EVENT_FD=9 и SCENARIO_DIAG_DIR, открывает канал
# событий на дескрипторе 9 и передаёт одноразовый секрет запуска один раз через
# дескриптор 8. Секрет читается при подключении в неэкспортируемую переменную,
# поэтому дочерние процессы не получают его ни через окружение, ни через дескриптор.
# Проверяемые команды запускаются через scenario_exec: без дескриптора 9 и с
# сохранением их stderr, который сборщик перечитывает перед зачётом отказа.

SCENARIO_IDS=()
SCENARIO_FUNCS=()
SCENARIO_CURRENT=''
SCENARIO__TOKEN=''
SCENARIO__EXEC_COUNT=0
SCENARIO__LAST_DIAG=''
SCENARIO__LAST_CODE=''
SCENARIO__ACCEPT_CODE=''
SCENARIO__ACCEPT_DIAG=''
SCENARIO__LAST_CONTRACT=''

scenario__die() {
  printf 'scenario infrastructure error: %s\n' "$1" >&2
  exit 3
}

scenario__strict() { [ "${SCENARIO_EVENT_FD:-}" = 9 ]; }

if scenario__strict; then
  case "$-" in *a*) scenario__die 'allexport would leak the run secret';; esac
  IFS= read -r SCENARIO__TOKEN <&8 || scenario__die 'run secret is not readable'
  exec 8<&-
  [[ "$SCENARIO__TOKEN" =~ ^[0-9a-f]{32}$ ]] || scenario__die 'invalid run secret'
  [ -d "${SCENARIO_DIAG_DIR:-}" ] && [ ! -L "$SCENARIO_DIAG_DIR" ] || scenario__die 'missing diagnostics directory'
  unset SCENARIO_RUN_ID
fi

scenario__emit() {
  scenario__strict || return 0
  printf '{"v":2,"run":"%s","event":"%s","id":"%s"%s}\n' \
    "$SCENARIO__TOKEN" "$1" "$2" "${3:-}" >&9 || scenario__die 'event channel is not writable'
}

scenario_declare() {
  local id="$1" func="$2" known
  [[ "$id" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || scenario__die "invalid scenario id: $id"
  for known in "${SCENARIO_IDS[@]+"${SCENARIO_IDS[@]}"}"; do
    [ "$known" != "$id" ] || scenario__die "duplicate scenario id: $id"
  done
  SCENARIO_IDS+=("$id")
  SCENARIO_FUNCS+=("$func")
}

scenario_begin() {
  [ -n "$SCENARIO_CURRENT" ] || scenario__die 'scenario_begin outside a scenario'
  SCENARIO__LAST_DIAG=''
  SCENARIO__LAST_CODE=''
  SCENARIO__ACCEPT_CODE=''
  SCENARIO__ACCEPT_DIAG=''
  scenario__emit start "$SCENARIO_CURRENT"
}

# Доверенный тест заранее задаёт точный код и полный stderr предметного исхода.
# Без контракта допустим только код 0 с пустым stderr. Контракт действует до смены.
scenario_accept_exit() {
  [[ "$1" =~ ^[0-9]+$ ]] || scenario__die 'accepted exit code must be a number'
  SCENARIO__ACCEPT_CODE="$1"
  SCENARIO__ACCEPT_DIAG="$2"
}

# scenario_exec <имя-переменной-кода> <команда>...: сохраняет код без `set -e` и `!`.
scenario_exec() {
  local __target="$1" __code __diag='' __accepted='null'
  shift
  if scenario__strict; then
    SCENARIO__EXEC_COUNT=$((SCENARIO__EXEC_COUNT + 1))
    __diag="$SCENARIO_DIAG_DIR/exec-$SCENARIO__EXEC_COUNT.err"
    SCENARIO__LAST_CONTRACT=''
    if [ -n "$SCENARIO__ACCEPT_CODE" ]; then
      SCENARIO__LAST_CONTRACT="$SCENARIO_DIAG_DIR/exec-$SCENARIO__EXEC_COUNT.expected"
      printf '%s' "$SCENARIO__ACCEPT_DIAG" > "$SCENARIO__LAST_CONTRACT"
    fi
    if env -u SCENARIO_EVENT_FD -u SCENARIO_DIAG_DIR "$@" 9>&- 2>"$__diag"; then __code=0; else __code=$?; fi
    cat "$__diag" >&2 || true
  else
    if "$@"; then __code=0; else __code=$?; fi
  fi
  SCENARIO__LAST_DIAG="$__diag"
  SCENARIO__LAST_CODE="$__code"
  if scenario__strict; then
    if [ -n "$SCENARIO__LAST_CONTRACT" ]; then __accepted="$SCENARIO__ACCEPT_CODE"; fi
    scenario__emit exec "$SCENARIO_CURRENT" ",\"actual\":$__code,\"child\":$__code,\"diag\":\"$__diag\",\"accepted\":$__accepted,\"contract\":\"$SCENARIO__LAST_CONTRACT\""
  fi
  printf -v "$__target" '%s' "$__code"
}

# Вызов scenario_assert_exit должен целиком находиться на одной строке теста.
scenario_assert_exit() {
  local expected="$1" actual="$2" file="${BASH_SOURCE[1]}" line="${BASH_LINENO[0]}" child='null' diag='' accepted='null'
  [ -n "$SCENARIO_CURRENT" ] || scenario__die 'scenario_assert_exit outside a scenario'
  [[ "$expected" =~ ^[0-9]+$ && "$actual" =~ ^[0-9]+$ ]] || scenario__die 'exit codes must be numbers'
  case "$file$SCENARIO__LAST_DIAG" in *'"'*|*'\'*|*$'\n'*) scenario__die 'unsupported path';; esac
  if [ -n "$SCENARIO__LAST_DIAG" ]; then child="$SCENARIO__LAST_CODE"; diag="$SCENARIO__LAST_DIAG"; fi
  if [ -n "$SCENARIO__LAST_CONTRACT" ]; then accepted="$SCENARIO__ACCEPT_CODE"; fi
  local contract_fields=",\"accepted\":$accepted,\"contract\":\"$SCENARIO__LAST_CONTRACT\""
  local fields=",\"file\":\"$file\",\"line\":$line,\"expected\":$expected,\"actual\":$actual,\"child\":$child,\"diag\":\"$diag\"$contract_fields"
  if [ "$expected" = "$actual" ]; then
    scenario__emit assert "$SCENARIO_CURRENT" ",\"ok\":true$fields"
    return 0
  fi
  scenario__emit assert "$SCENARIO_CURRENT" ",\"ok\":false$fields"
  printf 'FAIL: %s: expected exit %s, actual %s\n' "$SCENARIO_CURRENT" "$expected" "$actual" >&2
  exit 1
}

scenario_pass() {
  [ -n "$SCENARIO_CURRENT" ] || scenario__die 'scenario_pass outside a scenario'
  scenario__emit pass "$SCENARIO_CURRENT"
}

# Помощник забирает ранее объявленную EXIT-очистку и проверяет её отдельно.
# Событие обязательно даже при отсутствии пользовательской очистки. Если сценарий
# заменит или снимет ловушку, сборщик не получит cleanup-ok и запретит зачёт.
scenario__finish() {
  local original="$1" cleanup_code
  trap - EXIT
  set +e
  (
    set -e
    # В обеих ветках eval получает исходный $?; условие не отключает errexit
    # для самой очистки, поэтому false в её теле прекращает подпроцесс.
    if (exit "$original"); then eval "$SCENARIO__CLEANUP"; else eval "$SCENARIO__CLEANUP"; fi
  )
  cleanup_code=$?
  if [ "$cleanup_code" -ne 0 ]; then exit 3; fi
  scenario__emit cleanup-ok "$SCENARIO__CLEANUP_ID"
  exit "$original"
}

scenario__capture_cleanup() {
  local spec
  spec="$(trap -p EXIT)"
  SCENARIO__CLEANUP=':'
  if [ -n "$spec" ]; then
    spec="${spec#trap -- }"
    spec="${spec% EXIT}"
    eval "SCENARIO__CLEANUP=$spec"
  fi
  trap 'scenario__finish $?' EXIT
}

scenario__run_one() {
  local id="$1" index
  for index in "${!SCENARIO_IDS[@]}"; do
    if [ "${SCENARIO_IDS[$index]}" = "$id" ]; then
      SCENARIO_CURRENT="$id"
      if scenario__strict; then
        SCENARIO__CLEANUP_ID="$id"
        scenario__capture_cleanup
      fi
      "${SCENARIO_FUNCS[$index]}"
      SCENARIO_CURRENT=''
      return 0
    fi
  done
  scenario__die "unknown scenario id: $id"
}

scenario_main() {
  local id selected=() known candidate
  [ "${#SCENARIO_IDS[@]}" -gt 0 ] || scenario__die 'no scenarios declared'
  if scenario__strict; then
    { : >&9; } 2>/dev/null || scenario__die 'event channel is not open'
  fi
  if [ "${1:-}" = --list-scenarios ]; then
    [ "$#" -eq 1 ] || scenario__die 'unexpected arguments'
    for id in "${SCENARIO_IDS[@]}"; do scenario__emit declare "$id"; done
    return 0
  fi
  while [ "$#" -gt 0 ]; do
    [ "$1" = --scenario ] && [ "$#" -ge 2 ] || scenario__die "usage: [--scenario <id>]..."
    for id in "${selected[@]+"${selected[@]}"}"; do [ "$id" != "$2" ] || scenario__die "duplicate selection: $2"; done
    selected+=("$2"); shift 2
  done
  if [ "${#selected[@]}" -eq 0 ]; then selected=("${SCENARIO_IDS[@]}"); fi
  for id in "${selected[@]}"; do
    known=0
    for candidate in "${SCENARIO_IDS[@]}"; do [ "$candidate" != "$id" ] || known=1; done
    [ "$known" -eq 1 ] || scenario__die "unknown scenario id: $id"
  done
  for id in "${selected[@]}"; do scenario__run_one "$id"; done
}
