#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/zykovsrg/ai-dev-architecture-template.git"
REF="main"
MODE="dry-run"
HUB_DIR="$PWD"
SOURCE_DIR=""
CONFIRM_PLAN=""
DO_COMMIT=0
ALLOW_DIRTY=0
TMP_DIR=""
RESOLVED_SHA=""

usage() {
  cat <<'EOF'
Usage: update-installed-hub.sh [--check|--dry-run|--apply --confirm-plan SHA] [--hub DIR] [--source DIR | --ref REF] [--commit] [--allow-dirty]

Uses scripts/hub_release.py as the single preview/apply engine.
Remote refs are resolved once to one commit SHA and that exact revision is used for the whole invocation.
EOF
}
die() { echo "ERROR: $*" >&2; exit 1; }
cleanup() { [ -z "$TMP_DIR" ] || rm -rf "$TMP_DIR"; }
trap cleanup EXIT

while [ "$#" -gt 0 ]; do
  case "$1" in
    --check) MODE="check" ;;
    --dry-run) MODE="dry-run" ;;
    --apply) MODE="apply" ;;
    --commit) DO_COMMIT=1 ;;
    --allow-dirty) ALLOW_DIRTY=1 ;;
    --hub) shift; [ "$#" -gt 0 ] || die "--hub requires a directory"; HUB_DIR="$1" ;;
    --source) shift; [ "$#" -gt 0 ] || die "--source requires a directory"; SOURCE_DIR="$1" ;;
    --ref) shift; [ "$#" -gt 0 ] || die "--ref requires a ref"; REF="$1" ;;
    --confirm-plan) shift; [ "$#" -gt 0 ] || die "--confirm-plan requires a hash"; CONFIRM_PLAN="$1" ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

[ -d "$HUB_DIR" ] || die "Hub directory not found: $HUB_DIR"
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
[ -f "$HUB_DIR/AGENTS.md" ] && [ -f "$HUB_DIR/ai/architecture.md" ] || die "target is not an installed Hub"

if [ -n "$SOURCE_DIR" ]; then
  [ -d "$SOURCE_DIR" ] || die "source directory not found: $SOURCE_DIR"
  SOURCE_REPO_ROOT="$(cd "$SOURCE_DIR" && pwd -P)"
else
  command -v git >/dev/null 2>&1 || die "git is required for remote updates"
  RESOLVED_SHA="$(git ls-remote "$REPO_URL" "$REF" "refs/heads/$REF" "refs/tags/$REF^{}" "refs/tags/$REF" | awk 'NR==1{print $1}')"
  [ -n "$RESOLVED_SHA" ] || die "could not resolve remote ref: $REF"
  TMP_DIR="$(mktemp -d)"
  SOURCE_REPO_ROOT="$TMP_DIR/source"
  git init -q "$SOURCE_REPO_ROOT"
  git -C "$SOURCE_REPO_ROOT" remote add origin "$REPO_URL"
  git -C "$SOURCE_REPO_ROOT" fetch -q --depth 1 origin "$RESOLVED_SHA"
  git -C "$SOURCE_REPO_ROOT" checkout -q --detach FETCH_HEAD
  [ "$(git -C "$SOURCE_REPO_ROOT" rev-parse HEAD)" = "$RESOLVED_SHA" ] || die "resolved revision changed during fetch"
  echo "Resolved revision: $RESOLVED_SHA"
fi

[ -f "$SOURCE_REPO_ROOT/scripts/hub_release.py" ] || die "source is missing scripts/hub_release.py"
[ -d "$SOURCE_REPO_ROOT/hub-template" ] || die "source is missing hub-template/"

PLAN_JSON="$(python3 "$SOURCE_REPO_ROOT/scripts/hub_release.py" preview --source "$SOURCE_REPO_ROOT" --hub "$HUB_DIR")"
PLAN_SHA="$(printf '%s' "$PLAN_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["plan_sha256"])')"
DIFF_COUNT="$(printf '%s' "$PLAN_JSON" | python3 -c 'import json,sys; print(sum(1 for x in json.load(sys.stdin)["operations"] if x["action"] != "keep"))')"

print_plan() {
  printf '%s' "$PLAN_JSON" | python3 -c 'import json,sys
p=json.load(sys.stdin)
for x in p["operations"]:
    if x["action"] != "keep": print(f"{x['"'"'action'"'"']}: {x['"'"'target'"'"']}")
print("Plan SHA256:", p["plan_sha256"])'
}

if [ "$MODE" = "check" ]; then
  if [ "$DIFF_COUNT" -eq 0 ]; then
    echo "Hub managed files match the selected release."
    exit 0
  fi
  echo "Managed files differ from the selected release."
  print_plan
  exit 1
fi

if [ "$MODE" = "dry-run" ]; then
  print_plan
  exit 0
fi

[ -n "$CONFIRM_PLAN" ] || die "--apply requires --confirm-plan from the reviewed preview"
[ "$CONFIRM_PLAN" = "$PLAN_SHA" ] || die "confirmed plan differs from current preview"
if [ "$ALLOW_DIRTY" -ne 1 ] && git -C "$HUB_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 && [ -n "$(git -C "$HUB_DIR" status --porcelain)" ]; then
  die "Hub working tree is dirty; commit/stash first or use --allow-dirty"
fi

python3 "$SOURCE_REPO_ROOT/scripts/hub_release.py" apply --source "$SOURCE_REPO_ROOT" --hub "$HUB_DIR" --confirm-plan "$CONFIRM_PLAN"

if [ "$DO_COMMIT" -eq 1 ]; then
  git -C "$HUB_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "--commit requires a Git Hub"
  git -C "$HUB_DIR" add -u
  git -C "$HUB_DIR" add AGENTS.md CLAUDE.md ai scripts 2>/dev/null || true
  if ! git -C "$HUB_DIR" diff --cached --quiet; then
    git -C "$HUB_DIR" commit -m "chore: update personal AI hub"
  fi
fi
