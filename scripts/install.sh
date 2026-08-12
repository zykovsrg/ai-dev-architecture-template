#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_TEMPLATE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/template"

usage() {
  echo "Usage: $0 [--mode standalone|hub] [--root DIR ...] [TARGET_DIR]" >&2
  exit 1
}

MODE=""
ROOT_ARGS=()
TARGET_DIR=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode)
      [ "$#" -ge 2 ] || usage
      MODE="$2"
      shift 2
      ;;
    --root)
      [ "$#" -ge 2 ] || usage
      ROOT_ARGS+=("--root" "$2")
      shift 2
      ;;
    --)
      shift
      [ "$#" -le 1 ] || usage
      TARGET_DIR="${1:-.}"
      break
      ;;
    -*)
      usage
      ;;
    *)
      [ -z "$TARGET_DIR" ] || usage
      TARGET_DIR="$1"
      shift
      ;;
  esac
done

TARGET_DIR="${TARGET_DIR:-.}"

if [ -z "$MODE" ]; then
  if [ -t 0 ] && [ -t 1 ]; then
    read -r -p "Установить дополнительный personal AI hub? [д/Н] " install_hub
    case "$install_hub" in
      д|Д|да|Да|ДА|y|Y|yes|Yes|YES) MODE="hub" ;;
      *) MODE="standalone" ;;
    esac
  else
    MODE="standalone"
  fi
fi

if [ "$MODE" = "hub" ] && [ "${#ROOT_ARGS[@]}" -eq 0 ]; then
  if [ -t 0 ] && [ -t 1 ]; then
    echo "Укажите хотя бы один разрешённый корень через --root DIR и повторите команду." >&2
  fi
  echo "Hub mode requires at least one --root DIR." >&2
  exit 1
fi

case "$MODE" in
  hub)
    exec "$SCRIPT_DIR/install-hub.sh" "${ROOT_ARGS[@]}" "$TARGET_DIR"
    ;;
  standalone)
    [ "${#ROOT_ARGS[@]}" -eq 0 ] || {
      echo "--root is available only in hub mode." >&2
      exit 1
    }
    ;;
  *)
    echo "Unknown installation mode: $MODE" >&2
    usage
    ;;
esac

if [ -n "${AI_DEV_ARCH_TEMPLATE:-}" ]; then
  TEMPLATE_DIR="$AI_DEV_ARCH_TEMPLATE"
elif [ -d "$REPO_TEMPLATE_DIR" ]; then
  TEMPLATE_DIR="$REPO_TEMPLATE_DIR"
else
  TEMPLATE_DIR="$HOME/Documents/ai-dev-architecture-template/template"
fi

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
echo "1. Open the start screen: $(cd "$SCRIPT_DIR/.." && pwd)/getting-started/getting-started.md"
echo "2. Fill ai/project-context.md"
echo "3. Run environment-check in the agent"
echo "4. Use task-intake to record the first task in ai/current-task.md"
echo "5. Use the final menu as a list of available next commands, not as automatic workflow execution"
