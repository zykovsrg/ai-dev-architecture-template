#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${1:-.}"
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
TAB="$(printf '\t')"
CR="$(printf '\r')"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_safe_directory() {
  local rel="$1" path canonical_path
  path="$HUB_DIR/$rel"

  [ ! -L "$path" ] || die "symlink is not allowed: $rel"
  [ -d "$path" ] || die "missing directory: $rel"
  canonical_path="$(cd "$path" && pwd -P)"
  case "$canonical_path" in
    "$HUB_DIR"/*) ;;
    *) die "directory is outside canonical hub: $rel" ;;
  esac
}

require_safe_regular_file() {
  local rel="$1" path parent canonical_parent
  path="$HUB_DIR/$rel"

  [ ! -L "$path" ] || die "symlink is not allowed: $rel"
  [ -f "$path" ] || die "missing regular file: $rel"
  parent="$(dirname "$path")"
  canonical_parent="$(cd "$parent" && pwd -P)"
  case "$canonical_parent" in
    "$HUB_DIR"|"$HUB_DIR"/*) ;;
    *) die "regular file is outside canonical hub: $rel" ;;
  esac
}

require_safe_directory "ai"
require_safe_regular_file "ai/project-registry.md"
require_safe_directory "ai/project-cards"

registry_rows="$(awk -v tab="$TAB" -v cr="$CR" '
function die(message) {
  print "ERROR: " message > "/dev/stderr"
  exit 1
}

function trim(text) {
  sub(/^ +/, "", text)
  sub(/ +$/, "", text)
  return text
}

function reset_fields() {
  name = ""
  tags = ""
  status = ""
  name_count = 0
  tags_count = 0
  status_count = 0
}

function reject_tsv_breakers(label, value) {
  if (index(value, tab) > 0 || index(value, cr) > 0) {
    die("compact index field contains forbidden control character in " label)
  }
}

function status_ok(value) {
  return value == "active" || value == "paused" || value == "archived" || value == "missing" || value == "registration-pending"
}

function emit_row() {
  if (project_id == "") return
  if (project_id !~ /^[a-z0-9]+(-[a-z0-9]+)*$/) die("invalid project ID in compact index: " project_id)
  if (seen[project_id]++) die("duplicate project ID in compact index: " project_id)
  if (name_count != 1 || name == "") die("missing or duplicate Name in compact index: " project_id)
  if (tags_count != 1 || tags == "") die("missing or duplicate Tags in compact index: " project_id)
  if (status_count != 1 || !status_ok(status)) die("invalid Status in compact index: " project_id)

  reject_tsv_breakers("project_id", project_id)
  reject_tsv_breakers("name", name)
  reject_tsv_breakers("tags", tags)
  reject_tsv_breakers("status", status)

  print project_id "\t" name "\t" tags "\t" status
}

/^## / {
  emit_row()
  project_id = trim(substr($0, 4))
  reset_fields()
  next
}

project_id != "" {
  if ($0 ~ /^Name: /) {
    name_count++
    name = substr($0, 7)
    next
  }
  if ($0 ~ /^Tags: /) {
    tags_count++
    tags = substr($0, 7)
    next
  }
  if ($0 ~ /^Status: /) {
    status_count++
    status = substr($0, 9)
    next
  }
}

END {
  emit_row()
}
' "$HUB_DIR/ai/project-registry.md")" || exit 1

rows=""
if [ -n "$registry_rows" ]; then
  while IFS="$TAB" read -r project_id name tags status; do
    card_rel="ai/project-cards/$project_id.md"
    require_safe_regular_file "$card_rel"
    purpose="$(awk -v project_id="$project_id" -v tab="$TAB" -v cr="$CR" '
      function die(message) {
        print "ERROR: " message > "/dev/stderr"
        exit 1
      }

      /^Purpose: / {
        purpose_count++
        purpose = substr($0, 10)
      }

      END {
        if (purpose_count != 1 || purpose == "") die("missing or duplicate Purpose in compact index: " project_id)
        if (index(purpose, tab) > 0 || index(purpose, cr) > 0) die("compact index field contains forbidden control character in purpose_brief")
        print purpose
      }
    ' "$HUB_DIR/$card_rel")" || exit 1

    row="$project_id$TAB$name$TAB$tags$TAB$status$TAB$purpose"
    rows+="${rows:+$'\n'}$row"
  done <<< "$registry_rows"
fi

printf 'project_id\tname\ttags\tstatus\tpurpose_brief\n'
if [ -n "$rows" ]; then
  printf '%s\n' "$rows" | LC_ALL=C sort -t "$TAB" -k1,1
fi
