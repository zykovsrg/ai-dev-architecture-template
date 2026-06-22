#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/zykovsrg/ai-dev-architecture-template"
REF="main"
MODE="dry-run"
DO_COMMIT="false"
ALLOW_DIRTY="false"
CHECK="false"
PROJECT_DIR="$PWD"
SOURCE_DIR=""
COMMIT_MESSAGE="chore: update AI development architecture"
TMP_DIR=""
SOURCE_TEMPLATE=""

usage() {
  cat <<'EOF'
Usage:
  update-installed-architecture.sh [options]

Safe updater for projects where ai-dev-architecture-template is already installed.

Default mode is --dry-run: print the architecture diff without changing files.

Options:
  --check            Compare the project architecture version with the source and,
                     if the project is behind, show a dry-run preview. Never writes.
  --dry-run          Show planned changes only. Default.
  --apply            Apply architecture updates.
  --commit           Apply updates and commit them.
  --project DIR      Project directory. Default: current directory.
  --source DIR       Local template repository or template directory. Optional.
  --ref REF          GitHub ref to download when --source is omitted. Default: main.
  --allow-dirty      Allow apply when the project has uncommitted changes.
  -h, --help         Show this help.

Examples:
  curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --check
  curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --dry-run
  curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --apply --commit
  bash scripts/update-installed-architecture.sh --project /path/to/project --source /path/to/ai-dev-architecture-template --dry-run
EOF
}

# read_arch_version FILE -> prints the X.Y after "Version:" on the first matching line, or empty
read_arch_version() {
  [ -f "$1" ] || return 0
  sed -n -E 's/^Version:[[:space:]]*([0-9]+\.[0-9]+).*/\1/p' "$1" | head -n 1
}

# version_lt A B -> exit 0 (true) if version A is strictly less than B, comparing major then minor numerically
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
    --project)
      shift
      [ "$#" -gt 0 ] || die "--project requires a directory"
      PROJECT_DIR="$1"
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

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
cd "$PROJECT_DIR"

git rev-parse --show-toplevel >/dev/null 2>&1 || die "Project is not a Git repository: $PROJECT_DIR"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"
PROJECT_DIR="$PROJECT_ROOT"

for required_arch_file in "AGENTS.md" "ai/architecture.md" "ai/current-task.md"; do
  if [ ! -f "$required_arch_file" ]; then
    die "This does not look like a project with the AI development architecture installed. Missing required file: $required_arch_file. Use scripts/install.sh first."
  fi
done

if [ "$MODE" = "apply" ] && [ "$ALLOW_DIRTY" != "true" ] && [ -n "$(git status --porcelain)" ]; then
  die "Working tree is not clean. Commit or stash project changes first, or rerun with --allow-dirty."
fi

resolve_source_template() {
  if [ -n "$SOURCE_DIR" ]; then
    SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
    if [ -d "$SOURCE_DIR/template/ai" ]; then
      SOURCE_TEMPLATE="$SOURCE_DIR/template"
    elif [ -d "$SOURCE_DIR/ai" ] && [ -f "$SOURCE_DIR/AGENTS.md" ]; then
      SOURCE_TEMPLATE="$SOURCE_DIR"
    else
      die "--source must point to the template repository or to its template/ directory"
    fi
  else
    command -v curl >/dev/null 2>&1 || die "curl is required"
    command -v tar >/dev/null 2>&1 || die "tar is required"

    TMP_DIR="$(mktemp -d)"
    curl -fsSL "$REPO_URL/archive/$REF.tar.gz" -o "$TMP_DIR/template.tar.gz"
    tar -xzf "$TMP_DIR/template.tar.gz" -C "$TMP_DIR"
    SOURCE_ROOT="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d -name 'ai-dev-architecture-template-*' | head -n 1)"
    [ -n "$SOURCE_ROOT" ] || die "Could not find extracted template repository"
    SOURCE_TEMPLATE="$SOURCE_ROOT/template"
  fi

  [ -f "$SOURCE_TEMPLATE/AGENTS.md" ] || die "Source template is missing AGENTS.md"
  [ -f "$SOURCE_TEMPLATE/CLAUDE.md" ] || die "Source template is missing CLAUDE.md"
  [ -f "$SOURCE_TEMPLATE/ai/architecture.md" ] || die "Source template is missing ai/architecture.md"
}

ARCHITECTURE_FILES=(
  "AGENTS.md"
  "CLAUDE.md"
  "ai/architecture.md"
  "ai/external-tools.md"
)

CONTROLLED_MEMORY_FILES=(
  "ai/project-context.md"
  "ai/current-task.md"
  "ai/decisions.md"
  "ai/changelog.md"
  "ai/paused-tasks.md"
  "ai/future-tasks.md"
  "ai/archive/.gitkeep"
)

changes_found=0

show_file_diff() {
  local rel="$1"
  local src="$SOURCE_TEMPLATE/$rel"
  local dst="$PROJECT_DIR/$rel"

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
    echo "Would create protected architecture file: $rel"
    diff -u /dev/null "$src" || true
  fi
}

show_missing_memory_file() {
  local rel="$1"
  local src="$SOURCE_TEMPLATE/$rel"
  local dst="$PROJECT_DIR/$rel"

  [ -f "$src" ] || return 0

  if [ ! -e "$dst" ]; then
    changes_found=1
    echo ""
    echo "### $rel"
    echo "Would create missing controlled memory file without overwriting project memory: $rel"
  fi
}

copy_file() {
  local rel="$1"
  local src="$SOURCE_TEMPLATE/$rel"
  local dst="$PROJECT_DIR/$rel"

  [ -f "$src" ] || return 0
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
}

copy_missing_memory_file() {
  local rel="$1"
  local src="$SOURCE_TEMPLATE/$rel"
  local dst="$PROJECT_DIR/$rel"

  [ -f "$src" ] || return 0
  if [ ! -e "$dst" ]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
  fi
}

for_each_architecture_file() {
  local callback="$1"
  local rel

  for rel in "${ARCHITECTURE_FILES[@]}"; do
    "$callback" "$rel"
  done

  if [ -d "$SOURCE_TEMPLATE/ai/skills" ]; then
    while IFS= read -r src_file; do
      rel="${src_file#$SOURCE_TEMPLATE/}"
      "$callback" "$rel"
    done < <(find "$SOURCE_TEMPLATE/ai/skills" -type f | sort)
  fi

  for optional_dir in ".claude" ".codex"; do
    if [ -d "$SOURCE_TEMPLATE/$optional_dir" ]; then
      while IFS= read -r src_file; do
        rel="${src_file#$SOURCE_TEMPLATE/}"
        "$callback" "$rel"
      done < <(find "$SOURCE_TEMPLATE/$optional_dir" -type f | sort)
    fi
  done
}

for_each_memory_file() {
  local callback="$1"
  local rel

  for rel in "${CONTROLLED_MEMORY_FILES[@]}"; do
    "$callback" "$rel"
  done
}

add_if_exists() {
  local rel="$1"
  if [ -e "$PROJECT_DIR/$rel" ]; then
    git add "$rel"
  fi
}

resolve_source_template

echo "Project: $PROJECT_DIR"
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
  project_version="$(read_arch_version "$PROJECT_DIR/ai/architecture.md")"
  [ -n "$source_version" ] || die "Could not read architecture version from the source template."

  echo ""
  if [ -z "$project_version" ]; then
    echo "Project architecture version: unknown (no readable 'Version:' line)."
    echo "Latest architecture version:  v$source_version"
    echo "Could not read the project version — recommend updating. Preview below."
    DRY_RUN_EXIT=1
  elif version_lt "$project_version" "$source_version"; then
    echo "Project architecture version: v$project_version"
    echo "Latest architecture version:  v$source_version"
    echo "Update available. Preview below (no files are changed)."
    DRY_RUN_EXIT=1
  else
    echo "Architecture is up to date (v$project_version)."
    exit 0
  fi
fi

if [ "$MODE" = "dry-run" ]; then
  echo ""
  echo "Dry run. No files will be changed."
  echo ""
  echo "Protected architecture files to compare:"
  for_each_architecture_file show_file_diff
  echo ""
  echo "Controlled memory files to create only if missing:"
  for_each_memory_file show_missing_memory_file

  if [ "$changes_found" -eq 0 ]; then
    echo ""
    echo "No architecture updates found."
  else
    echo ""
    echo "Dry run complete. To apply:"
    echo "  bash scripts/update-installed-architecture.sh --apply"
    echo "Or from GitHub:"
    echo "  curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --apply --commit"
  fi
  exit "$DRY_RUN_EXIT"
fi

for_each_architecture_file copy_file
for_each_memory_file copy_missing_memory_file

echo ""
echo "Applied architecture update. Current diff:"
git diff -- \
  AGENTS.md \
  CLAUDE.md \
  ai/architecture.md \
  ai/external-tools.md \
  ai/skills \
  ai/project-context.md \
  ai/current-task.md \
  ai/decisions.md \
  ai/changelog.md \
  ai/paused-tasks.md \
  ai/future-tasks.md \
  ai/archive \
  .claude \
  .codex 2>/dev/null || git diff

if [ "$DO_COMMIT" = "true" ]; then
  for_each_architecture_file add_if_exists
  for_each_memory_file add_if_exists

  if git diff --cached --quiet; then
    echo ""
    echo "No changes to commit."
  else
    git commit -m "$COMMIT_MESSAGE"
  fi
fi

echo ""
echo "Next step: ask the agent to run environment-check. Its final menu is informational only."
