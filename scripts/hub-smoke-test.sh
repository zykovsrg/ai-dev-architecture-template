#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-hub-smoke.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_contains() { grep -Fq "$2" "$1" || fail "expected '$2' in $1"; }
assert_file() { [ -f "$1" ] || fail "missing file: $1"; }
normalize_entry() {
  sed \
    -e '1{/^# Personal AI Hub — Codex$/d;}' \
    -e '1{/^# Personal AI Hub — Claude Code$/d;}' \
    -e '/^<!-- Tool-specific activation: Codex reads AGENTS\.md as its project entry file\. -->$/d' \
    -e '/^<!-- Tool-specific activation: Claude Code reads CLAUDE\.md as its project entry file\. -->$/d' \
    "$1"
}

HUB_AGENTS="$ROOT/hub-template/AGENTS.md"
HUB_CLAUDE="$ROOT/hub-template/CLAUDE.md"
assert_file "$HUB_AGENTS"
assert_file "$HUB_CLAUDE"
[ "$(wc -l < "$HUB_AGENTS")" -le 120 ] || fail 'hub AGENTS.md too long'
[ "$(wc -c < "$HUB_AGENTS")" -le 6000 ] || fail 'hub AGENTS.md too large'
[ "$(wc -l < "$HUB_CLAUDE")" -le 120 ] || fail 'hub CLAUDE.md too long'
[ "$(wc -c < "$HUB_CLAUDE")" -le 6000 ] || fail 'hub CLAUDE.md too large'
grep -Fq 'explicit confirmation' "$HUB_AGENTS" || fail 'missing confirmation gate'
grep -Fq 'allowed roots' "$HUB_AGENTS" || fail 'missing allowed-root gate'
grep -Fq 'explicit confirmation' "$HUB_CLAUDE" || fail 'missing confirmation gate'
grep -Fq 'allowed roots' "$HUB_CLAUDE" || fail 'missing allowed-root gate'

THIRD_ACTIVATION="$TMP_DIR/entry-with-third-activation.md"
cp "$HUB_AGENTS" "$THIRD_ACTIVATION"
printf '%s\n' '<!-- Tool-specific activation: A third tool reads this entry differently. -->' >> "$THIRD_ACTIVATION"
assert_contains <(normalize_entry "$THIRD_ACTIVATION") \
  '<!-- Tool-specific activation: A third tool reads this entry differently. -->'

cmp -s <(normalize_entry "$HUB_AGENTS") <(normalize_entry "$HUB_CLAUDE") \
  || fail 'hub entry files differ beyond title and activation paragraph'

VALID="$TMP_DIR/valid-hub"
mkdir -p "$VALID/ai/project-cards" "$TMP_DIR/projects/analytics-seo"
printf '%s\n' '# Allowed Roots' '' "- $TMP_DIR/projects" > "$VALID/ai/allowed-roots.md"
printf '%s\n' '# Project Registry' '' \
  '## analytics-seo' \
  'Name: SEO Analytics' \
  'Type: work' \
  'Status: active' \
  "Path: $TMP_DIR/projects/analytics-seo" \
  'Tags: seo, analytics, traffic, leads' \
  'Card: ai/project-cards/analytics-seo.md' > "$VALID/ai/project-registry.md"
printf '%s\n' '# SEO Analytics' '' 'Project ID: analytics-seo' > "$VALID/ai/project-cards/analytics-seo.md"

bash "$ROOT/scripts/check-hub-registry.sh" "$VALID" > "$TMP_DIR/valid.out"
assert_contains "$TMP_DIR/valid.out" 'Registry check passed'

INVALID="$TMP_DIR/invalid-hub"
cp -R "$VALID" "$INVALID"
sed "s#Path: $TMP_DIR/projects/analytics-seo#Path: $TMP_DIR/outside#" \
  "$VALID/ai/project-registry.md" > "$INVALID/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$INVALID" > "$TMP_DIR/invalid.out" 2>&1; then
  fail 'validator accepted project outside allowed roots'
fi
assert_contains "$TMP_DIR/invalid.out" 'outside allowed roots'

MISSING_ROOT="$TMP_DIR/missing-root-hub"
cp -R "$VALID" "$MISSING_ROOT"
printf '%s\n' '# Allowed Roots' '' "- $TMP_DIR/does-not-exist" > "$MISSING_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$MISSING_ROOT" > "$TMP_DIR/missing-root.out" 2>&1; then
  fail 'validator accepted a nonexistent allowed root'
fi
assert_contains "$TMP_DIR/missing-root.out" 'allowed root does not exist'

RELATIVE_ROOT="$TMP_DIR/relative-root-hub"
cp -R "$VALID" "$RELATIVE_ROOT"
printf '%s\n' '# Allowed Roots' '' '- relative/projects' > "$RELATIVE_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$RELATIVE_ROOT" > "$TMP_DIR/relative-root.out" 2>&1; then
  fail 'validator accepted a relative allowed root'
fi
assert_contains "$TMP_DIR/relative-root.out" 'allowed root must be a nonempty absolute path'

EMPTY_ROOT="$TMP_DIR/empty-root-hub"
cp -R "$VALID" "$EMPTY_ROOT"
printf '%s\n' '# Allowed Roots' '' '- ' > "$EMPTY_ROOT/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$EMPTY_ROOT" > "$TMP_DIR/empty-root.out" 2>&1; then
  fail 'validator accepted an empty allowed root'
fi
assert_contains "$TMP_DIR/empty-root.out" 'allowed root must be a nonempty absolute path'

ROOT_FILESYSTEM="$TMP_DIR/root-filesystem-hub"
cp -R "$VALID" "$ROOT_FILESYSTEM"
printf '%s\n' '# Allowed Roots' '' '- /' > "$ROOT_FILESYSTEM/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ROOT_FILESYSTEM" > "$TMP_DIR/root-filesystem.out" 2>&1; then
  fail 'validator accepted filesystem root as an allowed root'
fi
assert_contains "$TMP_DIR/root-filesystem.out" 'ERROR: allowed root must not be /'

ROOT_DOUBLE_SLASH="$TMP_DIR/root-double-slash-hub"
cp -R "$VALID" "$ROOT_DOUBLE_SLASH"
printf '%s\n' '# Allowed Roots' '' '- //' > "$ROOT_DOUBLE_SLASH/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ROOT_DOUBLE_SLASH" > "$TMP_DIR/root-double-slash.out" 2>&1; then
  fail 'validator accepted // as an allowed root'
fi
assert_contains "$TMP_DIR/root-double-slash.out" 'allowed root must not be /'

ROOT_SYMLINK_FILESYSTEM="$TMP_DIR/root-symlink-filesystem-hub"
ln -s / "$TMP_DIR/filesystem-root-link"
cp -R "$VALID" "$ROOT_SYMLINK_FILESYSTEM"
printf '%s\n' '# Allowed Roots' '' "- $TMP_DIR/filesystem-root-link" > "$ROOT_SYMLINK_FILESYSTEM/ai/allowed-roots.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$ROOT_SYMLINK_FILESYSTEM" > "$TMP_DIR/root-symlink-filesystem.out" 2>&1; then
  fail 'validator accepted a symlink resolving to filesystem root'
fi
assert_contains "$TMP_DIR/root-symlink-filesystem.out" 'allowed root must not be /'

LEXICAL_ESCAPE="$TMP_DIR/lexical-escape-hub"
cp -R "$VALID" "$LEXICAL_ESCAPE"
sed "s#Path: $TMP_DIR/projects/analytics-seo#Path: $TMP_DIR/projects/../outside/missing#" \
  "$VALID/ai/project-registry.md" > "$LEXICAL_ESCAPE/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$LEXICAL_ESCAPE" > "$TMP_DIR/lexical-escape.out" 2>&1; then
  fail 'validator accepted a lexical path escape'
fi
assert_contains "$TMP_DIR/lexical-escape.out" 'outside allowed roots'

SYMLINK_ESCAPE="$TMP_DIR/symlink-escape-hub"
mkdir -p "$TMP_DIR/outside"
ln -s "$TMP_DIR/outside" "$TMP_DIR/projects/link-out"
cp -R "$VALID" "$SYMLINK_ESCAPE"
sed "s#Path: $TMP_DIR/projects/analytics-seo#Path: $TMP_DIR/projects/link-out/missing#" \
  "$VALID/ai/project-registry.md" > "$SYMLINK_ESCAPE/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$SYMLINK_ESCAPE" > "$TMP_DIR/symlink-escape.out" 2>&1; then
  fail 'validator accepted a symlink component escape'
fi
assert_contains "$TMP_DIR/symlink-escape.out" 'outside allowed roots'

MISSING_PROJECT="$TMP_DIR/missing-project-hub"
cp -R "$VALID" "$MISSING_PROJECT"
sed -e 's/Status: active/Status: missing/' \
  -e "s#Path: $TMP_DIR/projects/analytics-seo#Path: $TMP_DIR/projects/genuinely-missing#" \
  "$VALID/ai/project-registry.md" > "$MISSING_PROJECT/ai/project-registry.md"
bash "$ROOT/scripts/check-hub-registry.sh" "$MISSING_PROJECT" > "$TMP_DIR/missing-project.out"
assert_contains "$TMP_DIR/missing-project.out" 'Registry check passed'
