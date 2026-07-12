#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_TEMPLATE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/template"

if [ -n "${AI_DEV_ARCH_TEMPLATE:-}" ]; then
  TEMPLATE_DIR="$AI_DEV_ARCH_TEMPLATE"
elif [ -d "$REPO_TEMPLATE_DIR" ]; then
  TEMPLATE_DIR="$REPO_TEMPLATE_DIR"
else
  TEMPLATE_DIR="$HOME/Documents/ai-dev-architecture-template/template"
fi
TARGET_DIR="${1:-.}"

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "Template directory not found: $TEMPLATE_DIR"
  echo "Clone the template repository first:"
  echo "cd ~/Documents && git clone git@github.com:zykovsrg/ai-dev-architecture-template.git"
  exit 1
fi

mkdir -p "$TARGET_DIR"
rsync -av --ignore-existing "$TEMPLATE_DIR/" "$TARGET_DIR/"

echo ""
echo "AI development architecture copied into: $TARGET_DIR"
echo "Existing files were not overwritten."
echo ""
echo "Next steps:"
echo "1. Open the start screen: $(cd "$SCRIPT_DIR/.." && pwd)/start-screen/start-screen.md"
echo "2. Fill ai/project-context.md"
echo "3. Run environment-check in the agent"
echo "4. Use task-intake to record the first task in ai/current-task.md"
echo "5. Use the final menu as a list of available next commands, not as automatic workflow execution"
