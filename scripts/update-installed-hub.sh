#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/zykovsrg/ai-dev-architecture-template"
REF="main"
MODE="dry-run"
DO_COMMIT="false"
ALLOW_DIRTY="false"
CHECK="false"
HUB_DIR="$PWD"
SOURCE_DIR=""
COMMIT_MESSAGE="chore: update personal AI hub"
TMP_DIR=""
SOURCE_TEMPLATE=""
SOURCE_VALIDATOR=""
CREATED_MEMORY_FILES=()

usage() {
  cat <<'EOF'
Usage:
  update-installed-hub.sh [options]

Safe updater for an installed personal AI hub.

Default mode is --dry-run: print protected-file diffs without changing files.

Options:
  --check            Compare the hub architecture version with the source and,
                     if the hub is behind, show a dry-run preview. Never writes.
  --dry-run          Show planned changes only. Default.
  --apply            Apply protected-file updates and add missing memory templates.
  --commit           Apply updates and commit only updater-managed changes.
  --hub DIR          Hub directory. Default: current directory.
  --source DIR       Local template repository or hub-template directory. Optional.
  --ref REF          GitHub ref to download when --source is omitted. Default: main.
  --allow-dirty      Allow apply when the hub has uncommitted changes.
  -h, --help         Show this help.

Examples:
  bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/ai-dev-architecture-template --dry-run
  bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/ai-dev-architecture-template --apply --commit
EOF
}

read_arch_version() {
  [ -f "$1" ] || return 0
  sed -n -E 's/^Version:[[:space:]]*([0-9]+\.[0-9]+).*/\1/p' "$1" | head -n 1
}

version_lt() {
  awk -v a="$1" -v b="$2" '
    BEGIN {
      na = split(a, pa, ".")
      nb = split(b, pb, ".")
      amaj = pa[1] + 0; amin = (na > 1 ? pa[2] + 0 : 0)
      bmaj = pb[1] + 0; bmin = (nb > 1 ? pb[2] + 0 : 0)
      if (amaj < bmaj) exit 0
      if (amaj > bmaj) exit 1
      if (amin < bmin) exit 0
      exit 1
    }'
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

cleanup() {
  if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      MODE="dry-run"
      ;;
    --apply)
      MODE="apply"
      ;;
    --commit)
      MODE="apply"
      DO_COMMIT="true"
      ;;
    --hub)
      shift
      [ "$#" -gt 0 ] || die "--hub requires a directory"
      HUB_DIR="$1"
      ;;
    --source)
      shift
      [ "$#" -gt 0 ] || die "--source requires a directory"
      SOURCE_DIR="$1"
      ;;
    --ref)
      shift
      [ "$#" -gt 0 ] || die "--ref requires a GitHub ref"
      REF="$1"
      ;;
    --allow-dirty)
      ALLOW_DIRTY="true"
      ;;
    --check)
      CHECK="true"
      MODE="dry-run"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
  shift
done

if [ "$CHECK" = "true" ]; then
  MODE="dry-run"
  DO_COMMIT="false"
fi

HUB_DIR="$(cd "$HUB_DIR" && pwd)"
cd "$HUB_DIR"

git rev-parse --show-toplevel >/dev/null 2>&1 || die "Hub is not a Git repository: $HUB_DIR"
HUB_ROOT="$(git rev-parse --show-toplevel)"
cd "$HUB_ROOT"
HUB_DIR="$HUB_ROOT"

for required_hub_file in "AGENTS.md" "ai/architecture.md" "ai/project-registry.md"; do
  if [ ! -f "$required_hub_file" ]; then
    die "This does not look like an installed personal AI hub. Missing required file: $required_hub_file. Use scripts/install.sh --mode hub first."
  fi
done

if [ "$MODE" = "apply" ] && [ "$ALLOW_DIRTY" != "true" ] && [ -n "$(git status --porcelain)" ]; then
  die "Working tree is not clean. Commit or stash hub changes first, or rerun with --allow-dirty."
fi

resolve_source_template() {
  if [ -n "$SOURCE_DIR" ]; then
    SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
    if [ -d "$SOURCE_DIR/hub-template/ai" ]; then
      SOURCE_TEMPLATE="$SOURCE_DIR/hub-template"
      SOURCE_VALIDATOR="$SOURCE_DIR/scripts/check-hub-registry.sh"
    elif [ -d "$SOURCE_DIR/ai" ] && [ -f "$SOURCE_DIR/AGENTS.md" ]; then
      SOURCE_TEMPLATE="$SOURCE_DIR"
      SOURCE_VALIDATOR="$(cd "$SOURCE_DIR/.." && pwd)/scripts/check-hub-registry.sh"
    else
      die "--source must point to the template repository or to its hub-template/ directory"
    fi
  else
    command -v curl >/dev/null 2>&1 || die "curl is required"
    command -v tar >/dev/null 2>&1 || die "tar is required"

    TMP_DIR="$(mktemp -d)"
    curl -fsSL "$REPO_URL/archive/$REF.tar.gz" -o "$TMP_DIR/template.tar.gz"
    tar -xzf "$TMP_DIR/template.tar.gz" -C "$TMP_DIR"
    SOURCE_ROOT="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d -name 'ai-dev-architecture-template-*' | head -n 1)"
    [ -n "$SOURCE_ROOT" ] || die "Could not find extracted template repository"
    SOURCE_TEMPLATE="$SOURCE_ROOT/hub-template"
    SOURCE_VALIDATOR="$SOURCE_ROOT/scripts/check-hub-registry.sh"
  fi

  [ -f "$SOURCE_TEMPLATE/AGENTS.md" ] || die "Source hub template is missing AGENTS.md"
  [ -f "$SOURCE_TEMPLATE/CLAUDE.md" ] || die "Source hub template is missing CLAUDE.md"
  [ -f "$SOURCE_TEMPLATE/ai/architecture.md" ] || die "Source hub template is missing ai/architecture.md"
  grep -Fqx '# Personal AI Hub — Codex' "$SOURCE_TEMPLATE/AGENTS.md" \
    || die "Source template is not a personal AI hub"
  grep -Fqx '# Personal AI Hub Architecture' "$SOURCE_TEMPLATE/ai/architecture.md" \
    || die "Source template is not a personal AI hub"
  for mandatory_skill in project-router project-switch project-register registry-check knowledge-capture knowledge-review; do
    [ -f "$SOURCE_TEMPLATE/ai/skills/$mandatory_skill/SKILL.md" ] \
      || die "Source template missing mandatory hub skill: $mandatory_skill"
  done
}

PROTECTED_FILES=(
  "AGENTS.md"
  "CLAUDE.md"
  "ai/architecture.md"
)

MEMORY_FILES=(
  "ai/allowed-roots.md"
  "ai/active-project.md"
  "ai/project-registry.md"
  "ai/cross-project-signals.md"
)

# Paths removed from an installed hub because they were renamed or retired
# upstream. Explicit list only — never "delete whatever the template lacks".
SUPERSEDED_PATHS=()
if [ -n "${SUPERSEDED_TEST_SOURCE:-}" ]; then
  SUPERSEDED_PATHS=(
    "ai/skills/legacy-fixture-skill/SKILL.md"
  )
fi

for_each_superseded_path() {
  local callback="$1" rel
  for rel in ${SUPERSEDED_PATHS[@]+"${SUPERSEDED_PATHS[@]}"}; do
    "$callback" "$rel"
  done
}

show_superseded_path() {
  local rel="$1"
  [ -e "$HUB_DIR/$rel" ] || return 0
  changes_found=1
  echo "  $rel"
}

path_contains_symlink() {
  local base="$1" rel="$2" remaining component child
  remaining="$rel"

  while [ -n "$remaining" ]; do
    component="${remaining%%/*}"
    if [ "$remaining" = "$component" ]; then
      remaining=""
    else
      remaining="${remaining#*/}"
    fi

    case "$component" in
      ''|.) ;;
      ..)
        return 1
        ;;
      *)
        child="$base/$component"
        if [ -L "$child" ]; then
          return 0
        fi
        base="$child"
        ;;
    esac
  done

  return 1
}

remove_superseded_path() {
  local rel="$1" target="$HUB_DIR/$rel"

  # Validate rel is non-empty and hub-relative
  case "$rel" in
    "") die "superseded path must not be empty" ;;
    /*) die "superseded path must be hub-relative without traversal: $rel" ;;
    *..*)
      # Check for .. as a path component
      case "$rel" in
        */..*|../*)
          die "superseded path must be hub-relative without traversal: $rel"
          ;;
      esac
      ;;
  esac

  # Check if any component of the path is a symlink
  if path_contains_symlink "$HUB_DIR" "$rel"; then
    die "superseded path must not be a symlink: $rel"
  fi

  [ -e "$target" ] || return 0

  rm -rf "$target"
  echo "Removed superseded path: $rel"
}

changes_found=0

show_file_diff() {
  local rel="$1"
  local src="$SOURCE_TEMPLATE/$rel"
  local dst="$HUB_DIR/$rel"

  [ "$rel" = "scripts/check-hub-registry.sh" ] && src="$SOURCE_VALIDATOR"

  [ -f "$src" ] || return 0

  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
    return 0
  fi

  changes_found=1
  echo ""
  echo "### $rel"

  if [ -f "$dst" ]; then
    diff -u "$dst" "$src" || true
  else
    echo "Would create protected hub file: $rel"
    diff -u /dev/null "$src" || true
  fi
}

show_missing_memory_file() {
  local rel="$1"
  local src="$SOURCE_TEMPLATE/$rel"
  local dst="$HUB_DIR/$rel"

  [ -f "$src" ] || return 0

  if [ ! -e "$dst" ]; then
    changes_found=1
    echo ""
    echo "### $rel"
    echo "Would create missing hub memory file without overwriting hub memory: $rel"
  fi
}

copy_file() {
  local rel="$1"
  local src="$SOURCE_TEMPLATE/$rel"
  local dst="$HUB_DIR/$rel"

  [ "$rel" = "scripts/check-hub-registry.sh" ] && src="$SOURCE_VALIDATOR"

  [ -f "$src" ] || return 0
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
}

copy_missing_memory_file() {
  local rel="$1"
  local src="$SOURCE_TEMPLATE/$rel"
  local dst="$HUB_DIR/$rel"

  [ -f "$src" ] || return 0
  if [ ! -e "$dst" ]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    CREATED_MEMORY_FILES+=("$rel")
  fi
}

for_each_protected_file() {
  local callback="$1"
  local rel

  for rel in "${PROTECTED_FILES[@]}"; do
    "$callback" "$rel"
  done

  if [ -f "$SOURCE_VALIDATOR" ]; then
    "$callback" "scripts/check-hub-registry.sh"
  fi

  if [ -d "$SOURCE_TEMPLATE/ai/skills" ]; then
    while IFS= read -r src_file; do
      rel="${src_file#$SOURCE_TEMPLATE/}"
      "$callback" "$rel"
    done < <(find "$SOURCE_TEMPLATE/ai/skills" -type f | sort)
  fi
}

for_each_memory_file() {
  local callback="$1"
  local rel

  for rel in "${MEMORY_FILES[@]}"; do
    "$callback" "$rel"
  done

  for memory_dir in "ai/project-cards" "ai/archive"; do
    if [ -d "$SOURCE_TEMPLATE/$memory_dir" ]; then
      while IFS= read -r src_file; do
        rel="${src_file#$SOURCE_TEMPLATE/}"
        "$callback" "$rel"
      done < <(find "$SOURCE_TEMPLATE/$memory_dir" -type f | sort)
    fi
  done
}

append_existing_path() {
  local rel="$1"
  if [ -e "$HUB_DIR/$rel" ]; then
    UPDATE_PATHS+=("$rel")
  fi
}

resolve_source_template

echo "Hub: $HUB_DIR"
echo "Source template: $SOURCE_TEMPLATE"
if [ "$CHECK" = "true" ]; then
  echo "Mode: check"
else
  echo "Mode: $MODE"
fi
if [ "$DO_COMMIT" = "true" ]; then
  echo "Commit: enabled"
fi

DRY_RUN_EXIT=0

if [ "$CHECK" = "true" ]; then
  source_version="$(read_arch_version "$SOURCE_TEMPLATE/ai/architecture.md")"
  hub_version="$(read_arch_version "$HUB_DIR/ai/architecture.md")"
  [ -n "$source_version" ] || die "Could not read architecture version from the source hub template."

  echo ""
  if [ -z "$hub_version" ]; then
    echo "Hub architecture version: unknown (no readable 'Version:' line)."
    echo "Latest architecture version: v$source_version"
    echo "Could not read the hub version — recommend updating. Preview below."
    DRY_RUN_EXIT=1
  elif version_lt "$hub_version" "$source_version"; then
    echo "Hub architecture version: v$hub_version"
    echo "Latest architecture version: v$source_version"
    echo "Update available. Preview below (no files are changed)."
    DRY_RUN_EXIT=1
  else
    echo "Hub architecture is up to date (v$hub_version)."
    exit 0
  fi
fi

if [ "$MODE" = "dry-run" ]; then
  echo ""
  echo "Dry run. No files will be changed."
  echo ""
  echo "Protected hub files to compare:"
  for_each_protected_file show_file_diff
  echo ""
  echo "Hub memory templates to create only if missing:"
  for_each_memory_file show_missing_memory_file
  echo ""
  echo "Superseded paths to remove:"
  for_each_superseded_path show_superseded_path

  if [ "$changes_found" -eq 0 ]; then
    echo ""
    echo "No hub updates found."
  else
    echo ""
    echo "Dry run complete. To apply:"
    echo "  bash scripts/update-installed-hub.sh --apply"
  fi
  exit "$DRY_RUN_EXIT"
fi

for_each_protected_file copy_file
for_each_memory_file copy_missing_memory_file
for_each_superseded_path remove_superseded_path

UPDATE_PATHS=()
for_each_protected_file append_existing_path
if [ "${#CREATED_MEMORY_FILES[@]}" -gt 0 ]; then
  for rel in "${CREATED_MEMORY_FILES[@]}"; do
    UPDATE_PATHS+=("$rel")
  done
fi

echo ""
echo "Applied personal AI hub update. Current updater-managed changes:"
if [ "${#UPDATE_PATHS[@]}" -gt 0 ]; then
  git status --short -- "${UPDATE_PATHS[@]}"
  git diff -- "${UPDATE_PATHS[@]}"
fi

if [ "$DO_COMMIT" = "true" ]; then
  if [ "${#UPDATE_PATHS[@]}" -gt 0 ]; then
    git add -- "${UPDATE_PATHS[@]}"
  fi

  if [ "${#UPDATE_PATHS[@]}" -eq 0 ] || git diff --cached --quiet -- "${UPDATE_PATHS[@]}"; then
    echo ""
    echo "No updater-managed changes to commit."
  else
    git commit -m "$COMMIT_MESSAGE" -- "${UPDATE_PATHS[@]}"
  fi
fi

echo ""
echo "Hub memory was preserved; only missing memory templates were created."
