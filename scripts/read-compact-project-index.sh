#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${1:-.}"
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TAB="$(printf '\t')"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

[ -f "$ROOT/scripts/check-hub-registry.sh" ] || die "missing registry validator: $ROOT/scripts/check-hub-registry.sh"

bash "$ROOT/scripts/check-hub-registry.sh" "$HUB_DIR" >/dev/null

printf 'project_id\tname\ttags\tstatus\tpurpose_brief\n'
awk -v hub_dir="$HUB_DIR" '
function trim(text) {
  sub(/^ +/, "", text)
  sub(/ +$/, "", text)
  return text
}

function reset_fields() {
  delete fields
}

function emit_row(   card_path, line, name, tags, status, purpose) {
  if (project_id == "") {
    return
  }

  name = fields["Name"]
  if (name == "") name = "unknown"
  tags = fields["Tags"]
  if (tags == "") tags = "unknown"
  status = fields["Status"]
  if (status == "") status = "unknown"

  card_path = hub_dir "/ai/project-cards/" project_id ".md"
  purpose = "unknown"
  while ((getline line < card_path) > 0) {
    if (line ~ /^Purpose: /) {
      purpose = substr(line, 10)
      break
    }
  }
  close(card_path)

  printf "%s\t%s\t%s\t%s\t%s\n", project_id, name, tags, status, purpose
}

/^## / {
  emit_row()
  project_id = trim(substr($0, 4))
  reset_fields()
  next
}

project_id != "" {
  if ($0 ~ /^Name: /) {
    fields["Name"] = substr($0, 7)
    next
  }
  if ($0 ~ /^Tags: /) {
    fields["Tags"] = substr($0, 7)
    next
  }
  if ($0 ~ /^Status: /) {
    fields["Status"] = substr($0, 9)
    next
  }
}

END {
  emit_row()
}
' "$HUB_DIR/ai/project-registry.md" | LC_ALL=C sort -t "$TAB" -k1,1
