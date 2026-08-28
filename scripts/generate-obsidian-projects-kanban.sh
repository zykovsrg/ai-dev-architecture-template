#!/usr/bin/env bash
# Generate read-only Obsidian task and project views. Source records remain canonical.
set -euo pipefail

die() { printf '%s\n' "error: $*" >&2; exit 1; }
is_absolute() { [[ "$1" = /* ]]; }
inside() { [[ "$1" == "$2" || "$1" == "$2"/* ]]; }
physical_dir() { cd "$1" && pwd -P; }
hash_text() { printf '%s' "$1" | shasum -a 256 | awk '{print $1}'; }
hash_file() { shasum -a 256 "$1" | awk '{print $1}'; }
hash_files() { shasum -a 256 "$@" | shasum -a 256 | awk '{print $1}'; }
json_string() { local text="$1"; text=${text//\\/\\\\}; text=${text//\"/\\\"}; text=${text//$'\n'/\\n}; text=${text//$'\r'/}; printf '"%s"' "$text"; }
read_field() { sed -n "s/^$2: //p" "$1" | head -n 1; }
# The board anchor must be unique inside one file, and a task ID is only unique
# inside its own project, so the anchor carries both. A project ID may not
# contain the separator, otherwise the anchor could not be split back apart.
card_key() { printf '%s--%s' "$1" "$2"; }
current_state() { awk '/^## / { exit } /^Status: / { print substr($0, 9); exit }' "$1"; }
current_title() { awk '/^## Goal[[:space:]]*$/ {goal=1; next} goal && /^## / {exit} goal && NF {print; exit}' "$1" | sed 's/[[:space:]]*$//'; }
validate_task_source() { LC_ALL=C grep -q $'\r' "$1" && die "task source must not contain a carriage return: $1" || true; }
current_task_id() {
  local file="$1" project_id="$2" ids=()
  while IFS= read -r task_id; do ids+=("$task_id"); done < <(sed -n '/^## /q; /^Task ID: /s/^Task ID: //p' "$file")
  [ "${#ids[@]}" -eq 1 ] && [ -n "${ids[0]}" ] || die "renderable current task must have exactly one Task ID: $file"
  ids[0]="$(printf '%s' "${ids[0]}" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  [[ "${ids[0]}" =~ ^TASK-[0-9]{8}-[0-9]{3}$ || "${ids[0]}" =~ ^FT-[0-9]{8}-[0-9]+$ || "${ids[0]}" =~ ^TASK-${project_id}-[0-9]{8}-[0-9]{3}$ ]] || die "invalid Task ID for project $project_id: $file"
  printf '%s' "${ids[0]}"
}
safe_due() { sed -nE 's/^[[:space:]]*due:[[:space:]]*([0-9]{4}-[0-9]{2}-[0-9]{2})[[:space:]]*$/\1/p' "$@" | sort -u | head -n 1; }
table_cell() { local text="$1"; text=${text//|/\\|}; text=${text//$'\n'/ }; printf '%s' "$text"; }

future_records() {
  awk -v project_id="$2" '
    function flush() { if (entry && (state == "idea" || state == "ready" || state == "blocked")) print id "\t" state "\t" title "\t" due }
    function valid_id(value) {
      return value ~ /^FT-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9]+$/ || value ~ ("^TASK-" project_id "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]$")
    }
    /^### (FT-|TASK-)/ {
      flush(); id=$2
      if (!valid_id(id)) {
        if (id ~ /^TASK-/) { printf "error: invalid future Task ID for project %s: %s\n", project_id, FILENAME > "/dev/stderr"; invalid=1 }
        entry=0; next
      }
      entry=1; state=""; due=""; title=$0
      sub(/^### [^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]*/, "", title); next
    }
    /^### / { flush(); entry=0; state=""; due=""; title=""; next }
    entry && /^Status: / { state=substr($0, 9); next }
    entry && /^[[:space:]]*due:[[:space:]]*[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][[:space:]]*$/ { due=$0; sub(/^[[:space:]]*due:[[:space:]]*/, "", due); sub(/[[:space:]]*$/, "", due) }
    END { flush(); exit invalid }
  ' "$1" | sed 's/[[:space:]]*$//'
}
paused_records() {
  awk -v project_id="$2" '
    function valid_id(value) {
      return value ~ /^TASK-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]$/ || value ~ /^FT-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9]+$/ || value ~ ("^TASK-" project_id "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]$")
    }
    function flush() { if (entry && state == "paused") { sub(/^[[:space:]]+/, "", id); sub(/[[:space:]]+$/, "", id); if (id_count != 1 || id == "") { printf "error: renderable paused task must have exactly one Task ID: %s\\n", FILENAME > "/dev/stderr"; invalid=1 } else if (!valid_id(id)) { printf "error: invalid Task ID for project %s: %s\\n", project_id, FILENAME > "/dev/stderr"; invalid=1 } else print id "\t" title } }
    /^### [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][[:space:]]/ { flush(); entry=1; state=""; id=""; id_count=0; title=$0; sub(/^### [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][[:space:]]+[^[:space:]]+[[:space:]]*/, "", title); next }
    /^### / { flush(); entry=0; state=""; id=""; id_count=0; title=""; next }
    entry && /^Task ID: / { id=substr($0, 10); id_count++; next }
    entry && /^Status: / { state=substr($0, 9) }
    END { flush(); exit invalid }
  ' "$1" | sed 's/[[:space:]]*$//'
}
count_future_state() { future_records "$1" "$3" | awk -F '\t' -v wanted="$2" '$2 == wanted {count++} END {print count+0}'; }
resolve_card() {
  local raw="$1" parent canonical_parent root
  case "$raw" in /*) die "registry card path must be relative: $raw";; ai/project-cards/*);; *) die "registry card path must stay beneath ai/project-cards: $raw";; esac
  parent="$HUB/$(dirname "$raw")"; [ -d "$parent" ] && [ ! -L "$parent" ] || die "missing or unsafe card directory: $raw"
  canonical_parent="$(physical_dir "$parent")"; root="$(physical_dir "$HUB/ai/project-cards")"; inside "$canonical_parent" "$root" || die "registry card path escapes ai/project-cards: $raw"
  printf '%s/%s\n' "$canonical_parent" "$(basename "$raw")"
}
resolve_archiproject_group() {
  local requested="$1" count block kind name
  [ -n "$requested" ] && [ "$requested" != none ] || die 'project card must declare primary_archiproject'
  count="$(grep -Ec "^## ${requested}$" "$ARCHIPROJECTS" || true)"
  [ "$count" -eq 1 ] || die "unknown or duplicate primary_archiproject: $requested"
  block="$(awk -v heading="## $requested" '$0 == heading {found=1; next} found && /^## / {exit} found {print}' "$ARCHIPROJECTS")"
  kind="$(printf '%s\n' "$block" | sed -n 's/^kind: //p')"
  [ "$(printf '%s\n' "$kind" | sed '/^$/d' | wc -l | tr -d ' ')" -le 1 ] || die "duplicate archiproject kind: $requested"
  # The project-board migration must read the new explicit group records. The
  # old fixture form had no kind and used unit: project; retain it only as a
  # read-compatible input while explicit non-group records remain rejected.
  if [ -n "$kind" ]; then
    [ "$kind" = group ] || die "primary_archiproject is not a group: $requested"
  else
    printf '%s\n' "$block" | grep -Fxq 'unit: project' || die "primary_archiproject is not a group: $requested"
  fi
  name="$(printf '%s\n' "$block" | sed -n 's/^name: //p')"
  [ "$(printf '%s\n' "$name" | sed '/^$/d' | wc -l | tr -d ' ')" -eq 1 ] && [ -n "$name" ] || die "invalid archiproject name: $requested"
  printf '%s' "$name"
}

HUB='' SCOPE='' VAULT='' MODE='' CONFIRM=0 REFRESH_FROM_ARCHITECTURE=0 REPLACE_CONFIRMED_BOARD=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --hub|--scope|--vault) [ "$#" -ge 2 ] || die "missing value for $1"; case "$1" in --hub) HUB=$2;; --scope) SCOPE=$2;; --vault) VAULT=$2;; esac; shift 2;;
    --preview|--write) [ -z "$MODE" ] || die 'choose exactly one of --preview or --write'; MODE=${1#--}; shift;;
    --confirm-generated-write) CONFIRM=1; shift;;
    --refresh-from-architecture) REFRESH_FROM_ARCHITECTURE=1; shift;;
    --replace-confirmed-board) REPLACE_CONFIRMED_BOARD=1; shift;;
    *) die "unknown flag: $1";;
  esac
done
[ -n "$HUB" ] && [ -n "$SCOPE" ] && [ -n "$VAULT" ] && [ -n "$MODE" ] || die 'usage: --hub <absolute-path> --scope <id-file> --vault <local-vault> (--preview|--write)'
[ "$REFRESH_FROM_ARCHITECTURE" -eq 0 ] || [ "$MODE" = write ] || die '--refresh-from-architecture requires --write'
[ "$REPLACE_CONFIRMED_BOARD" -eq 0 ] || { [ "$MODE" = write ] && [ "$REFRESH_FROM_ARCHITECTURE" -eq 1 ] && [ "$CONFIRM" -eq 1 ]; } || die '--replace-confirmed-board requires --write --refresh-from-architecture --confirm-generated-write'
[ "$MODE" = preview ] || [ "$CONFIRM" -eq 1 ] || [ "$REFRESH_FROM_ARCHITECTURE" -eq 1 ] || die 'write requires --confirm-generated-write'
is_absolute "$HUB" && is_absolute "$SCOPE" && is_absolute "$VAULT" || die 'hub, scope, and vault must be absolute paths'
[ -d "$HUB" ] && [ ! -L "$HUB" ] || die 'hub must be a non-symlink directory'
HUB="$(physical_dir "$HUB")"; [ -f "$SCOPE" ] && [ ! -L "$SCOPE" ] || die 'scope must be a regular non-symlink file'
SCOPE="$(cd "$(dirname "$SCOPE")" && pwd -P)/$(basename "$SCOPE")"; inside "$SCOPE" "$HUB" || die 'scope must be inside hub'
REGISTRY="$HUB/ai/project-registry.md"; [ -f "$REGISTRY" ] && [ ! -L "$REGISTRY" ] || die 'missing or unsafe project registry'
ARCHIPROJECTS="$HUB/ai/archiprojects.md"; [ -f "$ARCHIPROJECTS" ] && [ ! -L "$ARCHIPROJECTS" ] || die 'missing or unsafe archiproject registry'
architecture_block="$(awk '$0 == "## ai-dev-architecture" {found=1; next} found && /^## / {exit} found {print}' "$REGISTRY")"
architecture_path="$(printf '%s\n' "$architecture_block" | sed -n 's/^Path: //p' | head -n 1)"
[ -n "$architecture_path" ] && is_absolute "$architecture_path" && [ -d "$architecture_path" ] && [ ! -L "$architecture_path" ] || die 'missing or unsafe architecture project'
architecture_real="$(physical_dir "$architecture_path")"; inside "$architecture_real" "$HUB/projects" || die 'architecture project path escapes allowed root'; EXPECTED_VAULT="$architecture_real/obsidian-vault"
[ -d "$VAULT" ] && [ ! -L "$VAULT" ] || die 'vault must be a non-symlink directory'; VAULT="$(physical_dir "$VAULT")"
inside "$VAULT" "$architecture_real" && [ "$VAULT" = "$EXPECTED_VAULT" ] || die 'vault must be the local vault under ai-dev-architecture/obsidian-vault'

IDS=(); while IFS= read -r id; do IDS+=("$id"); done < <(sed '/^[[:space:]]*$/d' "$SCOPE" | sort)
[ "${#IDS[@]}" -gt 0 ] || die 'scope is empty'
if printf '%s\n' "${IDS[@]}" | uniq -d | grep -q .; then die 'duplicate project ID in scope'; fi
REGISTRY_IDS=(); while IFS= read -r id; do REGISTRY_IDS+=("$id"); done < <(sed -nE 's/^## ([a-z0-9][a-z0-9-]*)$/\1/p' "$REGISTRY" | sort)
[ "${#REGISTRY_IDS[@]}" -gt 0 ] || die 'registry is empty'
if printf '%s\n' "${REGISTRY_IDS[@]}" | uniq -d | grep -q .; then die 'duplicate project ID in registry'; fi
if [ "$MODE" = write ] && ! cmp -s <(printf '%s\n' "${IDS[@]}") <(printf '%s\n' "${REGISTRY_IDS[@]}"); then die 'write scope must match all registered project IDs'; fi

TASK_IDS=() TASK_COLUMNS=() TASK_TITLES=() TASK_PROJECTS=() TASK_PROJECT_IDS=() TASK_DUES=() TASK_DONE=() TASK_SOURCE_FILES=() TASK_SOURCE_HASHES=()
SOURCE_IDS=() SOURCE_PATHS=() SOURCE_CARDS=() SOURCE_HASHES=(); OVERVIEW_ROWS=''
add_task() {
  [[ "$3" != *$'\t'* ]] || die "task title must not contain a tab: $3"
  TASK_IDS+=("$1"); TASK_COLUMNS+=("$2"); TASK_TITLES+=("$3"); TASK_PROJECTS+=("$4"); TASK_PROJECT_IDS+=("$5"); TASK_DUES+=("$6"); TASK_DONE+=("$7"); TASK_SOURCE_FILES+=("$8"); TASK_SOURCE_HASHES+=("$9")
}

for id in "${IDS[@]}"; do
  [[ "$id" =~ ^[a-z0-9][a-z0-9-]*$ ]] || die "invalid project ID: $id"
  [[ "$id" != *--* ]] || die "project ID must not contain the card key separator: $id"
  [ "$(grep -Ec "^## ${id}$" "$REGISTRY" || true)" -eq 1 ] || die "unregistered or duplicate project ID: $id"
  block="$(awk -v heading="## $id" '$0 == heading {found=1; next} found && /^## / {exit} found {print}' "$REGISTRY")"
  path="$(printf '%s\n' "$block" | sed -n 's/^Path: //p' | head -n 1)"; raw_card="$(printf '%s\n' "$block" | sed -n 's/^Card: //p' | head -n 1)"; registry_status="$(printf '%s\n' "$block" | sed -n 's/^Status: //p' | head -n 1)"
  [ -n "$path" ] && [ -n "$raw_card" ] && is_absolute "$path" && [ -d "$path" ] && [ ! -L "$path" ] && [ -d "$path/ai" ] && [ ! -L "$path/ai" ] || die "registry entry incomplete or unsafe: $id"
  path="$(physical_dir "$path")"; inside "$path" "$HUB/projects" || die "registry project path outside allowed root: $id"; card="$(resolve_card "$raw_card")"
  [ -f "$card" ] && [ ! -L "$card" ] || die "missing or symlinked project card: $id"
  render_tasks=1; [ "$registry_status" = archived ] && render_tasks=0
  current_file="$path/ai/current-task.md"; future_file="$path/ai/future-tasks.md"; paused_file="$path/ai/paused-tasks.md"
  for source in "$current_file" "$future_file" "$paused_file"; do [ -f "$source" ] && [ ! -L "$source" ] || die "missing or symlinked allowed task file: $id"; validate_task_source "$source"; done
  name="$(read_field "$card" Name)"; [ -n "$name" ] || name=$id
  primary_archiproject="$(read_field "$card" primary_archiproject)"
  archiproject_name="$(resolve_archiproject_group "$primary_archiproject")"
  current="$(current_state "$current_file")"; title="$(current_title "$current_file")"; due="$(safe_due "$current_file")"; overview_current='—'
  current_column='' current_done=' '
  case "$current" in
    active) current_column=Active;; ready|in_progress) current_column=Ready;; waiting) current_column=Waiting;; blocked) current_column=Blocked;; review) current_column=Review;; paused) current_column=Paused;; done|completed) current_column=Done; current_done=x;;
  esac
  if [ -n "$current_column" ]; then
    # A substituted placeholder title would differ from the canonical record, so
    # every later scan would propose a rename the user never made.
    [ -n "$title" ] || die "renderable current task must have a goal line: $current_file"
    current_task_id="$(current_task_id "$current_file" "$id")"
    [ "$render_tasks" -eq 0 ] || add_task "$current_task_id" "$current_column" "$title" "$name" "$id" "$due" "$current_done" "$current_file" "$(hash_file "$current_file")"
    overview_current="$title"
  fi
  while IFS=$'\t' read -r future_task_id future_status future_title future_due; do
    [ -n "$future_status" ] || continue
    [ "$render_tasks" -eq 0 ] || case "$future_status" in idea) add_task "$future_task_id" Ideas "$future_title" "$name" "$id" "$future_due" ' ' "$future_file" "$(hash_file "$future_file")";; ready) add_task "$future_task_id" Ready "$future_title" "$name" "$id" "$future_due" ' ' "$future_file" "$(hash_file "$future_file")";; blocked) add_task "$future_task_id" Blocked "$future_title" "$name" "$id" "$future_due" ' ' "$future_file" "$(hash_file "$future_file")";; esac
  done < <(future_records "$future_file" "$id")
  paused_output="$(paused_records "$paused_file" "$id")"
  while IFS=$'\t' read -r paused_task_id paused_title; do [ "$render_tasks" -eq 1 ] && [ -n "$paused_title" ] && add_task "$paused_task_id" Paused "$paused_title" "$name" "$id" '' ' ' "$paused_file" "$(hash_file "$paused_file")"; done <<< "$paused_output"
  OVERVIEW_ROWS+="| [[Projects/$id/Kanban\\\\|$(table_cell "$name")]] | $(table_cell "$archiproject_name") | $(table_cell "$overview_current") |"$'\n'
  SOURCE_IDS+=("$id"); SOURCE_PATHS+=("$path"); SOURCE_CARDS+=("$card"); SOURCE_HASHES+=("$(hash_files "$card" "$current_file" "$future_file" "$paused_file")")
done

# A task ID identifies a task inside its own project. Legacy FT numbers were
# allocated per project and know nothing about their neighbours, so the same
# number in two projects is normal data. The card key is the pair, which is
# also what keeps every anchor unique inside the single board file.
TASK_KEYS=(); for i in "${!TASK_IDS[@]}"; do TASK_KEYS+=("$(card_key "${TASK_PROJECT_IDS[$i]}" "${TASK_IDS[$i]}")"); done
if [ "${#TASK_KEYS[@]}" -gt 0 ]; then
  duplicate_task_keys="$(printf '%s\n' "${TASK_KEYS[@]}" | sort | uniq -d)"
  [ -z "$duplicate_task_keys" ] || die 'duplicate task ID in renderable tasks'
fi
BOARD_RENDERS=() BOARD_TARGETS=() BOARD_HASHES=()
for id in "${IDS[@]}"; do
  board="$( { printf '%s\n' '---' 'kanban-plugin: board' '---'; for column in Ideas Ready Active Waiting Blocked Review Paused Done; do printf '\n## %s\n' "$column"; for i in "${!TASK_COLUMNS[@]}"; do [ "${TASK_PROJECT_IDS[$i]}" = "$id" ] && [ "${TASK_COLUMNS[$i]}" = "$column" ] || continue; printf '\n- [%s] %s ^%s\n' "${TASK_DONE[$i]}" "${TASK_TITLES[$i]}" "${TASK_KEYS[$i]}"; printf '  - project: %s\n' "${TASK_PROJECTS[$i]}"; [ -z "${TASK_DUES[$i]}" ] || printf '  - 📅 %s\n' "${TASK_DUES[$i]}"; done; done; } )"
  BOARD_RENDERS+=("$board"); BOARD_TARGETS+=("Projects/$id/Kanban.md"); BOARD_HASHES+=("$(hash_text "$board")")
done
OVERVIEW_RENDER="$( { printf '%s\n' '# Projects Overview' '' '| Проект | Архипроект | Текущая задача |' '| --- | --- | --- |'; printf '%s' "$OVERVIEW_ROWS"; } )"
OVERVIEW_HASH="$(hash_text "$OVERVIEW_RENDER")"; TASKS_HASH=''; GENERATED_AT="${SOURCE_DATE_EPOCH:-$(date -u +%s)}"
TASK_ENTRIES="$( { comma=''; for i in "${!TASK_IDS[@]}"; do printf '%s    {"task_id": ' "$comma"; json_string "${TASK_IDS[$i]}"; printf ', "project_id": '; json_string "${TASK_PROJECT_IDS[$i]}"; printf ', "source_file": '; json_string "${TASK_SOURCE_FILES[$i]}"; printf ', "source_sha256": '; json_string "${TASK_SOURCE_HASHES[$i]}"; printf '}'; comma=$',\n'; done; } )"
MANIFEST_RENDER="$( { printf '{\n  "format_version": 3,\n  "generated_at": '; json_string "$GENERATED_AT"; printf ',\n  "views": {\n    "tasks_kanban": {"target": "Obsidian/Tasks-Kanban.md", "sha256": '; json_string "$TASKS_HASH"; printf '},\n    "projects_overview": {"target": "Obsidian/Projects-Overview.md", "sha256": '; json_string "$OVERVIEW_HASH"; printf '}\n  },\n  "tasks": [\n%s\n  ],\n  "sources": [\n' "$TASK_ENTRIES"; comma=''; for i in "${!SOURCE_IDS[@]}"; do printf '%s    {"id": ' "$comma"; json_string "${SOURCE_IDS[$i]}"; printf ', "registered_path": '; json_string "${SOURCE_PATHS[$i]}"; printf ', "card_path": '; json_string "${SOURCE_CARDS[$i]}"; printf ', "sha256": '; json_string "${SOURCE_HASHES[$i]}"; printf '}'; comma=$',\n'; done; printf '\n  ]\n}\n'; } )"
BOARD_ENTRIES="$( { comma=''; for i in "${!IDS[@]}"; do printf '%s    {\"project_id\": ' "$comma"; json_string "${IDS[$i]}"; printf ', \"target\": \"Obsidian/%s\", \"sha256\": ' "${BOARD_TARGETS[$i]}"; json_string "${BOARD_HASHES[$i]}"; printf '}'; comma=$',\n'; done; } )"
MANIFEST_RENDER="$( { printf '{\n  \"format_version\": 4,\n  \"generated_at\": '; json_string "$GENERATED_AT"; printf ',\n  \"views\": {\n    \"projects_overview\": {\"target\": \"Obsidian/Projects-Overview.md\", \"sha256\": '; json_string "$OVERVIEW_HASH"; printf '}\n  },\n  \"project_boards\": [\n%s\n  ],\n  \"tasks\": [\n%s\n  ],\n  \"sources\": [\n' "$BOARD_ENTRIES" "$TASK_ENTRIES"; comma=''; for i in "${!SOURCE_IDS[@]}"; do printf '%s    {\"id\": ' "$comma"; json_string "${SOURCE_IDS[$i]}"; printf ', \"registered_path\": '; json_string "${SOURCE_PATHS[$i]}"; printf ', \"card_path\": '; json_string "${SOURCE_CARDS[$i]}"; printf ', \"sha256\": '; json_string "${SOURCE_HASHES[$i]}"; printf '}'; comma=$',\n'; done; printf '\n  ]\n}\n'; } )"

if [ "$MODE" = preview ]; then
  for i in "${!BOARD_RENDERS[@]}"; do printf '%s\n' "${BOARD_RENDERS[$i]}"; done
  printf '%s\n--- projects overview ---\n%s\n--- manifest ---\n%s' '' "$OVERVIEW_RENDER" "$MANIFEST_RENDER"
  exit 0
fi

TARGET_DIR="$VAULT/Obsidian"; TARGET_LEGACY="$TARGET_DIR/Tasks-Kanban.md"; TARGET_OVERVIEW="$TARGET_DIR/Projects-Overview.md"; TARGET_MANIFEST="$TARGET_DIR/AI-Architecture.manifest.json"
[ -d "$TARGET_DIR" ] && [ ! -L "$TARGET_DIR" ] || die 'target directory missing or symlinked'
for rel in "${BOARD_TARGETS[@]}"; do [ ! -L "$TARGET_DIR/$rel" ] || die 'generated targets must not be symlinks'; done
[ ! -L "$TARGET_LEGACY" ] && [ ! -L "$TARGET_OVERVIEW" ] && [ ! -L "$TARGET_MANIFEST" ] || die 'generated targets must not be symlinks'

write_rename_proposal() {
  local board_id="$1" board_file="$2" i actual task_id runtime
  for i in "${!TASK_IDS[@]}"; do
    [ "${TASK_PROJECT_IDS[$i]}" = "$board_id" ] || continue
    actual="$(awk -v suffix=" ^$(card_key "$board_id" "${TASK_IDS[$i]}")" 'substr($0, length($0) - length(suffix) + 1) == suffix {line=$0; sub(/^- \[[ xX]\] /, "", line); sub(/[[:space:]]+\^[^[:space:]]+$/, "", line); print line; exit}' "$board_file")"
    [ "$actual" = "${TASK_TITLES[$i]}" ] && continue
    task_id="${TASK_IDS[$i]}"; break
  done
  [ -n "${task_id:-}" ] && [ -n "${actual:-}" ] || return 1
  runtime="$VAULT/.ai-architecture-sync"; mkdir -p "$runtime"
  { printf '{\n  \"state\": \"ready\",\n  \"operations\": [{\"operation\": \"rename\", \"task_id\": '; json_string "$task_id"; printf ', \"project_id\": '; json_string "$board_id"; printf ', \"from\": '; json_string "${TASK_TITLES[$i]}"; printf ', \"to\": '; json_string "$actual"; printf '}],\n  \"blocked_reasons\": []\n}\n'; } > "$runtime/pending-proposal.json"
}

if [ -e "$TARGET_MANIFEST" ] || [ -e "$TARGET_OVERVIEW" ]; then
  [ -f "$TARGET_MANIFEST" ] && [ -f "$TARGET_OVERVIEW" ] || die 'proposal pending: generated view set is incomplete'
  manifest_format="$(/usr/bin/jq -r '.format_version // empty' "$TARGET_MANIFEST" 2>/dev/null || true)"
  [ "$manifest_format" = 4 ] || { [ "$manifest_format" = 3 ] && die 'proposal pending: manifest v3 requires a fresh confirmed rebuild'; die 'proposal pending: generated manifest is invalid'; }
  recorded_overview="$(/usr/bin/jq -r '.views.projects_overview.sha256 // empty' "$TARGET_MANIFEST")"
  [ "$recorded_overview" = "$(hash_file "$TARGET_OVERVIEW")" ] || die 'proposal pending: manual project overview edit detected'
  for i in "${!BOARD_TARGETS[@]}"; do
    board_file="$TARGET_DIR/${BOARD_TARGETS[$i]}"; [ -f "$board_file" ] || die 'proposal pending: generated view set is incomplete'
    recorded_board="$(/usr/bin/jq -r --arg id "${IDS[$i]}" '[.project_boards[] | select(.project_id == $id) | .sha256] | if length == 1 then .[0] else empty end' "$TARGET_MANIFEST")"
    [ -n "$recorded_board" ] || die 'proposal pending: generated manifest is invalid'
    if [ "$REPLACE_CONFIRMED_BOARD" -eq 0 ] && [ "$recorded_board" != "$(hash_file "$board_file")" ]; then
      [ "$REFRESH_FROM_ARCHITECTURE" -eq 0 ] || write_rename_proposal "${IDS[$i]}" "$board_file" || true
      die 'proposal pending: manual task board edit detected'
    fi
  done
fi

transaction_dir="$TARGET_DIR/.AI-Architecture.generated-write.transaction"
if [ -e "$transaction_dir" ] || [ -L "$transaction_dir" ]; then die 'generated view recovery failed; transaction backup was preserved'; fi
stage_dir="$(mktemp -d "$TARGET_DIR/.AI-Architecture.stage.XXXXXX")"; prepared=0
PUBLISH_TARGETS=("${BOARD_TARGETS[@]}" 'Projects-Overview.md' 'AI-Architecture.manifest.json')
restore_generated_set() {
  local existed rel
  [ -f "$transaction_dir/previous/paths" ] || return 1
  while IFS=' ' read -r existed rel; do
    [ -n "$rel" ] || continue
    if [ "$existed" = 1 ]; then
      mkdir -p "$(dirname "$TARGET_DIR/$rel")" && cp -p "$transaction_dir/previous/$rel" "$TARGET_DIR/$rel" || return 1
    else
      rm -f "$TARGET_DIR/$rel" || return 1
    fi
  done < "$transaction_dir/previous/paths"
}
cleanup_project_write() {
  if [ "$prepared" -eq 1 ]; then
    if restore_generated_set; then prepared=0
    else printf '%s\n' 'error: generated view recovery failed; transaction backup was preserved' >&2; fi
  fi
  [ -z "$stage_dir" ] || rm -rf "$stage_dir"
  [ "$prepared" -eq 1 ] || [ ! -d "$transaction_dir" ] || rm -rf "$transaction_dir"
}
trap cleanup_project_write EXIT

for i in "${!BOARD_TARGETS[@]}"; do
  mkdir -p "$(dirname "$stage_dir/${BOARD_TARGETS[$i]}")"
  printf '%s' "${BOARD_RENDERS[$i]}" > "$stage_dir/${BOARD_TARGETS[$i]}"
  [ "$(hash_file "$stage_dir/${BOARD_TARGETS[$i]}")" = "${BOARD_HASHES[$i]}" ] || die 'temporary project board hash validation failed'
done
printf '%s' "$OVERVIEW_RENDER" > "$stage_dir/Projects-Overview.md"
printf '%s' "$MANIFEST_RENDER" > "$stage_dir/AI-Architecture.manifest.json"
[ "$(hash_file "$stage_dir/Projects-Overview.md")" = "$OVERVIEW_HASH" ] || die 'temporary project overview hash validation failed'
/usr/bin/jq -e '.format_version == 4' "$stage_dir/AI-Architecture.manifest.json" >/dev/null || die 'temporary manifest validation failed'

mkdir "$transaction_dir" && mkdir "$transaction_dir/previous" || die 'generated view transaction already in progress'
for rel in "${PUBLISH_TARGETS[@]}"; do
  if [ -e "$TARGET_DIR/$rel" ]; then
    [ -f "$TARGET_DIR/$rel" ] && mkdir -p "$(dirname "$transaction_dir/previous/$rel")" && cp -p "$TARGET_DIR/$rel" "$transaction_dir/previous/$rel" || die 'generated target is unsafe'
    printf '1 %s\n' "$rel" >> "$transaction_dir/previous/paths"
  else
    printf '0 %s\n' "$rel" >> "$transaction_dir/previous/paths"
  fi
done
: > "$transaction_dir/prepared"; prepared=1
for rel in "${PUBLISH_TARGETS[@]}"; do
  mkdir -p "$(dirname "$TARGET_DIR/$rel")"
  mv -f "$stage_dir/$rel" "$TARGET_DIR/$rel"
done
prepared=0
rm -rf "$transaction_dir"; transaction_dir=''
rm -rf "$stage_dir"; stage_dir=''
[ ! -f "$TARGET_LEGACY" ] || rm -f "$TARGET_LEGACY"
trap - EXIT
printf 'wrote project boards, %s, and %s\n' "$TARGET_OVERVIEW" "$TARGET_MANIFEST"
exit 0
TARGET_DIR="$VAULT/Obsidian"; TARGET_TASKS="$TARGET_DIR/Tasks-Kanban.md"; TARGET_OVERVIEW="$TARGET_DIR/Projects-Overview.md"; TARGET_MANIFEST="$TARGET_DIR/AI-Architecture.manifest.json"
[ -d "$TARGET_DIR" ] && [ ! -L "$TARGET_DIR" ] || die 'target directory missing or symlinked'; [ ! -L "$TARGET_TASKS" ] && [ ! -L "$TARGET_OVERVIEW" ] && [ ! -L "$TARGET_MANIFEST" ] || die 'generated targets must not be symlinks'
transaction_dir="$TARGET_DIR/.AI-Architecture.generated-write.transaction"
tmp_tasks='' tmp_overview='' tmp_manifest='' refresh_lock='' owns_refresh_lock=0 owns_generated_transaction=0 generated_transaction_prepared=0
clear_generated_transaction() {
  rm -f "$transaction_dir/Tasks-Kanban.md" "$transaction_dir/Projects-Overview.md" "$transaction_dir/AI-Architecture.manifest.json" \
    "$transaction_dir/original-set-present" "$transaction_dir/original-set-absent" "$transaction_dir/prepared" || return 1
  rmdir "$transaction_dir"
}
recover_generated_transaction() {
  local mode_count=0
  [ -d "$transaction_dir" ] && [ ! -L "$transaction_dir" ] || return 1
  if [ ! -e "$transaction_dir/prepared" ]; then
    clear_generated_transaction
    return
  fi
  [ -f "$transaction_dir/prepared" ] && [ ! -L "$transaction_dir/prepared" ] || return 1
  [ -f "$transaction_dir/original-set-present" ] && [ ! -L "$transaction_dir/original-set-present" ] && mode_count=$((mode_count + 1))
  [ -f "$transaction_dir/original-set-absent" ] && [ ! -L "$transaction_dir/original-set-absent" ] && mode_count=$((mode_count + 1))
  [ "$mode_count" -eq 1 ] || return 1
  if [ -f "$transaction_dir/original-set-present" ]; then
    for backup in Tasks-Kanban.md Projects-Overview.md AI-Architecture.manifest.json; do
      [ -f "$transaction_dir/$backup" ] && [ ! -L "$transaction_dir/$backup" ] || return 1
    done
    cp -p "$transaction_dir/Tasks-Kanban.md" "$TARGET_TASKS" || return 1
    cp -p "$transaction_dir/Projects-Overview.md" "$TARGET_OVERVIEW" || return 1
    cp -p "$transaction_dir/AI-Architecture.manifest.json" "$TARGET_MANIFEST" || return 1
  else
    rm -f "$TARGET_TASKS" "$TARGET_OVERVIEW" "$TARGET_MANIFEST" || return 1
  fi
  clear_generated_transaction
}
if [ -e "$transaction_dir" ] || [ -L "$transaction_dir" ]; then
  recover_generated_transaction || die 'generated view recovery failed; transaction backup was preserved'
fi

release_refresh_lock() {
  [ "$owns_refresh_lock" -eq 0 ] || rmdir "$refresh_lock" 2>/dev/null || true
  owns_refresh_lock=0
}
if [ "$REFRESH_FROM_ARCHITECTURE" -eq 1 ]; then
  RUNTIME="$VAULT/.ai-architecture-sync"
  if [ -e "$RUNTIME" ] || [ -L "$RUNTIME" ]; then
    [ -d "$RUNTIME" ] && [ ! -L "$RUNTIME" ] || die 'runtime directory is unsafe'
  else
    mkdir "$RUNTIME" || die 'cannot create safe runtime directory'
    [ -d "$RUNTIME" ] && [ ! -L "$RUNTIME" ] || die 'cannot create safe runtime directory'
  fi
  refresh_lock="$RUNTIME/refresh.lock"
  [ ! -e "$refresh_lock" ] && [ ! -L "$refresh_lock" ] || die 'architecture refresh already in progress'
  mkdir "$refresh_lock" || die 'architecture refresh already in progress'
  owns_refresh_lock=1
  trap release_refresh_lock EXIT
fi

guard_manual_board_edit() {
  local script_dir sync
  [ "$REFRESH_FROM_ARCHITECTURE" -eq 1 ] || die 'proposal pending: manual task board edit detected'
  script_dir="$(cd "$(dirname "$0")" && pwd -P)"
  sync="$script_dir/obsidian-task-sync.sh"
  [ -f "$sync" ] && [ ! -L "$sync" ] || die 'proposal pending: manual task board edit detected; task sync command is missing or unsafe'
  "$sync" scan --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" || die 'proposal pending: manual task board edit detected; proposal scan failed'
  die 'proposal pending: manual task board edit detected'
}
if [ -e "$TARGET_TASKS" ] || [ -e "$TARGET_OVERVIEW" ] || [ -e "$TARGET_MANIFEST" ]; then
  [ -f "$TARGET_TASKS" ] && [ -f "$TARGET_OVERVIEW" ] && [ -f "$TARGET_MANIFEST" ] || die 'proposal pending: generated view set is incomplete'
  manifest_format="$(sed -n 's/^  "format_version": \([0-9][0-9]*\),$/\1/p' "$TARGET_MANIFEST")"
  [ "$manifest_format" = 3 ] || { [ "$manifest_format" = 2 ] && die 'proposal pending: manifest v2 requires a fresh confirmed rebuild'; die 'proposal pending: generated manifest is invalid'; }
  recorded_tasks="$(sed -n 's/^    "tasks_kanban": {"target": "Obsidian\/Tasks-Kanban.md", "sha256": "\([0-9a-f]*\)"},$/\1/p' "$TARGET_MANIFEST")"; recorded_overview="$(sed -n 's/^    "projects_overview": {"target": "Obsidian\/Projects-Overview.md", "sha256": "\([0-9a-f]*\)"}$/\1/p' "$TARGET_MANIFEST")"
  [ -n "$recorded_tasks" ] && [ -n "$recorded_overview" ] || die 'proposal pending: generated manifest is invalid'
  [ "$REPLACE_CONFIRMED_BOARD" -eq 1 ] || [ "$recorded_tasks" = "$(shasum -a 256 "$TARGET_TASKS" | awk '{print $1}')" ] || guard_manual_board_edit
  [ "$recorded_overview" = "$(shasum -a 256 "$TARGET_OVERVIEW" | awk '{print $1}')" ] || die 'proposal pending: manual project overview edit detected'
fi
cleanup_generated_write() {
  local recovery_failed=0
  if [ "$generated_transaction_prepared" -eq 1 ]; then
    recover_generated_transaction || recovery_failed=1
  elif [ "$owns_generated_transaction" -eq 1 ]; then
    clear_generated_transaction || recovery_failed=1
  fi
  [ -z "$tmp_tasks" ] || rm -f "$tmp_tasks"
  [ -z "$tmp_overview" ] || rm -f "$tmp_overview"
  [ -z "$tmp_manifest" ] || rm -f "$tmp_manifest"
  release_refresh_lock
  [ "$recovery_failed" -eq 0 ] || printf '%s\n' 'error: generated view recovery failed; transaction backup was preserved' >&2
}
trap cleanup_generated_write EXIT

tmp_tasks="$(mktemp "$TARGET_DIR/.Tasks-Kanban.md.XXXXXX")"; tmp_overview="$(mktemp "$TARGET_DIR/.Projects-Overview.md.XXXXXX")"; tmp_manifest="$(mktemp "$TARGET_DIR/.AI-Architecture.manifest.json.XXXXXX")"
printf '%s' "$TASKS_RENDER" > "$tmp_tasks"; printf '%s' "$OVERVIEW_RENDER" > "$tmp_overview"; printf '%s' "$MANIFEST_RENDER" > "$tmp_manifest"
[ "$(shasum -a 256 "$tmp_tasks" | awk '{print $1}')" = "$TASKS_HASH" ] || die 'temporary task board hash validation failed'; [ "$(shasum -a 256 "$tmp_overview" | awk '{print $1}')" = "$OVERVIEW_HASH" ] || die 'temporary project overview hash validation failed'
mkdir "$transaction_dir" || die 'generated view transaction already in progress'
owns_generated_transaction=1
if [ -f "$TARGET_TASKS" ]; then
  cp -p "$TARGET_TASKS" "$transaction_dir/Tasks-Kanban.md"
  cp -p "$TARGET_OVERVIEW" "$transaction_dir/Projects-Overview.md"
  cp -p "$TARGET_MANIFEST" "$transaction_dir/AI-Architecture.manifest.json"
  : > "$transaction_dir/original-set-present"
else
  : > "$transaction_dir/original-set-absent"
fi
: > "$transaction_dir/prepared"
generated_transaction_prepared=1
mv -f "$tmp_tasks" "$TARGET_TASKS"; tmp_tasks=''
mv -f "$tmp_overview" "$TARGET_OVERVIEW"; tmp_overview=''
mv -f "$tmp_manifest" "$TARGET_MANIFEST"; tmp_manifest=''
generated_transaction_prepared=0
clear_generated_transaction
owns_generated_transaction=0
cleanup_generated_write; trap - EXIT
printf 'wrote %s, %s, and %s\n' "$TARGET_TASKS" "$TARGET_OVERVIEW" "$TARGET_MANIFEST"
