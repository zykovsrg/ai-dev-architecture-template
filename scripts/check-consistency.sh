#!/usr/bin/env bash
# Verify that every canonical list (wrapped in <!-- canon:NAME --> markers)
# holds the same ordered set of file paths across all files that contain it.
# macOS bash 3.2 compatible: no mapfile, no associative arrays.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MARKERS="canon:protected-files canon:controlled-memory"
fail=0

# extract_block FILE MARKER -> prints one path per line (first `backtick` token)
extract_block() {
  awk -v open="<!-- $2 -->" -v endmark="<!-- /$2 -->" '
    index($0, open)    { inb=1; next }
    index($0, endmark) { inb=0 }
    inb { print }
  ' "$1" \
  | { grep -E '^[[:space:]]*[-*][[:space:]].*`' || true; } \
  | sed -E 's/^[^`]*`([^`]+)`.*/\1/'
}

for marker in $MARKERS; do
  files=""
  while IFS= read -r f; do
    files="$files$f"$'\n'
  done < <(grep -rlF --include='*.md' --exclude-dir=superpowers "<!-- $marker -->" . | sort)

  files="$(printf '%s' "$files" | sed '/^$/d')"
  if [ -z "$files" ]; then
    echo "WARN: no holders found for $marker"
    continue
  fi

  ref=""
  ref_list=""
  marker_ok=1
  while IFS= read -r f; do
    cur_list="$(extract_block "$f" "$marker")"
    if [ -z "$ref" ]; then
      ref="$f"
      ref_list="$cur_list"
      continue
    fi
    if [ "$cur_list" != "$ref_list" ]; then
      fail=1
      marker_ok=0
      echo "MISMATCH [$marker]"
      echo "  reference: $ref"
      echo "  differs:   $f"
      diff <(printf '%s\n' "$ref_list") <(printf '%s\n' "$cur_list") | sed 's/^/    /' || true
    fi
  done <<EOF
$files
EOF

  if [ "$marker_ok" -eq 1 ]; then
    n="$(printf '%s\n' "$files" | grep -c . || true)"
    if [ "$n" -lt 2 ]; then
      echo "WARN: only $n holder for $marker — nothing to cross-check"
    else
      echo "OK [$marker] — $n holders consistent"
    fi
  fi
done

if [ "$fail" -ne 0 ]; then
  echo ""
  echo "Consistency check FAILED. Make the marked lists identical (same paths, same order)."
  exit 1
fi
echo ""
echo "All canonical lists are consistent."
