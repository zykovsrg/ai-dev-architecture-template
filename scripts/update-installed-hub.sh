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
REMOVED_PATHS=()

usage() {
  cat <<'EOF'
Usage:
  update-installed-hub.sh [options]

Safe updater for an installed personal AI hub.

Default mode is --dry-run: print protected-file diffs without changing files.

Options:
  --check            Compare the hub architecture VERSION NUMBER with the source
                     and, if the hub is behind, show a dry-run preview. Does not
                     compare file contents — use --dry-run for that. Never writes.
  --dry-run          Show planned changes only. Default.
  --apply            Apply protected-file updates, add missing memory templates,
                     and remove superseded paths listed by the updater.
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
      # Resolve now, before the script cd's into the hub. A relative path
      # resolved later would be taken relative to the hub, not the caller.
      [ -d "$1" ] || die "--source directory not found: $1"
      SOURCE_DIR="$(cd "$1" && pwd -P)"
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
  # An installed hub is a copy of the template and satisfies every check above,
  # so without this guard the updater can compare the hub with itself and
  # report "no updates" (Audit 1).
  if [ "$(cd "$SOURCE_TEMPLATE" && pwd -P)" = "$(cd "$HUB_DIR" && pwd -P)" ]; then
    die "--source resolves to the hub itself; pass the template repository path"
  fi
  for mandatory_skill in hub-project-router hub-project-switch hub-project-register hub-registry-check hub-knowledge-capture hub-knowledge-review; do
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
  "ai/archiprojects.md"
  "ai/project-registry.md"
  "ai/cross-project-signals.md"
)

# Paths removed from an installed hub because they were renamed or retired
# upstream. Explicit list only — never "delete whatever the template lacks".
SUPERSEDED_PATHS=(
  "ai/skills/environment-check"
  "ai/skills/info-update"
  "ai/skills/knowledge-capture"
  "ai/skills/knowledge-enable"
  "ai/skills/knowledge-review"
  "ai/skills/local-router-install"
  "ai/skills/project-create"
  "ai/skills/project-migrate"
  "ai/skills/project-register"
  "ai/skills/project-router"
  "ai/skills/project-switch"
  "ai/skills/registry-check"
  "ai/skills/task-finish"
  "ai/skills/task-intake"
  "ai/skills/task-switch"
)
if [ -n "${SUPERSEDED_TEST_EMPTY:-}" ]; then
  SUPERSEDED_PATHS+=("")
fi
if [ -n "${SUPERSEDED_TEST_DOTDOT:-}" ]; then
  SUPERSEDED_PATHS+=("..")
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

STALE_SUPERSEDED_FOUND=0
mark_stale_superseded_path() {
  local rel="$1"
  [ -n "$rel" ] || return 0
  [ -e "$HUB_DIR/$rel" ] || return 0
  STALE_SUPERSEDED_FOUND=1
}

hub_has_stale_superseded_paths() {
  STALE_SUPERSEDED_FOUND=0
  for_each_superseded_path mark_stale_superseded_path
  [ "$STALE_SUPERSEDED_FOUND" -eq 1 ]
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

validate_superseded_path() {
  local rel="$1"

  # Validate rel is non-empty and hub-relative
  case "$rel" in
    "") die "superseded path must not be empty" ;;
    /*) die "superseded path must be hub-relative without traversal: $rel" ;;
    ..|*..*)
      # Check for .. as a whole path component, in any position.
      case "$rel" in
        ..|*/..|../*|*/../*)
          die "superseded path must be hub-relative without traversal: $rel"
          ;;
      esac
      ;;
  esac

  # Check if any component of the path is a symlink
  if path_contains_symlink "$HUB_DIR" "$rel"; then
    die "superseded path must not be a symlink: $rel"
  fi
}

remove_superseded_path() {
  local rel="$1" target="$HUB_DIR/$rel"

  [ -e "$target" ] || return 0

  rm -rf "$target"
  REMOVED_PATHS+=("$rel")
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

# Append-only, mirroring install-hub.sh:90-91. Never overwrite: the hub's
# .gitignore may carry the user's own entries, which a protected-file copy
# would destroy (Audit 5).
ensure_projects_ignored() {
  if ! grep -Fqx '/projects/' "$HUB_DIR/.gitignore" 2>/dev/null; then
    printf '%s\n' '/projects/' >> "$HUB_DIR/.gitignore"
    echo "Added missing ignore line: /projects/"
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

# The version gate for superseded-path removal is evaluated up front, right
# after the source template is resolved, so it can refuse an old source
# before --apply copies a single byte (dry-run/check only report it).
MIN_REMOVAL_VERSION="1.3"
SOURCE_VERSION_FOR_REMOVAL="$(read_arch_version "$SOURCE_TEMPLATE/ai/architecture.md")"
REMOVAL_VERSION_GATE_MESSAGE="Source template version ${SOURCE_VERSION_FOR_REMOVAL:-unknown} is older than $MIN_REMOVAL_VERSION (the version that introduced superseded-path removal); refusing to delete hub skills — use a source template at or above version $MIN_REMOVAL_VERSION."
removal_version_gate_blocked() {
  [ -z "$SOURCE_VERSION_FOR_REMOVAL" ] || version_lt "$SOURCE_VERSION_FOR_REMOVAL" "$MIN_REMOVAL_VERSION"
}

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
  elif hub_has_stale_superseded_paths; then
    echo "Hub architecture is up to date (v$hub_version), but stale superseded paths remain."
    echo "Run --apply to remove them. Preview below (no files are changed)."
    DRY_RUN_EXIT=1
  else
    echo "Version numbers match (v$hub_version). This compares the version line only,"
    echo "not file contents. Run --dry-run to compare the files themselves."
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

  if removal_version_gate_blocked; then
    changes_found=1
    echo ""
    echo "$REMOVAL_VERSION_GATE_MESSAGE"
  fi

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

if removal_version_gate_blocked; then
  die "$REMOVAL_VERSION_GATE_MESSAGE"
fi

for_each_protected_file copy_file
ensure_projects_ignored
for_each_memory_file copy_missing_memory_file

# Validate every superseded-path entry before deleting anything: an invalid
# entry discovered mid-list must not leave earlier, valid entries already
# removed while later entries are still untouched.
for_each_superseded_path validate_superseded_path
for_each_superseded_path remove_superseded_path

UPDATE_PATHS=()
for_each_protected_file append_existing_path
if [ "${#CREATED_MEMORY_FILES[@]}" -gt 0 ]; then
  for rel in "${CREATED_MEMORY_FILES[@]}"; do
    UPDATE_PATHS+=("$rel")
  done
fi
if [ "${#REMOVED_PATHS[@]}" -gt 0 ]; then
  for rel in "${REMOVED_PATHS[@]}"; do
    UPDATE_PATHS+=("$rel")
  done
fi

if [ "${#REMOVED_PATHS[@]}" -gt 0 ]; then
  echo ""
  echo "Removed ${#REMOVED_PATHS[@]} superseded path(s):"
  for rel in "${REMOVED_PATHS[@]}"; do
    echo "  $rel"
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
