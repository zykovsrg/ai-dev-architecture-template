#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="hub"
TARGET_DIR=""

usage() {
  cat >&2 <<'EOF'
Usage: install.sh [--mode hub] /path/to/_ai-hub

Personal AI Hub is the only supported installation mode.
The retired standalone mode is no longer installable.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode)
      [ "$#" -ge 2 ] || { usage; exit 1; }
      MODE="$2"
      shift 2
      ;;
    --root)
      echo "--root is not supported: projects live in _ai-hub/projects/." >&2
      exit 1
      ;;
    --)
      shift
      [ "$#" -le 1 ] || { usage; exit 1; }
      TARGET_DIR="${1:-}"
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      usage
      exit 1
      ;;
    *)
      [ -z "$TARGET_DIR" ] || { usage; exit 1; }
      TARGET_DIR="$1"
      shift
      ;;
  esac
done

case "$MODE" in
  hub) ;;
  standalone)
    echo "Standalone installation is retired. Install the Personal AI Hub, then register/create/migrate the project through Hub workflows." >&2
    exit 2
    ;;
  *)
    echo "Unsupported installation mode: $MODE. Only hub is supported." >&2
    exit 1
    ;;
esac

[ -n "$TARGET_DIR" ] || { usage; exit 1; }
exec bash "$SCRIPT_DIR/install-hub.sh" "$TARGET_DIR"
