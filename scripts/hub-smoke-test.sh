#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-hub-smoke.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_contains() { grep -Fq "$2" "$1" || fail "expected '$2' in $1"; }

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
