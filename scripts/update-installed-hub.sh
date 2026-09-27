#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${HUB_RELEASE_REPO_URL:-https://github.com/zykovsrg/ai-dev-architecture-template.git}"
REF="main"
MODE="dry-run"
HUB_DIR="$PWD"
SOURCE_DIR=""
CONFIRM_PLAN=""
CONFIRM_SOURCE_SHA=""
DO_COMMIT=0
ALLOW_DIRTY=0
TMP_DIR=""
RESOLVED_SHA=""
MODULE_ARGS=()

usage() {
  cat <<'EOF'
Usage: update-installed-hub.sh [--check|--dry-run|--apply --confirm-plan SHA --confirm-source-sha SHA] [--hub DIR] [--source DIR | --ref REF] [--commit] [--allow-dirty] [--with ID] [--without ID]

Uses scripts/hub_release.py as the single preview/apply engine.
Remote preview resolves one immutable commit SHA and includes it in the plan.
Remote apply requires that exact SHA and fetches it directly, so a moved branch/tag
cannot silently change the reviewed release.
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
    --confirm-source-sha) shift; [ "$#" -gt 0 ] || die "--confirm-source-sha requires a commit SHA"; CONFIRM_SOURCE_SHA="$1" ;;
    --with|--without) opt="$1"; shift; [ "$#" -gt 0 ] || die "$opt requires a module id"; MODULE_ARGS+=("$opt" "$1") ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

[ -d "$HUB_DIR" ] || die "Hub directory not found: $HUB_DIR"
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
[ -f "$HUB_DIR/AGENTS.md" ] && [ -f "$HUB_DIR/ai/architecture.md" ] || die "target is not an installed Hub"

if [ -n "$SOURCE_DIR" ]; then
  [ -z "$CONFIRM_SOURCE_SHA" ] || die "--confirm-source-sha is only valid for remote updates"
  [ -d "$SOURCE_DIR" ] || die "source directory not found: $SOURCE_DIR"
  SOURCE_REPO_ROOT="$(cd "$SOURCE_DIR" && pwd -P)"
else
  command -v git >/dev/null 2>&1 || die "git is required for remote updates"
  if [ "$MODE" = "apply" ]; then
    [ -n "$CONFIRM_SOURCE_SHA" ] || die "remote --apply requires --confirm-source-sha from the reviewed preview"
    [[ "$CONFIRM_SOURCE_SHA" =~ ^[0-9a-fA-F]{40}$ ]] || die "invalid --confirm-source-sha"
    RESOLVED_SHA="$(printf '%s' "$CONFIRM_SOURCE_SHA" | tr 'A-F' 'a-f')"
  elif [[ "$REF" =~ ^[0-9a-fA-F]{40}$ ]]; then
    RESOLVED_SHA="$(printf '%s' "$REF" | tr 'A-F' 'a-f')"
  else
    RESOLVED_SHA="$(git ls-remote "$REPO_URL" "$REF" "refs/heads/$REF" "refs/tags/$REF^{}" "refs/tags/$REF" | awk 'NR==1{print $1}')"
  fi
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

if [ -n "$RESOLVED_SHA" ]; then
  PLAN_JSON="$(python3 "$SOURCE_REPO_ROOT/scripts/hub_release.py" preview --source "$SOURCE_REPO_ROOT" --hub "$HUB_DIR" --source-sha "$RESOLVED_SHA" ${MODULE_ARGS[@]+"${MODULE_ARGS[@]}"})"
else
  PLAN_JSON="$(python3 "$SOURCE_REPO_ROOT/scripts/hub_release.py" preview --source "$SOURCE_REPO_ROOT" --hub "$HUB_DIR" ${MODULE_ARGS[@]+"${MODULE_ARGS[@]}"})"
fi
PLAN_SHA="$(printf '%s' "$PLAN_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["plan_sha256"])')"
DIFF_COUNT="$(printf '%s' "$PLAN_JSON" | python3 -c 'import json,sys; print(sum(1 for x in json.load(sys.stdin)["operations"] if x["action"] != "keep"))')"

print_plan() {
  # Every apply action must appear here: sync-calendar-policy.sh runs on every
  # apply (see below), refreshing the server when calendar stays selected and
  # removing it when it doesn't -- regardless of whether the selection just
  # changed. previous_modules being unknown (fresh Hub, no installed.json yet)
  # is not a reason to omit the line: the post-apply step still runs.
  PLAN_JSON="$PLAN_JSON" python3 - <<'PY'
import json, os
p = json.loads(os.environ["PLAN_JSON"])
for x in p["operations"]:
    if x["action"] != "keep":
        print(f"{x['action']}: {x['target']}")
print("Modules:", ", ".join(p["modules"]))
prev = p.get("previous_modules")
if prev is not None:
    change = [f"-{m}" for m in prev if m not in p["modules"]] + [f"+{m}" for m in p["modules"] if m not in prev]
    if change:
        print("Module change:", " ".join(change))
if "calendar" in p["modules"]:
    print("Extra step: refresh calendar server (tools/apple-calendar-policy, bridge rebuild, .mcp.json hub_calendar if missing)")
else:
    print("Extra step: remove calendar server (tools/apple-calendar-policy, .mcp.json hub_calendar)")
print("Plan SHA256:", p["plan_sha256"])
if p.get("source_sha"):
    print("Source SHA:", p["source_sha"])
PY
}

calendar_selected() {
  PLAN_JSON="$PLAN_JSON" python3 -c 'import json, os; print("1" if "calendar" in json.loads(os.environ["PLAN_JSON"])["modules"] else "0")'
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
  [ -z "$RESOLVED_SHA" ] || echo "Apply with: --ref $REF --confirm-source-sha $RESOLVED_SHA --confirm-plan $PLAN_SHA"
  exit 0
fi

[ -n "$CONFIRM_PLAN" ] || die "--apply requires --confirm-plan from the reviewed preview"
[ "$CONFIRM_PLAN" = "$PLAN_SHA" ] || die "confirmed plan differs from current preview"
if [ "$ALLOW_DIRTY" -ne 1 ] && git -C "$HUB_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 && [ -n "$(git -C "$HUB_DIR" status --porcelain)" ]; then
  die "Hub working tree is dirty; commit/stash first or use --allow-dirty"
fi

if [ -n "$RESOLVED_SHA" ]; then
  python3 "$SOURCE_REPO_ROOT/scripts/hub_release.py" apply --source "$SOURCE_REPO_ROOT" --hub "$HUB_DIR" \
    --source-sha "$RESOLVED_SHA" --confirm-source-sha "$CONFIRM_SOURCE_SHA" --confirm-plan "$CONFIRM_PLAN" ${MODULE_ARGS[@]+"${MODULE_ARGS[@]}"}
else
  python3 "$SOURCE_REPO_ROOT/scripts/hub_release.py" apply --source "$SOURCE_REPO_ROOT" --hub "$HUB_DIR" --confirm-plan "$CONFIRM_PLAN" ${MODULE_ARGS[@]+"${MODULE_ARGS[@]}"}
fi

if [ -f "$SOURCE_REPO_ROOT/modules/calendar/scripts/sync-calendar-policy.sh" ]; then
  CALENDAR_REMOVE_FLAG=""
  if [ "$(calendar_selected)" = "0" ]; then CALENDAR_REMOVE_FLAG="--remove"; fi
  if ! bash "$SOURCE_REPO_ROOT/modules/calendar/scripts/sync-calendar-policy.sh" --source "$SOURCE_REPO_ROOT" --hub "$HUB_DIR" ${CALENDAR_REMOVE_FLAG:+$CALENDAR_REMOVE_FLAG}; then
    echo "Hub files were updated, but the calendar server step failed." >&2
    echo "Rerun: bash \"$SOURCE_REPO_ROOT/modules/calendar/scripts/sync-calendar-policy.sh\" --source \"$SOURCE_REPO_ROOT\" --hub \"$HUB_DIR\" ${CALENDAR_REMOVE_FLAG}" >&2
    exit 1
  fi
fi

if [ "$DO_COMMIT" -eq 1 ]; then
  git -C "$HUB_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "--commit requires a Git Hub"
  git -C "$HUB_DIR" add -u
  git -C "$HUB_DIR" add AGENTS.md CLAUDE.md ai scripts 2>/dev/null || true
  if ! git -C "$HUB_DIR" diff --cached --quiet; then
    git -C "$HUB_DIR" commit -m "chore: update personal AI hub"
  fi
fi
