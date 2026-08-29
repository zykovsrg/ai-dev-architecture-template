#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --hub ABSOLUTE_DIRECTORY [--dry-run|--apply]" >&2
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

canonical_dir() {
  [ -d "$1" ] || return 1
  (cd "$1" && pwd -P)
}

regular_file() {
  [ -f "$1" ] && [ ! -L "$1" ]
}

normalized_entry() {
  # AGENTS.md and CLAUDE.md are allowed to differ only in their tool heading.
  sed '1d' "$1"
}

has_bridge() {
  grep -Fqx '## Hub Obsidian Bridge' "$1"
}

render_bridge() {
  local source="$1" destination="$2"
  awk '
    BEGIN {
      bridge = "## Hub Obsidian Bridge\n\n" \
        "When this repository is the registered `<project-id>` direct child of a valid\n" \
        "personal AI hub, requests to import updates from Obsidian use the hub\047s central\n" \
        "vault automatically. Derive `<hub>` from this repository\047s `../..` parent,\n" \
        "verify its registry maps `<project-id>` to this exact project path, then run:\n\n" \
        "`bash <hub>/projects/ai-dev-architecture/scripts/obsidian-task-sync.sh scan --project-id <project-id> --hub <hub> --scope <hub>/ai/tmp/obsidian-scope.txt --vault <hub>/projects/ai-dev-architecture/obsidian-vault`\n\n" \
        "Show the resulting proposal. Apply it only after an explicit confirmation of\n" \
        "its proposal hash, with the same `--project-id`, hub, scope, and vault. If the\n" \
        "hub layout or registry mapping is absent, retain standalone behavior and ask\n" \
        "for a source; never guess a vault path.\n"
    }
    /^## Installation Mode[[:space:]]*$/ { in_section = 1 }
    in_section && /^## / && $0 !~ /^## Installation Mode[[:space:]]*$/ {
      printf "%s\n", bridge
      in_section = 0
      inserted = 1
    }
    { print }
    END {
      if (in_section) {
        printf "\n%s", bridge
        inserted = 1
      }
      if (!inserted) exit 42
    }
  ' "$source" > "$destination"
}

HUB=''
MODE='dry-run'
while [ "$#" -gt 0 ]; do
  case "$1" in
    --hub)
      shift
      [ "$#" -gt 0 ] || die '--hub requires a directory'
      case "$1" in --*) die '--hub requires a directory' ;; esac
      HUB="$1"
      ;;
    --dry-run) MODE='dry-run' ;;
    --apply) MODE='apply' ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

[ -n "$HUB" ] || die '--hub requires a directory'
case "$HUB" in /*) ;; *) die '--hub must be an absolute directory' ;; esac
HUB="$(canonical_dir "$HUB")" || die 'hub must be an existing directory'
git -C "$HUB" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die 'hub must be a Git directory'
regular_file "$HUB/ai/project-registry.md" || die 'missing regular ai/project-registry.md'
regular_file "$HUB/ai/tmp/obsidian-scope.txt" || die 'missing regular ai/tmp/obsidian-scope.txt'

while IFS=$'\t' read -r project_id registered_path; do
  [ -n "$project_id" ] || continue
  expected_path="$HUB/projects/$project_id"
  project_path="$(canonical_dir "$registered_path" 2>/dev/null || true)"
  expected_canonical="$(canonical_dir "$expected_path" 2>/dev/null || true)"
  [ -n "$project_path" ] && [ "$project_path" = "$expected_canonical" ] || continue

  architecture="$project_path/ai/architecture.md"
  regular_file "$architecture" || continue
  grep -Eq '^Version: 7\.3[[:space:]]*$' "$architecture" || continue

  agents="$project_path/AGENTS.md"
  claude="$project_path/CLAUDE.md"
  if ! regular_file "$agents" || ! regular_file "$claude"; then
    echo "SKIP: $project_id has no regular AGENTS.md/CLAUDE.md pair" >&2
    continue
  fi
  if ! cmp -s <(normalized_entry "$agents") <(normalized_entry "$claude"); then
    echo "SKIP: $project_id AGENTS.md/CLAUDE.md differ beyond their tool heading" >&2
    continue
  fi
  if has_bridge "$agents" && has_bridge "$claude"; then
    continue
  fi
  if has_bridge "$agents" || has_bridge "$claude"; then
    echo "SKIP: $project_id has an incomplete bridge pair" >&2
    continue
  fi

  agents_tmp="$(mktemp "$project_path/.AGENTS.md.bridge.XXXXXX")"
  claude_tmp="$(mktemp "$project_path/.CLAUDE.md.bridge.XXXXXX")"
  cleanup_pair() { rm -f "$agents_tmp" "$claude_tmp"; }
  if ! render_bridge "$agents" "$agents_tmp" || ! render_bridge "$claude" "$claude_tmp"; then
    cleanup_pair
    echo "SKIP: $project_id has no Installation Mode section" >&2
    continue
  fi
  if ! cmp -s <(normalized_entry "$agents_tmp") <(normalized_entry "$claude_tmp"); then
    cleanup_pair
    echo "SKIP: $project_id rendered entry files differ" >&2
    continue
  fi

  if [ "$MODE" = 'dry-run' ]; then
    echo "would update $project_id: $agents $claude"
    cleanup_pair
  else
    mv "$agents_tmp" "$agents"
    mv "$claude_tmp" "$claude"
    echo "updated $project_id: $agents $claude"
  fi
done < <(
  awk '
    /^## [^[:space:]]+$/ {
      if (id != "" && path != "") print id "\t" path
      id = substr($0, 4)
      path = ""
      next
    }
    id != "" && /^Path: / { path = substr($0, 7) }
    END { if (id != "" && path != "") print id "\t" path }
  ' "$HUB/ai/project-registry.md"
)
