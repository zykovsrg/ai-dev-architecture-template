#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALLER="$ROOT/scripts/install-legacy-hub-obsidian-bridge.sh"
TMP_DIR="$(mktemp -d /private/tmp/legacy-obsidian-bridge.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_contains() { grep -Fq -- "$2" "$1" || fail "expected '$2' in $1"; }
assert_not_contains() { ! grep -Fq -- "$2" "$1" || fail "unexpected '$2' in $1"; }

HUB="$TMP_DIR/hub"
PROJECTS="$HUB/projects"
LEGACY="$PROJECTS/legacy-project"
MODERN="$PROJECTS/modern-project"
BROKEN="$PROJECTS/broken-project"
mkdir -p "$HUB/ai/tmp" "$PROJECTS"
git -C "$HUB" init -q
printf '%s\n' '# Project Registry' > "$HUB/ai/project-registry.md"
printf '%s\n' 'legacy-project' > "$HUB/ai/tmp/obsidian-scope.txt"

add_project() {
  local id="$1" version="$2" project
  project="$PROJECTS/$id"
  mkdir -p "$project/ai"
  printf 'Version: %s\n' "$version" > "$project/ai/architecture.md"
  cat >> "$HUB/ai/project-registry.md" <<EOF

## $id
Path: $project
EOF
}

add_project legacy-project 7.3
add_project modern-project 7.4
add_project broken-project 7.3

printf '%s\n' '# Entry point' > "$LEGACY/AGENTS.md"
cp "$LEGACY/AGENTS.md" "$LEGACY/CLAUDE.md"
printf '%s\n' '# Modern entry point' > "$MODERN/AGENTS.md"
cp "$MODERN/AGENTS.md" "$MODERN/CLAUDE.md"
printf '%s\n' '# Broken agents entry point' > "$BROKEN/AGENTS.md"
printf '%s\n' '# Broken claude entry point' > "$BROKEN/CLAUDE.md"

"$INSTALLER" --hub "$HUB" --dry-run > "$TMP_DIR/dry-run.out"
assert_contains "$TMP_DIR/dry-run.out" 'legacy-project'
assert_not_contains "$TMP_DIR/dry-run.out" 'modern-project'
assert_not_contains "$TMP_DIR/dry-run.out" 'broken-project'

"$INSTALLER" --hub "$HUB" --apply > "$TMP_DIR/apply.out"
assert_contains "$LEGACY/AGENTS.md" '## Hub Obsidian Bridge'
cmp "$LEGACY/AGENTS.md" "$LEGACY/CLAUDE.md"
assert_not_contains "$MODERN/AGENTS.md" '## Hub Obsidian Bridge'
assert_not_contains "$BROKEN/AGENTS.md" '## Hub Obsidian Bridge'

echo 'PASS: legacy hub Obsidian bridge contract'
