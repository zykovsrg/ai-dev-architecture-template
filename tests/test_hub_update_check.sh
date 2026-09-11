#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TEMP_DIR="$(mktemp -d "$ROOT/.test-hub-update.XXXXXX")"
cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

HUB="$TEMP_DIR/_ai-hub"
mkdir -p "$HUB"
bash "$ROOT/scripts/install.sh" --mode hub "$HUB" >/dev/null
printf '\n<!-- local drift -->\n' >> "$HUB/AGENTS.md"

if bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB" --source "$ROOT" --check >"$TEMP_DIR/result" 2>&1; then
  echo "FAIL: --check accepted changed managed file" >&2
  exit 1
fi
grep -Fq 'Managed files differ' "$TEMP_DIR/result"
grep -Fq 'AGENTS.md' "$TEMP_DIR/result"

grep -Fq 'hub_release.py' "$ROOT/scripts/update-installed-hub.sh" || {
  echo 'FAIL: updater does not use hub_release.py' >&2
  exit 1
}
grep -Fq 'ls-remote' "$ROOT/scripts/update-installed-hub.sh" || {
  echo 'FAIL: remote symbolic ref is not pinned to a commit SHA' >&2
  exit 1
}
grep -Fq 'RESOLVED_SHA' "$ROOT/scripts/update-installed-hub.sh" || {
  echo 'FAIL: updater does not retain one resolved revision' >&2
  exit 1
}

# A reviewed remote preview must remain pinned even if the branch moves before apply.
REMOTE="$TEMP_DIR/remote.git"
WORK="$TEMP_DIR/work"
mkdir -p "$WORK"
git -C "$ROOT" archive HEAD | tar -x -C "$WORK"
git -C "$WORK" init -q
git -C "$WORK" config user.name test
git -C "$WORK" config user.email test@example.com
git -C "$WORK" add -A
git -C "$WORK" commit -q -m 'fixture: source A'
git init -q --bare "$REMOTE"
git -C "$WORK" remote add fixture "$REMOTE"
git -C "$WORK" push -q fixture HEAD:refs/heads/moving-source
SHA_A="$(git -C "$WORK" rev-parse HEAD)"

PIN_HUB="$TEMP_DIR/pin-hub"
mkdir -p "$PIN_HUB"
bash "$ROOT/scripts/install.sh" --mode hub "$PIN_HUB" >/dev/null
PREVIEW="$(HUB_RELEASE_REPO_URL="$REMOTE" bash "$ROOT/scripts/update-installed-hub.sh" --hub "$PIN_HUB" --ref moving-source --dry-run)"
PLAN_SHA="$(printf '%s\n' "$PREVIEW" | awk '/Plan SHA256:/ {print $3; exit}')"
PREVIEW_SHA="$(printf '%s\n' "$PREVIEW" | awk '/Resolved revision:/ {print $3; exit}')"
[ "$PREVIEW_SHA" = "$SHA_A" ] || { echo 'FAIL: preview did not pin SHA A' >&2; exit 1; }
[ -n "$PLAN_SHA" ] || { echo 'FAIL: preview did not emit plan hash' >&2; exit 1; }

printf '\n<!-- branch moved to B -->\n' >> "$WORK/hub-template/AGENTS.md"
git -C "$WORK" add hub-template/AGENTS.md
git -C "$WORK" commit -q -m 'fixture: move source branch'
SHA_B="$(git -C "$WORK" rev-parse HEAD)"
git -C "$WORK" push -q fixture HEAD:refs/heads/moving-source
[ "$SHA_A" != "$SHA_B" ] || { echo 'FAIL: fixture branch did not move' >&2; exit 1; }

# The fixture hub lives under ROOT, so it intentionally appears inside the
# repository worktree. --allow-dirty bypasses only that unrelated test-harness
# condition; source-SHA enforcement is still exercised by the updater itself.
HUB_RELEASE_REPO_URL="$REMOTE" bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$PIN_HUB" --ref moving-source --apply --allow-dirty \
  --confirm-plan "$PLAN_SHA" --confirm-source-sha "$SHA_A" >/dev/null

if grep -Fq 'branch moved to B' "$PIN_HUB/AGENTS.md"; then
  echo 'FAIL: apply silently used moved branch SHA B' >&2
  exit 1
fi
