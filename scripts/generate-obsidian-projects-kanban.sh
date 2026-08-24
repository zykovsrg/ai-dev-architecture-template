#!/usr/bin/env bash
# Generate a read-only Obsidian project-board projection.  Source records remain canonical.
set -euo pipefail

die() { printf '%s\n' "error: $*" >&2; exit 1; }
is_absolute() { [[ "$1" = /* ]]; }
sha256() { shasum -a 256 "$@" | shasum -a 256 | awk '{print $1}'; }
json_string() {
  local text="$1"
  text=${text//\\/\\\\}; text=${text//\"/\\\"}; text=${text//$'\n'/\\n}; text=${text//$'\r'/}
  printf '"%s"' "$text"
}
inside() { [[ "$1" == "$2" || "$1" == "$2"/* ]]; }
physical_dir() { cd "$1" && pwd -P; }
resolve_card() {
  local raw="$1" parent canonical_parent root
  case "$raw" in
    /*) die "registry card path must be relative: $raw" ;;
    ai/project-cards/*) ;;
    *) die "registry card path must stay beneath ai/project-cards: $raw" ;;
  esac
  parent="$HUB/$(dirname "$raw")"
  [ -d "$parent" ] && [ ! -L "$parent" ] || die "missing or unsafe card directory: $raw"
  canonical_parent="$(physical_dir "$parent")"
  root="$(physical_dir "$HUB/ai/project-cards")"
  inside "$canonical_parent" "$root" || die "registry card path escapes ai/project-cards: $raw"
  printf '%s/%s\n' "$canonical_parent" "$(basename "$raw")"
}
read_field() { sed -n "s/^$2: //p" "$1" | head -n 1; }
current_state() {
  awk '/^## / { exit } /^Status: / { print substr($0, 9); exit }' "$1"
}
future_state() {
  awk '
    function finish_entry() {
      if (!entry || state == "") return
      if (state == "ready") ready = 1
      else if (state != "idea" && state != "blocked" && state != "promoted" && state != "done" && state != "dropped") invalid = 1
    }
    /^### FT-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9]+[[:space:]]/ {
      finish_entry(); entry = 1; seen = 1; state = ""; next
    }
    /^### / { finish_entry(); entry = 0; state = ""; next }
    entry && /^Status: / {
      value = substr($0, 9)
      if (state == "") state = value
      else if (state != value) invalid = 1
    }
    END {
      finish_entry()
      if (invalid) print "__invalid__"
      else if (ready) print "ready"
      else if (seen) print "none"
    }
  ' "$1"
}
paused_state() {
  awk '
    function finish_entry() {
      if (!entry || state == "") return
      if (state == "paused") paused = 1
      else invalid = 1
    }
    /^### [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][[:space:]]/ {
      finish_entry(); entry = 1; seen = 1; state = ""; next
    }
    /^### / { finish_entry(); entry = 0; state = ""; next }
    entry && /^Status: / {
      value = substr($0, 9)
      if (state == "") state = value
      else if (state != value) invalid = 1
    }
    END {
      finish_entry()
      if (invalid) print "__invalid__"
      else if (paused) print "paused"
      else if (seen) print "none"
    }
  ' "$1"
}
safe_due() {
  sed -nE 's/^[[:space:]]*due:[[:space:]]*([0-9]{4}-[0-9]{2}-[0-9]{2})[[:space:]]*$/\1/p' "$@" |
    sort -u | head -n 1
}
structured_actions() {
  awk '
    /^task:[[:space:]]*$/ { in_task=1; next }
    in_task && /^[^[:space:]]/ { in_task=0 }
    in_task && /^  subtasks:[[:space:]]*$/ { in_subtasks=1; next }
    in_subtasks && /^[^[:space:]]/ { in_subtasks=0 }
    in_subtasks && /^[[:space:]]{4,}-?[[:space:]]*title:[[:space:]]*[^[:space:]].*$/ {
      line=$0; sub(/^[[:space:]]*-[[:space:]]*title:[[:space:]]*/, "", line); print line
    }
  ' "$@" | sed 's/[[:space:]]*$//' | awk 'length && !seen[$0]++' | head -n 7
}

HUB='' SCOPE='' VAULT='' MODE='' CONFIRM=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --hub|--scope|--vault)
      [ "$#" -ge 2 ] || die "missing value for $1"
      case "$1" in --hub) HUB=$2;; --scope) SCOPE=$2;; --vault) VAULT=$2;; esac
      shift 2 ;;
    --preview|--write)
      [ -z "$MODE" ] || die 'choose exactly one of --preview or --write'
      MODE=${1#--}; shift ;;
    --confirm-generated-write) CONFIRM=1; shift ;;
    *) die "unknown flag: $1" ;;
  esac
done

[ -n "$HUB" ] && [ -n "$SCOPE" ] && [ -n "$VAULT" ] && [ -n "$MODE" ] || die 'usage: --hub <absolute-path> --scope <id-file> --vault <copied-vault> (--preview|--write)'
[ "$MODE" = preview ] || [ "$CONFIRM" -eq 1 ] || die 'write requires --confirm-generated-write'
is_absolute "$HUB" && is_absolute "$SCOPE" && is_absolute "$VAULT" || die 'hub, scope, and vault must be absolute paths'
[ -d "$HUB" ] && [ ! -L "$HUB" ] || die 'hub must be a non-symlink directory'
HUB="$(cd "$HUB" && pwd -P)"
[ -f "$SCOPE" ] && [ ! -L "$SCOPE" ] || die 'scope must be a regular non-symlink file'
SCOPE="$(cd "$(dirname "$SCOPE")" && pwd -P)/$(basename "$SCOPE")"
inside "$SCOPE" "$HUB" || die 'scope must be inside hub'

REGISTRY="$HUB/ai/project-registry.md"
[ -f "$REGISTRY" ] && [ ! -L "$REGISTRY" ] || die 'missing or unsafe project registry'
ARCHITECTURE_ID='ai-dev-architecture'
architecture_count="$(grep -Ec "^## ${ARCHITECTURE_ID}$" "$REGISTRY" || true)"
[ "$architecture_count" -eq 1 ] || die 'missing or duplicate registered architecture project'
architecture_block="$(awk -v heading="## $ARCHITECTURE_ID" '$0 == heading {found=1; next} found && /^## / {exit} found {print}' "$REGISTRY")"
architecture_path="$(printf '%s\n' "$architecture_block" | sed -n 's/^Path: //p' | head -n 1)"
[ -n "$architecture_path" ] && is_absolute "$architecture_path" || die 'architecture project path must be absolute'
inside "$architecture_path" "$HUB/projects" || die 'architecture project path outside allowed root'
[ -d "$architecture_path" ] && [ ! -L "$architecture_path" ] || die 'missing or symlinked architecture project'
architecture_real="$(physical_dir "$architecture_path")"
inside "$architecture_real" "$HUB/projects" || die 'architecture project path escapes allowed root'
[ -d "$VAULT" ] && [ ! -L "$VAULT" ] || die 'vault must be a non-symlink directory'
VAULT="$(physical_dir "$VAULT")"
EXPECTED_VAULT="$architecture_real/tmp/obsidian-vault-copy"
inside "$VAULT" "$architecture_real" || die 'vault must be inside the architecture project'
[ "$VAULT" = "$EXPECTED_VAULT" ] || die 'vault must be the copied vault under ai-dev-architecture/tmp/obsidian-vault-copy'
IDS=()
while IFS= read -r id; do
  IDS+=("$id")
done < <(sed '/^[[:space:]]*$/d' "$SCOPE" | sort)
[ "${#IDS[@]}" -gt 0 ] || die 'scope is empty'
if printf '%s\n' "${IDS[@]}" | uniq -d | grep -q .; then die 'duplicate project ID in scope'; fi

if [ "$MODE" = write ]; then
  WORK="$(mktemp -d "$VAULT/.obsidian-board.XXXXXX")"
  trap 'rm -rf "$WORK"' EXIT
fi
PROJECT_PATHS=() CARD_PATHS=() NAMES=() PURPOSES=() COLUMNS=() STATUSES=() SOURCE_HASHES=() DUES=() ACTIONS=()
field() {
  local wanted="$1" key="$2" i
  for i in "${!IDS[@]}"; do
    [ "${IDS[$i]}" = "$wanted" ] || continue
    case "$key" in
      project_path) printf '%s' "${PROJECT_PATHS[$i]}";; card_path) printf '%s' "${CARD_PATHS[$i]}";;
      name) printf '%s' "${NAMES[$i]}";; purpose) printf '%s' "${PURPOSES[$i]}";;
      column) printf '%s' "${COLUMNS[$i]}";; status) printf '%s' "${STATUSES[$i]}";; source_hash) printf '%s' "${SOURCE_HASHES[$i]}";;
    esac
    return
  done
}

for id in "${IDS[@]}"; do
  [[ "$id" =~ ^[a-z0-9][a-z0-9-]*$ ]] || die "invalid project ID: $id"
  count="$(grep -Ec "^## ${id}$" "$REGISTRY" || true)"
  [ "$count" -eq 1 ] || die "unregistered or duplicate project ID: $id"
  block="$(awk -v heading="## $id" '$0 == heading {found=1; next} found && /^## / {exit} found {print}' "$REGISTRY")"
  path="$(printf '%s\n' "$block" | sed -n 's/^Path: //p' | head -n 1)"
  card="$(printf '%s\n' "$block" | sed -n 's/^Card: //p' | head -n 1)"
  [ -n "$path" ] && [ -n "$card" ] || die "registry entry incomplete: $id"
  is_absolute "$path" || die "registry project path must be absolute: $id"
  inside "$path" "$HUB/projects" || die "registry project path outside allowed root: $id"
  card="$(resolve_card "$card")"
  [ -d "$path" ] && [ ! -L "$path" ] && [ -f "$card" ] && [ ! -L "$card" ] || die "missing or symlinked registered source: $id"
  project_real="$(physical_dir "$path")"
  card_parent_real="$(physical_dir "$(dirname "$card")")"
  inside "$project_real" "$HUB/projects" && inside "$card_parent_real" "$HUB/ai/project-cards" || die "registry path escapes allowed root: $id"
  [ -d "$path/ai" ] && [ ! -L "$path/ai" ] || die "unsafe task directory: $id"
  for source in "$path/ai/current-task.md" "$path/ai/future-tasks.md" "$path/ai/paused-tasks.md"; do
    [ -f "$source" ] && [ ! -L "$source" ] || die "missing or symlinked allowed task file: $id"
  done
  name="$(read_field "$card" Name)"
  purpose="$(read_field "$card" Purpose)"
  [ -n "$name" ] || name=$id
  [ -n "$purpose" ] || purpose='нет описания'
  registry_status="$(printf '%s\n' "$block" | sed -n 's/^Status: //p' | head -n 1)"
  current="$(current_state "$path/ai/current-task.md")"
  future="$(future_state "$path/ai/future-tasks.md")"
  paused="$(paused_state "$path/ai/paused-tasks.md")"
  legacy=0
  case "$registry_status" in active|completed|archived) ;; *) legacy=1;; esac
  case "$current" in ''|active|ready|in_progress|waiting|completed|done|review|blocked|paused|empty|none) ;; *) legacy=1;; esac
  case "$future" in ''|ready|none) ;; *) legacy=1;; esac
  case "$paused" in ''|paused|none) ;; *) legacy=1;; esac
  if [ "$registry_status" = archived ]; then column=Archived; status=archived
  elif [ "$legacy" -eq 1 ]; then column=Incoming; status='нужно проверить'
  elif [[ "$current" = active || "$current" = ready || "$current" = in_progress ]]; then column=Active; status=active
  elif [ "$current" = waiting ]; then column=Waiting; status=waiting
  elif [ "$paused" = paused ]; then column=Paused; status=paused
  elif [ "$future" = ready ]; then column=Planned; status=planned
  elif [ "$registry_status" = completed ]; then column=Completed; status=completed
  else column=Incoming; status=incoming
  fi
  due="$(safe_due "$path/ai/current-task.md" "$path/ai/future-tasks.md" "$path/ai/paused-tasks.md")"
  actions="$(structured_actions "$path/ai/current-task.md")"
  PROJECT_PATHS+=("$path"); CARD_PATHS+=("$card"); NAMES+=("$name"); PURPOSES+=("$purpose")
  COLUMNS+=("$column"); STATUSES+=("$status"); DUES+=("$due"); ACTIONS+=("$actions")
  SOURCE_HASHES+=("$(sha256 "$card" "$path/ai/current-task.md" "$path/ai/future-tasks.md" "$path/ai/paused-tasks.md")")
done

BOARD_RENDER="$( {
  printf '%s\n\n' '# Projects Kanban (generated)' '_Источник истины: проектные записи AI. Ручные изменения — proposal pending._'
  for column in Incoming Planned Active Waiting Paused Completed Archived; do
    printf '\n## %s\n' "$column"
    for id in "${IDS[@]}"; do
      [ "$(field "$id" column)" = "$column" ] || continue
      printf '\n- id: %s\n  name: %s\n  purpose: %s\n  status: %s\n' "$id" "$(field "$id" name)" "$(field "$id" purpose)" "$(field "$id" status)"
      if [ "$column" != Archived ]; then
        due=''; actions=''
        for i in "${!IDS[@]}"; do [ "${IDS[$i]}" = "$id" ] && due="${DUES[$i]}" && actions="${ACTIONS[$i]}"; done
        [ -n "$due" ] || due='нет срока'
        printf '  due: %s\n  actions:\n' "$due"
        count=0
        if [ -n "$actions" ]; then
          while IFS= read -r action; do [ -n "$action" ] || continue; printf '    - %s\n' "$action"; count=$((count + 1)); done <<< "$actions"
        fi
        while [ "$count" -lt 3 ]; do printf '%s\n' '    - нет следующего действия'; count=$((count + 1)); done
      fi
    done
  done
} )"

GENERATED_AT="${SOURCE_DATE_EPOCH:-$(date -u +%s)}"
BOARD_HASH="$(printf '%s' "$BOARD_RENDER" | shasum -a 256 | awk '{print $1}')"
MANIFEST_RENDER="$( {
  printf '{\n  "format_version": 1,\n  "generated_at": '
  json_string "$GENERATED_AT"
  printf ',\n  "target": '
  json_string 'Obsidian/AI-архитектура/Projects/_views/Projects-Kanban.md'
  printf ',\n  "board_sha256": '
  json_string "$BOARD_HASH"
  printf ',\n  "sources": [\n'
  comma=''
  for id in "${IDS[@]}"; do
    printf '%s    {"id": ' "$comma"; json_string "$id"
    printf ', "registered_path": '; json_string "$(field "$id" project_path)"
    printf ', "card_path": '; json_string "$(field "$id" card_path)"
    printf ', "sha256": '; json_string "$(field "$id" source_hash)"
    printf '}'
    comma=$',\n'
  done
  printf '\n  ]\n}\n'
} )"

if [ "$MODE" = preview ]; then
  printf '%s' "$BOARD_RENDER"
  printf '\n--- manifest ---\n'
  printf '%s' "$MANIFEST_RENDER"
  exit 0
fi

TARGET_DIR="$VAULT/Obsidian/AI-архитектура/Projects/_views"
TARGET_BOARD="$TARGET_DIR/Projects-Kanban.md"
TARGET_MANIFEST="$TARGET_DIR/Projects-Kanban.manifest.json"
[ -d "$TARGET_DIR" ] && [ ! -L "$TARGET_DIR" ] || die 'target directory missing or symlinked'
for target_part in Obsidian Obsidian/AI-архитектура Obsidian/AI-архитектура/Projects Obsidian/AI-архитектура/Projects/_views; do
  [ ! -L "$VAULT/$target_part" ] || die 'target directory contains a symlink'
done
[ ! -L "$TARGET_BOARD" ] && [ ! -L "$TARGET_MANIFEST" ] || die 'generated targets must not be symlinks'
if [ -e "$TARGET_BOARD" ] || [ -e "$TARGET_MANIFEST" ]; then
  [ -f "$TARGET_BOARD" ] && [ -f "$TARGET_MANIFEST" ] || die 'proposal pending: generated file pair is incomplete'
  recorded="$(sed -n 's/^  "board_sha256": "\([0-9a-f]*\)",$/\1/p' "$TARGET_MANIFEST" | head -n 1)"
  actual="$(shasum -a 256 "$TARGET_BOARD" | awk '{print $1}')"
  [ -n "$recorded" ] && [ "$recorded" = "$actual" ] || die 'proposal pending: manual board edit detected'
fi
tmp_board="$(mktemp "$TARGET_DIR/.Projects-Kanban.md.XXXXXX")"
tmp_manifest="$(mktemp "$TARGET_DIR/.Projects-Kanban.manifest.json.XXXXXX")"
printf '%s' "$BOARD_RENDER" > "$tmp_board"; printf '%s' "$MANIFEST_RENDER" > "$tmp_manifest"
[ "$(shasum -a 256 "$tmp_board" | awk '{print $1}')" = "$BOARD_HASH" ] || die 'temporary board hash validation failed'
[ "$(shasum -a 256 "$tmp_manifest" | awk '{print $1}')" = "$(printf '%s' "$MANIFEST_RENDER" | shasum -a 256 | awk '{print $1}')" ] || die 'temporary manifest hash validation failed'
mv -f "$tmp_board" "$TARGET_BOARD"
mv -f "$tmp_manifest" "$TARGET_MANIFEST"
printf 'wrote %s and %s\n' "$TARGET_BOARD" "$TARGET_MANIFEST"
