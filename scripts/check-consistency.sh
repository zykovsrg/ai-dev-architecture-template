#!/usr/bin/env bash
# Verify that every canonical list (wrapped in <!-- canon:NAME --> markers)
# holds the same ordered set of file paths across all files that contain it.
# macOS bash 3.2 compatible: no mapfile, no associative arrays.
set -euo pipefail

ROOT="$(cd "${1:-$(dirname "$0")/..}" && pwd)"
cd "$ROOT"

assistant_workflow_guardrail_check() {
  local file="scripts/assistant-workflows.sh" skill="hub-template/ai/skills/hub-workflows/SKILL.md" source rule found=0
  if [ ! -f "$file" ]; then
    echo "MISSING [assistant workflow guardrails] — $file"
    return 1
  fi
  source="$(awk ' /^[[:space:]]*#/ { next } { sub(/[[:space:]]+#.*/, ""); print } ' "$file")"
  grep -Fq 'rar export --minutes' <<<"$source" || { echo 'MISSING [assistant workflow guardrails] — rar export --minutes'; return 1; }
  grep -Fq -- '--json' <<<"$source" || { echo 'MISSING [assistant workflow guardrails] — --json'; return 1; }
  grep -Fq 'rar status' <<<"$source" || { echo 'MISSING [assistant workflow guardrails] — rar status'; return 1; }
  grep -Fq 'Read-only workflow: no changes were made.' <<<"$source" || { echo 'MISMATCH [assistant workflow guardrails] — exact no-changes line'; return 1; }
  if grep -E '(^|[[:space:]])(calendar[ -]?mcp|obsidian-vault|rar[[:space:]]+(pause|resume|install))([[:space:]]|$)' <<<"$source" >/dev/null; then
    echo 'MISMATCH [assistant workflow guardrails] — forbidden executable path'
    return 1
  fi
  while IFS= read -r line; do
    case "$line" in *'--write|--apply)'*) ;; *) echo 'MISMATCH [assistant workflow guardrails] — executable --write/--apply path'; return 1 ;; esac
  done < <(grep -E '(^|[[:space:]])(--write|--apply)([[:space:]]|$)' <<<"$source" || true)
  for rule in hub-template/AGENTS.md hub-template/CLAUDE.md hub-template/ai/architecture.md; do
    if grep -Fq '`hub-workflows`' "$rule"; then found=1; break; fi
  done
  [ "$found" -eq 1 ] || { echo 'MISSING [assistant workflow guardrails] — literal `hub-workflows` hub rule'; return 1; }
  [ -f "$skill" ] || { echo "MISSING [assistant workflow guardrails] — $skill"; return 1; }
  grep -Fqx 'name: hub-workflows' "$skill" \
    || { echo 'MISMATCH [assistant workflow guardrails] — hub-workflows skill name'; return 1; }
  grep -Fq 'Never write or apply a proposal automatically' "$skill" \
    || { echo 'MISMATCH [assistant workflow guardrails] — no-auto-write rule'; return 1; }
  echo 'OK [assistant workflow guardrails] — executable source and hub rule'
}

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

normalize_hub_entry() {
  sed -E \
    -e 's/Personal AI Hub — (Codex|Claude Code)/Personal AI Hub — TOOL/g' \
    -e 's/(Codex|Claude Code)/TOOL/g' \
    -e 's/(AGENTS|CLAUDE)\.md/ENTRY.md/g' \
    "$1"
}

extract_array() {
  awk -v name="$2" '
    $0 ~ "^" name "=\\(" { in_array=1; next }
    in_array && /^\)/ { exit }
    in_array && match($0, /"[^"]+"/) {
      print substr($0, RSTART + 1, RLENGTH - 2)
    }
  ' "$1"
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

if [ -f AGENTS.md ] && [ -f CLAUDE.md ] && [ -f ai/architecture.md ]; then
  standalone_base="."
  standalone_source="root local files"
elif [ -f template/AGENTS.md ] && [ -f template/CLAUDE.md ] && [ -f template/ai/architecture.md ]; then
  standalone_base="template"
  standalone_source="template (root local files absent)"
else
  echo "MISSING [standalone canonical blocks] — no complete root or template holder set"
  fail=1
  standalone_base=""
fi

if [ -n "$standalone_base" ]; then
  standalone_ok=1
  for marker in $MARKERS; do
    standalone_ref="$(extract_block "$standalone_base/AGENTS.md" "$marker")"
    for holder in "$standalone_base/CLAUDE.md" "$standalone_base/ai/architecture.md"; do
      if [ "$(extract_block "$holder" "$marker")" != "$standalone_ref" ]; then
        echo "MISMATCH [standalone canonical blocks] — $holder differs for $marker"
        fail=1
        standalone_ok=0
      fi
    done
  done
  [ "$standalone_ok" -eq 0 ] \
    || echo "OK [standalone canonical blocks] — source: $standalone_source"
fi

if [ ! -f hub-template/AGENTS.md ] || [ ! -f hub-template/CLAUDE.md ]; then
  echo "MISSING [hub entry parity]"
  fail=1
elif cmp -s <(normalize_hub_entry hub-template/AGENTS.md) \
  <(normalize_hub_entry hub-template/CLAUDE.md); then
  echo "OK [hub entry parity] — equal after tool-name normalization"
else
  echo "MISMATCH [hub entry parity] — semantic content differs"
  fail=1
fi

hub_skill_ok=1
hub_skill_count=0
checked_hub_skills=""
HUB_REQUIRED_SKILLS="hub-project-router hub-project-switch hub-project-register hub-project-create hub-project-migrate hub-registry-check hub-info-update hub-local-router-install hub-environment-check hub-task-intake hub-task-switch hub-task-finish hub-knowledge-enable hub-knowledge-capture hub-knowledge-review hub-workflows"
if [ ! -f hub-template/ai/architecture.md ]; then
  echo "MISSING [hub skill references] — hub architecture absent"
  fail=1
  hub_skill_ok=0
fi
for skill in $HUB_REQUIRED_SKILLS $(sed -n -E 's/.*`([a-z][a-z0-9-]*)` workflow.*/\1/p' hub-template/ai/architecture.md | sort -u); do
  case " $checked_hub_skills " in *" $skill "*) continue ;; esac
  checked_hub_skills="$checked_hub_skills $skill"
  hub_skill_count=$((hub_skill_count + 1))
  if [ ! -f "hub-template/ai/skills/$skill/SKILL.md" ]; then
    echo "MISSING [hub skill references] — $skill"
    fail=1
    hub_skill_ok=0
  fi
done
[ "$hub_skill_ok" -eq 0 ] \
  || echo "OK [hub skill references] — $hub_skill_count declared skills exist"

hub_prefix_ok=1
if [ -d hub-template/ai/skills ]; then
  while IFS= read -r skill_dir; do
    case "$(basename "$skill_dir")" in
      hub-*) ;;
      *)
        echo "MISMATCH [hub skill prefix] — $skill_dir must be named hub-*"
        fail=1
        hub_prefix_ok=0
        ;;
    esac
  done < <(find hub-template/ai/skills -mindepth 1 -maxdepth 1 -type d | sort)
fi
[ "$hub_prefix_ok" -eq 0 ] \
  || echo "OK [hub skill prefix] — every hub skill directory is prefixed"

# Reverse of the [hub skill references] check above: that one reads the
# hardcoded HUB_REQUIRED_SKILLS list and proves declared -> exists. This proves
# exists -> declared, so a skill cannot be added without naming it in the rules.
hub_naming_ok=1
hub_rule_files="hub-template/CLAUDE.md hub-template/AGENTS.md hub-template/ai/architecture.md"
if [ -d hub-template/ai/skills ]; then
  while IFS= read -r skill_dir; do
    skill_name="$(basename "$skill_dir")"
    if ! grep -Fq "\`$skill_name\`" $hub_rule_files; then
      echo "UNNAMED [hub skill naming] — $skill_name is named in no hub rule file"
      fail=1
      hub_naming_ok=0
    fi
  done < <(find hub-template/ai/skills -mindepth 1 -maxdepth 1 -type d | sort)
fi
[ "$hub_naming_ok" -eq 0 ] \
  || echo "OK [hub skill naming] — every hub skill is named in a rule file"

hub_protected="$(extract_array scripts/update-installed-hub.sh PROTECTED_FILES)"
if [ -d hub-template/ai/skills ]; then
  while IFS= read -r protected_file; do
    hub_protected="${hub_protected}${hub_protected:+$'\n'}${protected_file#hub-template/}"
  done < <(find hub-template/ai/skills -type f | sort)
fi

hub_memory="$(extract_array scripts/update-installed-hub.sh MEMORY_FILES)"
for memory_dir in ai/project-cards ai/archive; do
  if [ -d "hub-template/$memory_dir" ]; then
    while IFS= read -r memory_file; do
      hub_memory="${hub_memory}${hub_memory:+$'\n'}${memory_file#hub-template/}"
    done < <(find "hub-template/$memory_dir" -type f | sort)
  fi
done

hub_classes_ok=1
while IFS= read -r memory_file; do
  [ -n "$memory_file" ] || continue
  if printf '%s\n' "$hub_protected" | grep -Fxq "$memory_file"; then
    echo "OVERLAP [hub update classes] — $memory_file is both protected and memory"
    fail=1
    hub_classes_ok=0
  fi
done <<EOF
$hub_memory
EOF
[ "$hub_classes_ok" -eq 0 ] \
  || echo "OK [hub update classes] — protected files exclude hub memory"

# path_is_or_contains LIST ENTRY -> 0 if ENTRY exactly equals a line in LIST,
# or ENTRY is a directory prefix of a line in LIST (line starts with "ENTRY/").
path_is_or_contains() {
  local list="$1" entry="$2" line
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    case "$line" in
      "$entry") return 0 ;;
      "$entry"/*) return 0 ;;
    esac
  done <<EOF
$list
EOF
  return 1
}

hub_superseded="$(extract_array scripts/update-installed-hub.sh SUPERSEDED_PATHS)"
hub_superseded_ok=1
while IFS= read -r superseded_path; do
  [ -n "$superseded_path" ] || continue
  if path_is_or_contains "$hub_memory" "$superseded_path" \
    || path_is_or_contains "$hub_protected" "$superseded_path"; then
    echo "OVERLAP [hub superseded paths] — $superseded_path is hub memory or a protected file"
    fail=1
    hub_superseded_ok=0
  fi
done <<EOF
$hub_superseded
EOF
[ "$hub_superseded_ok" -eq 0 ] \
  || echo "OK [hub superseded paths] — removals exclude hub memory and protected files"

standalone_architecture="$(extract_array scripts/update-installed-architecture.sh ARCHITECTURE_FILES)"
standalone_memory="$(extract_block "$standalone_base/AGENTS.md" canon:controlled-memory)"
standalone_boundaries_ok=1
while IFS= read -r memory_file; do
  [ -n "$memory_file" ] || continue
  if printf '%s\n' "$standalone_architecture" | grep -Fxq "$memory_file" \
    || printf '%s\n' "$hub_protected" | grep -Fxq "$memory_file"; then
    echo "OVERLAP [standalone memory updater boundaries] — $memory_file is updater-protected"
    fail=1
    standalone_boundaries_ok=0
  fi
done <<EOF
$standalone_memory
EOF
for updater in scripts/update-installed-architecture.sh scripts/update-installed-hub.sh; do
  if ! grep -Fq 'for_each_memory_file copy_missing_memory_file' "$updater"; then
    echo "MISMATCH [standalone memory updater boundaries] — $updater lacks create-only memory handling"
    fail=1
    standalone_boundaries_ok=0
  fi
done
[ "$standalone_boundaries_ok" -eq 0 ] \
  || echo "OK [standalone memory updater boundaries] — neither updater overwrites controlled memory"

assistant_workflow_guardrail_check || fail=1

if [ "$fail" -ne 0 ]; then
  echo ""
  echo "Consistency check FAILED. Make the marked lists identical (same paths, same order)."
  exit 1
fi
echo ""
echo "All canonical lists are consistent."
