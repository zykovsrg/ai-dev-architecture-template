#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALLER="$ROOT/scripts/install-legacy-hub-obsidian-bridge.sh"
TMP_DIR="$(mktemp -d /private/tmp/legacy-obsidian-bridge.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_contains() { grep -Fq -- "$2" "$1" || fail "expected '$2' in $1"; }
assert_not_contains() { ! grep -Fq -- "$2" "$1" || fail "unexpected '$2' in $1"; }
assert_equals() { [ "$1" = "$2" ] || fail "expected '$1' to equal '$2'"; }
assert_matching_entries() { cmp -s <(sed '1d' "$1") <(sed '1d' "$2") || fail "entry bodies differ: $1 $2"; }

HUB="$TMP_DIR/hub"
PROJECTS="$HUB/projects"
LEGACY="$PROJECTS/legacy-project"
MODERN="$PROJECTS/modern-project"
BROKEN="$PROJECTS/broken-project"
UNREGISTERED="$PROJECTS/unregistered-project"
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

cat > "$LEGACY/AGENTS.md" <<'EOF'
# Entry point — Codex

## Installation Mode

Standalone mode.

## Core Principles

Keep this content.
EOF
sed '1s/Codex/Claude Code/' "$LEGACY/AGENTS.md" > "$LEGACY/CLAUDE.md"
printf '%s\n' '# Modern entry point' '## Installation Mode' > "$MODERN/AGENTS.md"
cp "$MODERN/AGENTS.md" "$MODERN/CLAUDE.md"
printf '%s\n' '# Broken entry point' '## Installation Mode' 'Agents-only rule.' > "$BROKEN/AGENTS.md"
printf '%s\n' '# Broken entry point' '## Installation Mode' 'Claude-only rule.' > "$BROKEN/CLAUDE.md"
mkdir -p "$UNREGISTERED/ai"
printf '%s\n' 'Version: 7.3' > "$UNREGISTERED/ai/architecture.md"
printf '%s\n' '# Unregistered' '## Installation Mode' > "$UNREGISTERED/AGENTS.md"
cp "$UNREGISTERED/AGENTS.md" "$UNREGISTERED/CLAUDE.md"

LEGACY_BEFORE="$(cksum "$LEGACY/AGENTS.md")"
BROKEN_AGENTS_BEFORE="$(cksum "$BROKEN/AGENTS.md")"
BROKEN_CLAUDE_BEFORE="$(cksum "$BROKEN/CLAUDE.md")"

"$INSTALLER" --hub "$HUB" --dry-run > "$TMP_DIR/dry-run.out"
assert_contains "$TMP_DIR/dry-run.out" 'legacy-project'
assert_contains "$TMP_DIR/dry-run.out" 'AGENTS.md'
assert_contains "$TMP_DIR/dry-run.out" 'CLAUDE.md'
assert_not_contains "$TMP_DIR/dry-run.out" 'modern-project'
assert_not_contains "$TMP_DIR/dry-run.out" 'broken-project'
assert_not_contains "$TMP_DIR/dry-run.out" 'unregistered-project'
assert_equals "$LEGACY_BEFORE" "$(cksum "$LEGACY/AGENTS.md")"

"$INSTALLER" --hub "$HUB" --apply > "$TMP_DIR/apply.out"
assert_contains "$LEGACY/AGENTS.md" '## Hub Obsidian Bridge'
assert_contains "$LEGACY/AGENTS.md" 'obsidian-task-sync.sh scan --project-id <project-id>'
assert_contains "$LEGACY/AGENTS.md" 'never guess a vault path.'
assert_matching_entries "$LEGACY/AGENTS.md" "$LEGACY/CLAUDE.md"
assert_not_contains "$MODERN/AGENTS.md" '## Hub Obsidian Bridge'
assert_not_contains "$BROKEN/AGENTS.md" '## Hub Obsidian Bridge'
assert_not_contains "$UNREGISTERED/AGENTS.md" '## Hub Obsidian Bridge'
assert_equals "$BROKEN_AGENTS_BEFORE" "$(cksum "$BROKEN/AGENTS.md")"
assert_equals "$BROKEN_CLAUDE_BEFORE" "$(cksum "$BROKEN/CLAUDE.md")"

BRIDGE_COUNT="$(grep -Fc '## Hub Obsidian Bridge' "$LEGACY/AGENTS.md")"
"$INSTALLER" --hub "$HUB" --apply > "$TMP_DIR/reapply.out"
assert_equals "$BRIDGE_COUNT" "$(grep -Fc '## Hub Obsidian Bridge' "$LEGACY/AGENTS.md")"
assert_not_contains "$TMP_DIR/reapply.out" 'legacy-project'

echo 'PASS: legacy hub Obsidian bridge contract'
