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

[ -f "$HUB_DIR/ai/project-registry.md" ] || die "missing project registry"

rows="$(awk -v hub_dir="$HUB_DIR" -v tab="$TAB" -v cr="$CR" '
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

function emit_row(   card_path, line, purpose, purpose_count) {
  if (project_id == "") return
  if (project_id !~ /^[a-z0-9]+(-[a-z0-9]+)*$/) die("invalid project ID in compact index: " project_id)
  if (seen[project_id]++) die("duplicate project ID in compact index: " project_id)
  if (name_count != 1 || name == "") die("missing or duplicate Name in compact index: " project_id)
  if (tags_count != 1 || tags == "") die("missing or duplicate Tags in compact index: " project_id)
  if (status_count != 1 || !status_ok(status)) die("invalid Status in compact index: " project_id)

  card_path = hub_dir "/ai/project-cards/" project_id ".md"
  purpose = ""
  purpose_count = 0
  while ((getline line < card_path) > 0) {
    if (line ~ /^Purpose: /) {
      purpose_count++
      purpose = substr(line, 10)
    }
  }
  close(card_path)
  if (purpose_count != 1 || purpose == "") die("missing or duplicate Purpose in compact index: " project_id)

  reject_tsv_breakers("project_id", project_id)
  reject_tsv_breakers("name", name)
  reject_tsv_breakers("tags", tags)
  reject_tsv_breakers("status", status)
  reject_tsv_breakers("purpose_brief", purpose)

  print project_id "\t" name "\t" tags "\t" status "\t" purpose
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

printf 'project_id\tname\ttags\tstatus\tpurpose_brief\n'
if [ -n "$rows" ]; then
  printf '%s\n' "$rows" | LC_ALL=C sort -t "$TAB" -k1,1
fi
