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
current_state() { awk '/^## / { exit } /^Status: / { print substr($0, 9); exit }' "$1"; }
current_title() { awk '/^## Goal[[:space:]]*$/ {goal=1; next} goal && /^## / {exit} goal && NF {print; exit}' "$1" | sed 's/[[:space:]]*$//'; }
current_task_id() {
  local file="$1" ids=()
  while IFS= read -r task_id; do ids+=("$task_id"); done < <(sed -n '/^## /q; /^Task ID: /s/^Task ID: //p' "$file")
  [ "${#ids[@]}" -eq 1 ] && [ -n "${ids[0]}" ] || die "renderable current task must have exactly one Task ID: $file"
  ids[0]="$(printf '%s' "${ids[0]}" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  [[ "${ids[0]}" =~ ^TASK-[0-9]{8}-[0-9]{3}$ ]] || die "invalid Task ID: $file"
  printf '%s' "${ids[0]}"
}
safe_due() { sed -nE 's/^[[:space:]]*due:[[:space:]]*([0-9]{4}-[0-9]{2}-[0-9]{2})[[:space:]]*$/\1/p' "$@" | sort -u | head -n 1; }
table_cell() { local text="$1"; text=${text//|/\\|}; text=${text//$'\n'/ }; printf '%s' "$text"; }

future_records() {
  awk '
    function flush() { if (entry && (state == "idea" || state == "ready" || state == "blocked")) print id "\t" state "\t" title "\t" due }
    /^### FT-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9]+[[:space:]]/ {
      flush(); entry=1; state=""; due=""; id=$2; title=$0
      sub(/^### FT-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9]+[[:space:]]+[^[:space:]]+[[:space:]]*/, "", title); next
    }
    /^### / { flush(); entry=0; state=""; due=""; title=""; next }
    entry && /^Status: / { state=substr($0, 9); next }
    entry && /^[[:space:]]*due:[[:space:]]*[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][[:space:]]*$/ { due=$0; sub(/^[[:space:]]*due:[[:space:]]*/, "", due); sub(/[[:space:]]*$/, "", due) }
    END { flush() }
  ' "$1" | sed 's/[[:space:]]*$//'
}
paused_records() {
  awk '
    function flush() { if (entry && state == "paused") { sub(/^[[:space:]]+/, "", id); sub(/[[:space:]]+$/, "", id); if (id_count != 1 || id == "") { printf "error: renderable paused task must have exactly one Task ID: %s\\n", FILENAME > "/dev/stderr"; invalid=1 } else if (id !~ /^TASK-[0-9]{8}-[0-9]{3}$/) { printf "error: invalid Task ID: %s\\n", FILENAME > "/dev/stderr"; invalid=1 } else print id "\t" title } }
    /^### [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][[:space:]]/ { flush(); entry=1; state=""; id=""; id_count=0; title=$0; sub(/^### [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][[:space:]]+[^[:space:]]+[[:space:]]*/, "", title); next }
    /^### / { flush(); entry=0; state=""; id=""; id_count=0; title=""; next }
    entry && /^Task ID: / { id=substr($0, 10); id_count++; next }
    entry && /^Status: / { state=substr($0, 9) }
    END { flush(); exit invalid }
  ' "$1" | sed 's/[[:space:]]*$//'
}
count_future_state() { future_records "$1" | awk -F '\t' -v wanted="$2" '$2 == wanted {count++} END {print count+0}'; }
resolve_card() {
  local raw="$1" parent canonical_parent root
  case "$raw" in /*) die "registry card path must be relative: $raw";; ai/project-cards/*);; *) die "registry card path must stay beneath ai/project-cards: $raw";; esac
  parent="$HUB/$(dirname "$raw")"; [ -d "$parent" ] && [ ! -L "$parent" ] || die "missing or unsafe card directory: $raw"
  canonical_parent="$(physical_dir "$parent")"; root="$(physical_dir "$HUB/ai/project-cards")"; inside "$canonical_parent" "$root" || die "registry card path escapes ai/project-cards: $raw"
  printf '%s/%s\n' "$canonical_parent" "$(basename "$raw")"
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
  TASK_IDS+=("$1"); TASK_COLUMNS+=("$2"); TASK_TITLES+=("$3"); TASK_PROJECTS+=("$4"); TASK_PROJECT_IDS+=("$5"); TASK_DUES+=("$6"); TASK_DONE+=("$7"); TASK_SOURCE_FILES+=("$8"); TASK_SOURCE_HASHES+=("$9")
}

for id in "${IDS[@]}"; do
  [[ "$id" =~ ^[a-z0-9][a-z0-9-]*$ ]] || die "invalid project ID: $id"
  [ "$(grep -Ec "^## ${id}$" "$REGISTRY" || true)" -eq 1 ] || die "unregistered or duplicate project ID: $id"
  block="$(awk -v heading="## $id" '$0 == heading {found=1; next} found && /^## / {exit} found {print}' "$REGISTRY")"
  path="$(printf '%s\n' "$block" | sed -n 's/^Path: //p' | head -n 1)"; raw_card="$(printf '%s\n' "$block" | sed -n 's/^Card: //p' | head -n 1)"; registry_status="$(printf '%s\n' "$block" | sed -n 's/^Status: //p' | head -n 1)"
  [ -n "$path" ] && [ -n "$raw_card" ] && is_absolute "$path" && [ -d "$path" ] && [ ! -L "$path" ] && [ -d "$path/ai" ] && [ ! -L "$path/ai" ] || die "registry entry incomplete or unsafe: $id"
  path="$(physical_dir "$path")"; inside "$path" "$HUB/projects" || die "registry project path outside allowed root: $id"; card="$(resolve_card "$raw_card")"
  [ -f "$card" ] && [ ! -L "$card" ] || die "missing or symlinked project card: $id"
  current_file="$path/ai/current-task.md"; future_file="$path/ai/future-tasks.md"; paused_file="$path/ai/paused-tasks.md"
  for source in "$current_file" "$future_file" "$paused_file"; do [ -f "$source" ] && [ ! -L "$source" ] || die "missing or symlinked allowed task file: $id"; done
  name="$(read_field "$card" Name)"; [ -n "$name" ] || name=$id
  current="$(current_state "$current_file")"; title="$(current_title "$current_file")"; [ -n "$title" ] || title='Current task'; due="$(safe_due "$current_file")"; overview_current='—'
  current_column='' current_done=' '
  case "$current" in
    active) current_column=Active;; ready|in_progress) current_column=Ready;; waiting) current_column=Waiting;; blocked) current_column=Blocked;; review) current_column=Review;; paused) current_column=Paused;; done|completed) current_column=Done; current_done=x;;
  esac
  if [ -n "$current_column" ]; then
    current_task_id="$(current_task_id "$current_file")"
    add_task "$current_task_id" "$current_column" "$title" "$name" "$id" "$due" "$current_done" "$current_file" "$(hash_file "$current_file")"
    overview_current="$title"
  fi
  while IFS=$'\t' read -r future_task_id future_status future_title future_due; do
    [ -n "$future_status" ] || continue
    case "$future_status" in idea) add_task "$future_task_id" Ideas "$future_title" "$name" "$id" "$future_due" ' ' "$future_file" "$(hash_file "$future_file")";; ready) add_task "$future_task_id" Ready "$future_title" "$name" "$id" "$future_due" ' ' "$future_file" "$(hash_file "$future_file")";; blocked) add_task "$future_task_id" Blocked "$future_title" "$name" "$id" "$future_due" ' ' "$future_file" "$(hash_file "$future_file")";; esac
  done < <(future_records "$future_file")
  paused_output="$(paused_records "$paused_file")"
  while IFS=$'\t' read -r paused_task_id paused_title; do [ -n "$paused_title" ] && add_task "$paused_task_id" Paused "$paused_title" "$name" "$id" '' ' ' "$paused_file" "$(hash_file "$paused_file")"; done <<< "$paused_output"
  ready_count="$(count_future_state "$future_file" ready)"; waiting_count=0; [ "$current" = waiting ] && waiting_count=1
  overview_due="$due"; [ -n "$overview_due" ] || overview_due="$(future_records "$future_file" | awk -F '\t' '$2 == "ready" && $4 != "" {print $4}' | sort | head -n 1)"; [ -n "$overview_due" ] || overview_due='—'
  OVERVIEW_ROWS+="| $(table_cell "$name") | $(table_cell "$registry_status") | $(table_cell "$overview_current") | $ready_count | $waiting_count | $overview_due |"$'\n'
  SOURCE_IDS+=("$id"); SOURCE_PATHS+=("$path"); SOURCE_CARDS+=("$card"); SOURCE_HASHES+=("$(hash_files "$card" "$current_file" "$future_file" "$paused_file")")
done

duplicate_task_ids="$(printf '%s\n' "${TASK_IDS[@]}" | sort | uniq -d)"
[ -z "$duplicate_task_ids" ] || die 'duplicate task ID in renderable tasks'
TASKS_RENDER="$( { printf '%s\n' '---' 'kanban-plugin: board' '---'; for column in Ideas Ready Active Waiting Blocked Review Paused Done; do printf '\n## %s\n' "$column"; for i in "${!TASK_COLUMNS[@]}"; do [ "${TASK_COLUMNS[$i]}" = "$column" ] || continue; printf '\n- [%s] %s ^%s\n' "${TASK_DONE[$i]}" "${TASK_TITLES[$i]}" "${TASK_IDS[$i]}"; printf '  - project: %s\n' "${TASK_PROJECTS[$i]}"; [ -z "${TASK_DUES[$i]}" ] || printf '  - 📅 %s\n' "${TASK_DUES[$i]}"; done; done; } )"
OVERVIEW_RENDER="$( { printf '%s\n' '# Projects Overview' '' '| Project | Status | Current task | Ready | Waiting | Due |' '| --- | --- | --- | ---: | ---: | --- |'; printf '%s' "$OVERVIEW_ROWS"; } )"
TASKS_HASH="$(hash_text "$TASKS_RENDER")"; OVERVIEW_HASH="$(hash_text "$OVERVIEW_RENDER")"; GENERATED_AT="${SOURCE_DATE_EPOCH:-$(date -u +%s)}"
TASK_ENTRIES="$( { comma=''; for i in "${!TASK_IDS[@]}"; do printf '%s    {"task_id": ' "$comma"; json_string "${TASK_IDS[$i]}"; printf ', "project_id": '; json_string "${TASK_PROJECT_IDS[$i]}"; printf ', "source_file": '; json_string "${TASK_SOURCE_FILES[$i]}"; printf ', "source_sha256": '; json_string "${TASK_SOURCE_HASHES[$i]}"; printf '}'; comma=$',\n'; done; } )"
MANIFEST_RENDER="$( { printf '{\n  "format_version": 3,\n  "generated_at": '; json_string "$GENERATED_AT"; printf ',\n  "views": {\n    "tasks_kanban": {"target": "Obsidian/Tasks-Kanban.md", "sha256": '; json_string "$TASKS_HASH"; printf '},\n    "projects_overview": {"target": "Obsidian/Projects-Overview.md", "sha256": '; json_string "$OVERVIEW_HASH"; printf '}\n  },\n  "tasks": [\n%s\n  ],\n  "sources": [\n' "$TASK_ENTRIES"; comma=''; for i in "${!SOURCE_IDS[@]}"; do printf '%s    {"id": ' "$comma"; json_string "${SOURCE_IDS[$i]}"; printf ', "registered_path": '; json_string "${SOURCE_PATHS[$i]}"; printf ', "card_path": '; json_string "${SOURCE_CARDS[$i]}"; printf ', "sha256": '; json_string "${SOURCE_HASHES[$i]}"; printf '}'; comma=$',\n'; done; printf '\n  ]\n}\n'; } )"

if [ "$MODE" = preview ]; then printf '%s\n--- projects overview ---\n%s\n--- manifest ---\n%s' "$TASKS_RENDER" "$OVERVIEW_RENDER" "$MANIFEST_RENDER"; exit 0; fi
TARGET_DIR="$VAULT/Obsidian"; TARGET_TASKS="$TARGET_DIR/Tasks-Kanban.md"; TARGET_OVERVIEW="$TARGET_DIR/Projects-Overview.md"; TARGET_MANIFEST="$TARGET_DIR/AI-Architecture.manifest.json"
[ -d "$TARGET_DIR" ] && [ ! -L "$TARGET_DIR" ] || die 'target directory missing or symlinked'; [ ! -L "$TARGET_TASKS" ] && [ ! -L "$TARGET_OVERVIEW" ] && [ ! -L "$TARGET_MANIFEST" ] || die 'generated targets must not be symlinks'
if [ -e "$TARGET_TASKS" ] || [ -e "$TARGET_OVERVIEW" ] || [ -e "$TARGET_MANIFEST" ]; then
  [ -f "$TARGET_TASKS" ] && [ -f "$TARGET_OVERVIEW" ] && [ -f "$TARGET_MANIFEST" ] || die 'proposal pending: generated view set is incomplete'
  manifest_format="$(sed -n 's/^  "format_version": \([0-9][0-9]*\),$/\1/p' "$TARGET_MANIFEST")"
  [ "$manifest_format" = 3 ] || { [ "$manifest_format" = 2 ] && die 'proposal pending: manifest v2 requires a fresh confirmed rebuild'; die 'proposal pending: generated manifest is invalid'; }
  recorded_tasks="$(sed -n 's/^    "tasks_kanban": {"target": "Obsidian\/Tasks-Kanban.md", "sha256": "\([0-9a-f]*\)"},$/\1/p' "$TARGET_MANIFEST")"; recorded_overview="$(sed -n 's/^    "projects_overview": {"target": "Obsidian\/Projects-Overview.md", "sha256": "\([0-9a-f]*\)"}$/\1/p' "$TARGET_MANIFEST")"
  [ -n "$recorded_tasks" ] && [ -n "$recorded_overview" ] || die 'proposal pending: generated manifest is invalid'
  [ "$REPLACE_CONFIRMED_BOARD" -eq 1 ] || [ "$recorded_tasks" = "$(shasum -a 256 "$TARGET_TASKS" | awk '{print $1}')" ] || die 'proposal pending: manual task board edit detected'
  [ "$recorded_overview" = "$(shasum -a 256 "$TARGET_OVERVIEW" | awk '{print $1}')" ] || die 'proposal pending: manual project overview edit detected'
fi
tmp_tasks="$(mktemp "$TARGET_DIR/.Tasks-Kanban.md.XXXXXX")"; tmp_overview="$(mktemp "$TARGET_DIR/.Projects-Overview.md.XXXXXX")"; tmp_manifest="$(mktemp "$TARGET_DIR/.AI-Architecture.manifest.json.XXXXXX")"; trap 'rm -f "$tmp_tasks" "$tmp_overview" "$tmp_manifest"' EXIT
printf '%s' "$TASKS_RENDER" > "$tmp_tasks"; printf '%s' "$OVERVIEW_RENDER" > "$tmp_overview"; printf '%s' "$MANIFEST_RENDER" > "$tmp_manifest"
[ "$(shasum -a 256 "$tmp_tasks" | awk '{print $1}')" = "$TASKS_HASH" ] || die 'temporary task board hash validation failed'; [ "$(shasum -a 256 "$tmp_overview" | awk '{print $1}')" = "$OVERVIEW_HASH" ] || die 'temporary project overview hash validation failed'
mv -f "$tmp_tasks" "$TARGET_TASKS"; mv -f "$tmp_overview" "$TARGET_OVERVIEW"; mv -f "$tmp_manifest" "$TARGET_MANIFEST"; trap - EXIT
printf 'wrote %s, %s, and %s\n' "$TARGET_TASKS" "$TARGET_OVERVIEW" "$TARGET_MANIFEST"
