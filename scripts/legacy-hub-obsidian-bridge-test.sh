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
assert_matching_entries() {
  cmp -s \
    <(sed '1d' "$1" | sed 's/point for Codex; `CLAUDE\.md` is the matching Claude Code entry file\./point for <tool>; `<matching-entry-file>` is the matching <matching-tool> entry file./' | sed 's/point for Claude Code; `AGENTS\.md` is the matching Codex entry file\./point for <tool>; `<matching-entry-file>` is the matching <matching-tool> entry file./') \
    <(sed '1d' "$2" | sed 's/point for Codex; `CLAUDE\.md` is the matching Claude Code entry file\./point for <tool>; `<matching-entry-file>` is the matching <matching-tool> entry file./' | sed 's/point for Claude Code; `AGENTS\.md` is the matching Codex entry file\./point for <tool>; `<matching-entry-file>` is the matching <matching-tool> entry file./') \
    || fail "entry bodies differ: $1 $2"
}

HUB="$TMP_DIR/hub"
PROJECTS="$HUB/projects"
LEGACY="$PROJECTS/legacy-project"
RECIPROCAL="$PROJECTS/reciprocal-entry-project"
MODERN="$PROJECTS/modern-project"
BROKEN="$PROJECTS/broken-project"
UNREGISTERED="$PROJECTS/unregistered-project"
OUT_OF_SCOPE="$PROJECTS/out-of-scope-project"
INVALID_HEADER="$PROJECTS/invalid-header-project"
MALFORMED="$PROJECTS/malformed-bridge-project"
DUPLICATE="$PROJECTS/duplicate-bridge-project"
ATOMIC="$PROJECTS/atomic-project"
OUTSIDE="$HUB/outside-project"
SYMLINK="$PROJECTS/symlink-project"
mkdir -p "$HUB/ai/tmp" "$PROJECTS"
git -C "$HUB" init -q
printf '%s\n' '# Project Registry' > "$HUB/ai/project-registry.md"
printf '%s\n' \
  'legacy-project' \
  'reciprocal-entry-project' \
  'broken-project' \
  'invalid-header-project' \
  'malformed-bridge-project' \
  'duplicate-bridge-project' \
  'symlink-project' > "$HUB/ai/tmp/obsidian-scope.txt"

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
add_project reciprocal-entry-project 7.3
add_project modern-project 7.4
add_project broken-project 7.3
add_project out-of-scope-project 7.3
add_project invalid-header-project 7.3
add_project malformed-bridge-project 7.3
add_project duplicate-bridge-project 7.3
add_project atomic-project 7.3

mkdir -p "$OUTSIDE/ai"
printf '%s\n' 'Version: 7.3' > "$OUTSIDE/ai/architecture.md"
cat >> "$HUB/ai/project-registry.md" <<EOF

## ../outside-project
Path: $OUTSIDE
EOF
ln -s "$OUTSIDE" "$SYMLINK"
cat >> "$HUB/ai/project-registry.md" <<EOF

## symlink-project
Path: $SYMLINK
EOF

cat > "$LEGACY/AGENTS.md" <<'EOF'
# AI Development Entry Point — Codex

## Installation Mode

Standalone mode.

## Core Principles

Keep this content.
EOF
sed '1s/Codex/Claude Code/' "$LEGACY/AGENTS.md" > "$LEGACY/CLAUDE.md"
cp "$LEGACY/AGENTS.md" "$RECIPROCAL/AGENTS.md"
sed '1s/Codex/Claude Code/' "$RECIPROCAL/AGENTS.md" > "$RECIPROCAL/CLAUDE.md"
cat >> "$RECIPROCAL/AGENTS.md" <<'EOF'

point for Codex; `CLAUDE.md` is the matching Claude Code entry file.
EOF
cat >> "$RECIPROCAL/CLAUDE.md" <<'EOF'

point for Claude Code; `AGENTS.md` is the matching Codex entry file.
EOF
sed '1s/legacy-project/modern-project/' "$LEGACY/AGENTS.md" > "$MODERN/AGENTS.md"
sed '1s/Codex/Claude Code/' "$MODERN/AGENTS.md" > "$MODERN/CLAUDE.md"
printf '%s\n' '# AI Development Entry Point — Codex' '## Installation Mode' 'Agents-only rule.' > "$BROKEN/AGENTS.md"
printf '%s\n' '# AI Development Entry Point — Claude Code' '## Installation Mode' 'Claude-only rule.' > "$BROKEN/CLAUDE.md"
cp "$LEGACY/AGENTS.md" "$OUT_OF_SCOPE/AGENTS.md"
sed '1s/Codex/Claude Code/' "$OUT_OF_SCOPE/AGENTS.md" > "$OUT_OF_SCOPE/CLAUDE.md"
sed '1s/Codex/Not Codex/' "$LEGACY/AGENTS.md" > "$INVALID_HEADER/AGENTS.md"
sed '1s/Codex/Not Claude/' "$LEGACY/CLAUDE.md" > "$INVALID_HEADER/CLAUDE.md"
cp "$LEGACY/AGENTS.md" "$MALFORMED/AGENTS.md"
sed '1s/Codex/Claude Code/' "$MALFORMED/AGENTS.md" > "$MALFORMED/CLAUDE.md"
printf '%s\n' '' '## Hub Obsidian Bridge' '' 'Partial bridge text.' >> "$MALFORMED/AGENTS.md"
printf '%s\n' '' '## Hub Obsidian Bridge' '' 'Partial bridge text.' >> "$MALFORMED/CLAUDE.md"
cp "$MALFORMED/AGENTS.md" "$DUPLICATE/AGENTS.md"
sed '1s/Codex/Claude Code/' "$DUPLICATE/AGENTS.md" > "$DUPLICATE/CLAUDE.md"
printf '%s\n' '## Hub Obsidian Bridge' 'Another partial bridge.' >> "$DUPLICATE/AGENTS.md"
printf '%s\n' '## Hub Obsidian Bridge' 'Another partial bridge.' >> "$DUPLICATE/CLAUDE.md"
cp "$LEGACY/AGENTS.md" "$ATOMIC/AGENTS.md"
sed '1s/Codex/Claude Code/' "$ATOMIC/AGENTS.md" > "$ATOMIC/CLAUDE.md"
cp "$LEGACY/AGENTS.md" "$OUTSIDE/AGENTS.md"
sed '1s/Codex/Claude Code/' "$OUTSIDE/AGENTS.md" > "$OUTSIDE/CLAUDE.md"
mkdir -p "$UNREGISTERED/ai"
printf '%s\n' 'Version: 7.3' > "$UNREGISTERED/ai/architecture.md"
cp "$LEGACY/AGENTS.md" "$UNREGISTERED/AGENTS.md"
sed '1s/Codex/Claude Code/' "$UNREGISTERED/AGENTS.md" > "$UNREGISTERED/CLAUDE.md"

LEGACY_BEFORE="$(cksum "$LEGACY/AGENTS.md")"
BROKEN_AGENTS_BEFORE="$(cksum "$BROKEN/AGENTS.md")"
BROKEN_CLAUDE_BEFORE="$(cksum "$BROKEN/CLAUDE.md")"

if ! "$INSTALLER" --hub "$HUB" --dry-run > "$TMP_DIR/dry-run.out" 2> "$TMP_DIR/dry-run.err"; then
  cat "$TMP_DIR/dry-run.err" >&2
  fail 'dry-run should complete while skipping invalid projects'
fi
if ! grep -Fq 'legacy-project' "$TMP_DIR/dry-run.out"; then
  cat "$TMP_DIR/dry-run.out" >&2
  cat "$TMP_DIR/dry-run.err" >&2
  fail 'expected legacy-project in dry-run output'
fi
# This fixture reproduces the legacy reciprocal sentence that the old
# normalizer skipped; the exact-pair normalization must now select it.
assert_contains "$TMP_DIR/dry-run.out" 'reciprocal-entry-project'
assert_contains "$TMP_DIR/dry-run.out" 'AGENTS.md'
assert_contains "$TMP_DIR/dry-run.out" 'CLAUDE.md'
assert_not_contains "$TMP_DIR/dry-run.out" 'modern-project'
assert_not_contains "$TMP_DIR/dry-run.out" 'broken-project'
assert_not_contains "$TMP_DIR/dry-run.out" 'unregistered-project'
assert_not_contains "$TMP_DIR/dry-run.out" 'out-of-scope-project'
assert_not_contains "$TMP_DIR/dry-run.out" 'outside-project: '
assert_not_contains "$TMP_DIR/dry-run.out" 'symlink-project: '
assert_contains "$TMP_DIR/dry-run.err" 'invalid registry project ID: ../outside-project'
assert_contains "$TMP_DIR/dry-run.err" 'symlink-project is not a physical direct child'
assert_contains "$TMP_DIR/dry-run.err" 'invalid-header-project has invalid Codex/Claude headers'
assert_contains "$TMP_DIR/dry-run.err" 'malformed-bridge-project has an invalid bridge block'
assert_contains "$TMP_DIR/dry-run.err" 'duplicate-bridge-project has an invalid bridge block'
assert_equals "$LEGACY_BEFORE" "$(cksum "$LEGACY/AGENTS.md")"

"$INSTALLER" --hub "$HUB" --apply > "$TMP_DIR/apply.out" 2>&1
assert_contains "$LEGACY/AGENTS.md" '## Hub Obsidian Bridge'
assert_contains "$LEGACY/AGENTS.md" 'obsidian-task-sync.sh scan --project-id <project-id>'
assert_contains "$LEGACY/AGENTS.md" 'never guess a vault path.'
assert_matching_entries "$LEGACY/AGENTS.md" "$LEGACY/CLAUDE.md"
assert_contains "$RECIPROCAL/AGENTS.md" '## Hub Obsidian Bridge'
assert_contains "$RECIPROCAL/CLAUDE.md" '## Hub Obsidian Bridge'
assert_matching_entries "$RECIPROCAL/AGENTS.md" "$RECIPROCAL/CLAUDE.md"
assert_not_contains "$MODERN/AGENTS.md" '## Hub Obsidian Bridge'
assert_not_contains "$BROKEN/AGENTS.md" '## Hub Obsidian Bridge'
assert_not_contains "$UNREGISTERED/AGENTS.md" '## Hub Obsidian Bridge'
assert_not_contains "$OUT_OF_SCOPE/AGENTS.md" '## Hub Obsidian Bridge'
assert_not_contains "$INVALID_HEADER/AGENTS.md" '## Hub Obsidian Bridge'
assert_not_contains "$MALFORMED/AGENTS.md" 'vault automatically.'
assert_not_contains "$DUPLICATE/AGENTS.md" 'vault automatically.'
assert_not_contains "$OUTSIDE/AGENTS.md" 'vault automatically.'
assert_not_contains "$SYMLINK/AGENTS.md" 'vault automatically.'
assert_equals "$BROKEN_AGENTS_BEFORE" "$(cksum "$BROKEN/AGENTS.md")"
assert_equals "$BROKEN_CLAUDE_BEFORE" "$(cksum "$BROKEN/CLAUDE.md")"

BRIDGE_COUNT="$(grep -Fc '## Hub Obsidian Bridge' "$LEGACY/AGENTS.md")"
"$INSTALLER" --hub "$HUB" --apply > "$TMP_DIR/reapply.out" 2>&1
assert_equals "$BRIDGE_COUNT" "$(grep -Fc '## Hub Obsidian Bridge' "$LEGACY/AGENTS.md")"
assert_not_contains "$TMP_DIR/reapply.out" 'legacy-project'

printf '%s\n' 'legacy-project' '../outside-project' > "$HUB/ai/tmp/obsidian-scope.txt"
if "$INSTALLER" --hub "$HUB" --dry-run > "$TMP_DIR/invalid-scope.out" 2>&1; then
  fail 'invalid scope project IDs must reject the run'
fi
assert_contains "$TMP_DIR/invalid-scope.out" 'invalid project ID in scope: ../outside-project'

printf '%s\n' 'atomic-project' > "$HUB/ai/tmp/obsidian-scope.txt"
ATOMIC_AGENTS_BEFORE="$(cksum "$ATOMIC/AGENTS.md")"
ATOMIC_CLAUDE_BEFORE="$(cksum "$ATOMIC/CLAUDE.md")"
mkdir -p "$TMP_DIR/test-bin"
cat > "$TMP_DIR/test-bin/mv" <<'EOF'
#!/usr/bin/env bash
if [ "${FAIL_MV_DESTINATION:-}" = "${2:-}" ]; then
  exit 1
fi
exec /bin/mv "$@"
EOF
chmod +x "$TMP_DIR/test-bin/mv"
if ! PATH="$TMP_DIR/test-bin:$PATH" FAIL_MV_DESTINATION="$ATOMIC/CLAUDE.md" "$INSTALLER" --hub "$HUB" --apply > "$TMP_DIR/atomic.out" 2>&1; then
  fail 'installer should roll back and continue when the second replacement fails'
fi
assert_contains "$TMP_DIR/atomic.out" 'atomic-project could not be updated atomically; original pair restored'
assert_equals "$ATOMIC_AGENTS_BEFORE" "$(cksum "$ATOMIC/AGENTS.md")"
assert_equals "$ATOMIC_CLAUDE_BEFORE" "$(cksum "$ATOMIC/CLAUDE.md")"

echo 'PASS: legacy hub Obsidian bridge contract'
