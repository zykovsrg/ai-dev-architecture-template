#!/usr/bin/env bash
set -euo pipefail

TEMPLATE_DIR="${AI_DEV_ARCH_TEMPLATE:-$HOME/Documents/ai-dev-architecture-template/template}"
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
echo "1. Fill ai/project-context.md"
echo "2. Fill ai/current-task.md"
echo "3. Run environment-check in the agent"
echo "4. Use the final menu as a list of available next commands, not as automatic workflow execution"
