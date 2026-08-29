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

valid_project_id() {
  [[ "$1" =~ ^[a-z0-9][a-z0-9-]*$ ]]
}

normalized_entry() {
  # AGENTS.md and CLAUDE.md may differ in their tool heading and this one
  # exact reciprocal skill-activation rule.
  sed '1d' "$1" \
    | sed 's/point for Codex; `CLAUDE\.md` is the matching Claude Code entry file\./point for <tool>; `<matching-entry-file>` is the matching <matching-tool> entry file./' \
    | sed 's/point for Claude Code; `AGENTS\.md` is the matching Codex entry file\./point for <tool>; `<matching-entry-file>` is the matching <matching-tool> entry file./' \
    | sed "s/Codex does not auto-activate project skills\. Before using a workflow, open its current \`ai\\/skills\\/<name>\\/SKILL\.md\`\. Route by the user's request and the skill's \`name\` and \`description\`; do not load all skills\. Read extra project memory only when the selected task or skill requires it\./<tool> skill activation rule./" \
    | sed "s/Claude Code may auto-activate skills by description\. Before using a workflow, open its current \`ai\\/skills\\/<name>\\/SKILL\.md\`\. Route by the user's request and the skill's \`name\` and \`description\`; do not load all skills\. Read extra project memory only when the selected task or skill requires it\./<tool> skill activation rule./"
}

bridge_block() {
  cat <<'EOF'
## Hub Obsidian Bridge

When this repository is the registered `<project-id>` direct child of a valid
personal AI hub, requests to import updates from Obsidian use the hub's central
vault automatically. Derive `<hub>` from this repository's `../..` parent,
verify its registry maps `<project-id>` to this exact project path, then run:

`bash <hub>/projects/ai-dev-architecture/scripts/obsidian-task-sync.sh scan --project-id <project-id> --hub <hub> --scope <hub>/ai/tmp/obsidian-scope.txt --vault <hub>/projects/ai-dev-architecture/obsidian-vault`

Show the resulting proposal. Apply it only after an explicit confirmation of
its proposal hash, with the same `--project-id`, hub, scope, and vault. If the
hub layout or registry mapping is absent, retain standalone behavior and ask
for a source; never guess a vault path.
EOF
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

has_exact_single_bridge() {
  local entry="$1" count expected actual
  count="$(grep -Fxc '## Hub Obsidian Bridge' "$entry" || true)"
  [ "$count" -eq 1 ] || return 1
  expected="$(bridge_block)"
  actual="$(awk '
    $0 == "## Hub Obsidian Bridge" {
      count++
      if (count == 1) collecting = 1
    }
    collecting {
      if (count == 1 && seen && /^## /) exit
      print
      seen = 1
    }
  ' "$entry")"
  [ "$actual" = "$expected" ]
}

has_valid_entry_pair() {
  local agents="$1" claude="$2"
  [ "$(head -n 1 "$agents")" = '# AI Development Entry Point — Codex' ] || return 1
  [ "$(head -n 1 "$claude")" = '# AI Development Entry Point — Claude Code' ] || return 1
  cmp -s <(normalized_entry "$agents") <(normalized_entry "$claude")
}

is_physical_direct_project_child() {
  local project_id="$1" project_path="$2" projects_path projects_canonical parent_canonical
  valid_project_id "$project_id" || return 1
  projects_path="$HUB/projects"
  [ -d "$projects_path" ] && [ ! -L "$projects_path" ] || return 1
  [ -d "$project_path" ] && [ ! -L "$project_path" ] || return 1
  projects_canonical="$(canonical_dir "$projects_path")" || return 1
  parent_canonical="$(canonical_dir "$(dirname "$project_path")")" || return 1
  [ "$parent_canonical" = "$projects_canonical" ]
}

update_pair_atomically() {
  local agents="$1" agents_tmp="$2" claude="$3" claude_tmp="$4"
  local agents_backup claude_backup
  agents_backup="$(mktemp "${agents}.backup.XXXXXX")" || return 1
  claude_backup="$(mktemp "${claude}.backup.XXXXXX")" || {
    rm -f "$agents_backup"
    return 1
  }
  if ! cp -p "$agents" "$agents_backup" || ! cp -p "$claude" "$claude_backup"; then
    rm -f "$agents_backup" "$claude_backup"
    return 1
  fi
  if ! mv "$agents_tmp" "$agents"; then
    rm -f "$agents_backup" "$claude_backup"
    return 1
  fi
  if ! mv "$claude_tmp" "$claude"; then
    if ! mv "$agents_backup" "$agents"; then
      die "failed to restore $agents after a paired update failure"
    fi
    rm -f "$claude_backup"
    return 1
  fi
  rm -f "$agents_backup" "$claude_backup"
}

scope_contains() {
  grep -Fqx "$1" "$HUB/ai/tmp/obsidian-scope.txt"
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

while IFS= read -r scope_id || [ -n "$scope_id" ]; do
  [ -n "$scope_id" ] || continue
  valid_project_id "$scope_id" || die "invalid project ID in scope: $scope_id"
done < "$HUB/ai/tmp/obsidian-scope.txt"

while IFS=$'\t' read -r project_id registered_path; do
  [ -n "$project_id" ] || continue
  if ! valid_project_id "$project_id"; then
    echo "SKIP: invalid registry project ID: $project_id" >&2
    continue
  fi
  scope_contains "$project_id" || continue

  expected_path="$HUB/projects/$project_id"
  if ! is_physical_direct_project_child "$project_id" "$expected_path"; then
    echo "SKIP: $project_id is not a physical direct child of $HUB/projects" >&2
    continue
  fi
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
  if ! has_valid_entry_pair "$agents" "$claude"; then
    echo "SKIP: $project_id has invalid Codex/Claude headers or entry bodies" >&2
    continue
  fi
  if has_exact_single_bridge "$agents" && has_exact_single_bridge "$claude"; then
    continue
  fi
  if grep -Fqx '## Hub Obsidian Bridge' "$agents" || grep -Fqx '## Hub Obsidian Bridge' "$claude"; then
    echo "SKIP: $project_id has an invalid bridge block" >&2
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
    if ! update_pair_atomically "$agents" "$agents_tmp" "$claude" "$claude_tmp"; then
      cleanup_pair
      echo "SKIP: $project_id could not be updated atomically; original pair restored" >&2
      continue
    fi
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
