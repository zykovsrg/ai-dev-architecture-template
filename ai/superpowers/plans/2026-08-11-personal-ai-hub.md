# Personal AI Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, safe, token-efficient `_ai-hub` installation that routes requests between independent projects only after explicit user confirmation while preserving the existing standalone installation.

**Architecture:** Keep `template/` as the standalone product and add a separate `hub-template/` as the hub product. The hub owns common entry rules and routing skills; registered projects retain only project memory. Shell scripts provide deterministic installation, update, validation, and synthetic smoke tests, while all project selection and memory writes remain confirmation-gated agent workflows.

**Tech Stack:** Markdown, YAML-shaped Markdown data files, macOS-compatible Bash 3.2, Git, `rsync`, `awk`, `sed`, `grep`, `find`, and existing repository smoke/consistency scripts.

## Global Constraints

- Hub mode is optional; declining it leaves standalone behavior unchanged.
- Hub mode has one supported AI entry point: `_ai-hub`.
- Do not add semantic search, RAG, embeddings, databases, servers, Obsidian, or mandatory external relationship skills.
- Do not read project memory or code before explicit project confirmation.
- Operate only inside explicitly allowed roots and never scan the full home directory.
- Do not read `.env`, credentials, keychains, backup contents, or unregistered directories for classification.
- Every project has at most one active task; `project-switch` never mutates that task.
- Hub updates preserve registry, cards, signals, allowed roots, active-project state, and all project memory.
- Permanent AI-facing instructions are English; user-facing explanations are Russian.
- Keep `AGENTS.md` and `CLAUDE.md` equal in meaning except tool-specific notes.
- Bash must remain compatible with macOS `/bin/bash` 3.2.
- The first release includes template architecture only. Local `vibecode` migration, archival, and reminders require separate plans.

---

## Planned File Map

### New product template

- `hub-template/AGENTS.md` — compact Codex entry point for global routing.
- `hub-template/CLAUDE.md` — matching Claude Code entry point.
- `hub-template/ai/architecture.md` — hub workflow, precedence, safety, and token-loading rules.
- `hub-template/ai/allowed-roots.md` — user-controlled root allowlist template.
- `hub-template/ai/active-project.md` — last selected project without task content.
- `hub-template/ai/project-registry.md` — compact project index template.
- `hub-template/ai/project-cards/.gitkeep` — card directory holder.
- `hub-template/ai/cross-project-signals.md` — active signal store and schema.
- `hub-template/ai/archive/.gitkeep` — archive holder.
- `hub-template/ai/skills/*/SKILL.md` — five confirmation-gated hub workflows.

### Deterministic scripts and tests

- `scripts/install.sh` — universal mode selection and backward-compatible standalone install.
- `scripts/install-hub.sh` — hub-specific safe installer and allowed-root initialization.
- `scripts/update-installed-architecture.sh` — retain standalone updater behavior.
- `scripts/update-installed-hub.sh` — preview/apply hub protected-file updates while preserving hub memory.
- `scripts/check-hub-registry.sh` — deterministic registry/path/schema validation without project-content reads.
- `scripts/hub-smoke-test.sh` — synthetic routing-boundary, installation, update, and token fixture checks.
- `scripts/check-consistency.sh` — validate hub canonical lists and Codex/Claude parity holders.
- `scripts/smoke-test.sh` — invoke both standalone and hub smoke suites.

### Existing architecture and documentation

- `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, `ai/external-tools.md`, `ai/skills/*` — root working copy updated to document the two product modes.
- `template/AGENTS.md`, `template/CLAUDE.md`, `template/ai/architecture.md`, `template/ai/external-tools.md`, `template/ai/skills/*` — standalone template remains self-contained and advertises the optional hub without depending on it.
- `README.md`, `docs/install.md`, `docs/update.md`, `docs/update-installed-projects.md`, `docs/file-roles.md`, `docs/concepts.md`, `docs/prompts.md`, `docs/start-prompts.md`, `getting-started/getting-started.md` — user instructions for selection, installation, migration boundaries, updates, and daily use.

---

### Task 1: Hub Registry Schema and Read-Only Validator

**Files:**
- Create: `scripts/check-hub-registry.sh`
- Create: `scripts/hub-smoke-test.sh`
- Create: `hub-template/ai/allowed-roots.md`
- Create: `hub-template/ai/active-project.md`
- Create: `hub-template/ai/project-registry.md`
- Create: `hub-template/ai/project-cards/.gitkeep`
- Create: `hub-template/ai/cross-project-signals.md`
- Create: `hub-template/ai/archive/.gitkeep`

**Interfaces:**
- Consumes: a hub directory passed as the first positional argument.
- Produces: `check-hub-registry.sh HUB_DIR`, exit `0` for a valid registry and exit `1` with `ERROR:` lines for invalid roots, duplicate IDs, invalid statuses, missing card paths, or project paths outside allowed roots.

- [ ] **Step 1: Write the first failing registry smoke tests**

Create `scripts/hub-smoke-test.sh` with a temporary hub fixture and explicit assertions:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-hub-smoke.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_contains() { grep -Fq "$2" "$1" || fail "expected '$2' in $1"; }

VALID="$TMP_DIR/valid-hub"
mkdir -p "$VALID/ai/project-cards" "$TMP_DIR/projects/analytics-seo"
printf '%s\n' '# Allowed Roots' '' "- $TMP_DIR/projects" > "$VALID/ai/allowed-roots.md"
printf '%s\n' '# Project Registry' '' \
  '## analytics-seo' \
  'Name: SEO Analytics' \
  'Type: work' \
  'Status: active' \
  "Path: $TMP_DIR/projects/analytics-seo" \
  'Tags: seo, analytics, traffic, leads' \
  'Card: ai/project-cards/analytics-seo.md' > "$VALID/ai/project-registry.md"
printf '%s\n' '# SEO Analytics' '' 'Project ID: analytics-seo' > "$VALID/ai/project-cards/analytics-seo.md"

bash "$ROOT/scripts/check-hub-registry.sh" "$VALID" > "$TMP_DIR/valid.out"
assert_contains "$TMP_DIR/valid.out" 'Registry check passed'

INVALID="$TMP_DIR/invalid-hub"
cp -R "$VALID" "$INVALID"
sed "s#Path: $TMP_DIR/projects/analytics-seo#Path: $TMP_DIR/outside#" \
  "$VALID/ai/project-registry.md" > "$INVALID/ai/project-registry.md"
if bash "$ROOT/scripts/check-hub-registry.sh" "$INVALID" > "$TMP_DIR/invalid.out" 2>&1; then
  fail 'validator accepted project outside allowed roots'
fi
assert_contains "$TMP_DIR/invalid.out" 'outside allowed roots'
```

- [ ] **Step 2: Run the smoke test and verify the validator is missing**

Run: `bash scripts/hub-smoke-test.sh`

Expected: FAIL with `scripts/check-hub-registry.sh: No such file or directory`.

- [ ] **Step 3: Implement the minimal read-only validator**

Create `scripts/check-hub-registry.sh` with Bash 3.2-compatible parsing. Use exact labels (`Path:`, `Status:`, `Card:`), canonicalize existing directories with `cd "$path" && pwd -P`, reject symlink escapes, and never list or read project contents:

```bash
#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${1:-.}"
HUB_DIR="$(cd "$HUB_DIR" && pwd -P)"
ROOTS_FILE="$HUB_DIR/ai/allowed-roots.md"
REGISTRY_FILE="$HUB_DIR/ai/project-registry.md"

die() { echo "ERROR: $*" >&2; exit 1; }
[ -f "$ROOTS_FILE" ] || die "missing $ROOTS_FILE"
[ -f "$REGISTRY_FILE" ] || die "missing $REGISTRY_FILE"

root_contains() {
  local candidate="$1" root canonical_root
  while IFS= read -r root; do
    root="${root#- }"
    [ -d "$root" ] || continue
    canonical_root="$(cd "$root" && pwd -P)"
    case "$candidate/" in "$canonical_root/"*) return 0 ;; esac
  done < <(grep -E '^- /' "$ROOTS_FILE" || true)
  return 1
}

status_ok() {
  case "$1" in active|paused|archived|missing|registration-pending) return 0 ;; esac
  return 1
}

ids=""
current_id=""
while IFS= read -r line; do
  case "$line" in
    '## '*)
      current_id="${line#\#\# }"
      printf '%s\n' "$ids" | grep -Fxq "$current_id" && die "duplicate project ID: $current_id"
      ids="${ids}${current_id}
"
      ;;
    'Status: '*) status_ok "${line#Status: }" || die "invalid status for $current_id" ;;
    'Path: '*)
      path="${line#Path: }"
      if [ -d "$path" ]; then
        canonical_path="$(cd "$path" && pwd -P)"
        root_contains "$canonical_path" || die "project path outside allowed roots: $path"
      fi
      ;;
    'Card: '*) [ -f "$HUB_DIR/${line#Card: }" ] || die "missing card for $current_id" ;;
  esac
done < "$REGISTRY_FILE"

echo "Registry check passed"
```

- [ ] **Step 4: Add the minimal hub memory templates**

Use the exact labels consumed by the validator. Keep `active-project.md` empty by default (`Project ID: none`, `Path: none`, `Confirmation required on new chat: yes`). In `cross-project-signals.md`, document only `ID`, `Created`, `Source project`, `Related projects`, `Kind`, `Summary`, `Status`, optional `Source reference`, and optional clearly labeled hypotheses.

- [ ] **Step 5: Run the focused smoke test**

Run: `bash scripts/hub-smoke-test.sh`

Expected: `Registry check passed` and exit `0`.

- [ ] **Step 6: Commit the schema and validator**

```bash
git add hub-template/ai scripts/check-hub-registry.sh scripts/hub-smoke-test.sh
git commit -m "feat: add hub registry schema and validation"
```

---

### Task 2: Hub Entry Files and Core Architecture

**Files:**
- Create: `hub-template/AGENTS.md`
- Create: `hub-template/CLAUDE.md`
- Create: `hub-template/ai/architecture.md`
- Modify: `scripts/hub-smoke-test.sh`

**Interfaces:**
- Consumes: registry files defined in Task 1.
- Produces: compact Codex/Claude entry rules with equal meaning and a detailed on-demand architecture reference.

- [ ] **Step 1: Add failing parity and size tests**

Append checks that normalize only the tool-specific title and activation paragraph, then compare the files. Enforce a maximum of 120 lines and 6,000 bytes per entry file:

```bash
assert_file() { [ -f "$1" ] || fail "missing file: $1"; }
assert_file "$ROOT/hub-template/AGENTS.md"
assert_file "$ROOT/hub-template/CLAUDE.md"
[ "$(wc -l < "$ROOT/hub-template/AGENTS.md")" -le 120 ] || fail 'hub AGENTS.md too long'
[ "$(wc -c < "$ROOT/hub-template/AGENTS.md")" -le 6000 ] || fail 'hub AGENTS.md too large'
grep -Fq 'explicit confirmation' "$ROOT/hub-template/AGENTS.md" || fail 'missing confirmation gate'
grep -Fq 'allowed roots' "$ROOT/hub-template/AGENTS.md" || fail 'missing allowed-root gate'
```

- [ ] **Step 2: Run the test and verify missing entry files**

Run: `bash scripts/hub-smoke-test.sh`

Expected: FAIL with `missing file: .../hub-template/AGENTS.md`.

- [ ] **Step 3: Write compact entry files**

Both files must state, in English:

- start every real request with project routing unless a project was confirmed in the current chat;
- a remembered project still requires confirmation in a new chat;
- show project ID and exact path before reading it;
- do not read any project memory/code before confirmation;
- do not access unregistered paths or paths outside allowed roots;
- after confirmation, use hub skills against the selected project's memory;
- always show `Project: ...` and `Mode: ...` before project work;
- route detailed procedures to `hub-template/ai/architecture.md` and one matching skill.

- [ ] **Step 4: Write the detailed hub architecture reference**

Include rule precedence, registry/card ownership, confidence levels, project-switch/task-switch separation, local-router behavior, info-update permissions, signal rules, installation/update boundaries, secret exclusions, and context-loading budget. Keep examples synthetic and paths generic.

- [ ] **Step 5: Run parity, size, and registry tests**

Run: `bash scripts/hub-smoke-test.sh`

Expected: PASS.

- [ ] **Step 6: Commit hub entry architecture**

```bash
git add hub-template/AGENTS.md hub-template/CLAUDE.md hub-template/ai/architecture.md scripts/hub-smoke-test.sh
git commit -m "feat: add personal hub entry architecture"
```

---

### Task 3: Project Routing, Registration, Switching, and Maintenance Skills

**Files:**
- Create: `hub-template/ai/skills/project-router/SKILL.md`
- Create: `hub-template/ai/skills/project-switch/SKILL.md`
- Create: `hub-template/ai/skills/project-register/SKILL.md`
- Create: `hub-template/ai/skills/registry-check/SKILL.md`
- Modify: `scripts/hub-smoke-test.sh`

**Interfaces:**
- Consumes: `allowed-roots.md`, `active-project.md`, `project-registry.md`, project cards, and `check-hub-registry.sh`.
- Produces: confirmation-gated procedures with high/medium/low routing outcomes and read allowlists.

- [ ] **Step 1: Add failing structural and safety assertions**

For each skill, assert a `name:` and `description:` frontmatter and required phrases. Example:

```bash
for skill in project-router project-switch project-register registry-check; do
  file="$ROOT/hub-template/ai/skills/$skill/SKILL.md"
  assert_file "$file"
  grep -Fq 'explicit confirmation' "$file" || fail "$skill lacks confirmation rule"
done
grep -Fq 'maximum of three candidates' "$ROOT/hub-template/ai/skills/project-router/SKILL.md" || fail 'router candidate cap missing'
grep -Fq 'must not modify the current task' "$ROOT/hub-template/ai/skills/project-switch/SKILL.md" || fail 'project-switch task isolation missing'
grep -Fq 'direct child directory names only' "$ROOT/hub-template/ai/skills/project-register/SKILL.md" || fail 'registration read boundary missing'
grep -Fq 'read-only until approval' "$ROOT/hub-template/ai/skills/registry-check/SKILL.md" || fail 'maintenance write gate missing'
```

- [ ] **Step 2: Run and verify the skills are absent**

Run: `bash scripts/hub-smoke-test.sh`

Expected: FAIL on the first missing skill.

- [ ] **Step 3: Implement `project-router`**

Define exact phases: read compact index; select at most three candidates; read only candidate cards; compare purpose/tasks/boundaries/relationships; read only related active signals; classify confidence; show reason and exact path; wait. Include expected Russian response templates for one candidate, two candidates, no candidate, rejection, and explicit project naming.

- [ ] **Step 4: Implement `project-switch`**

Require current/new project display, unfinished-task warning, confirmation, canonical path validation, active-project update, project environment check, project `current-task` read, and handoff to `task-intake`. Explicitly forbid pausing, replacing, or editing either project's task.

- [ ] **Step 5: Implement `project-register`**

Allow only direct child names of confirmed roots before registration. Classify likely project/backup/unknown from names and Git-directory presence without reading content. Require approval before reading project context, creating a card, or adding registry data. Never auto-register backups.

- [ ] **Step 6: Implement `registry-check`**

Run the validator, identify missing paths, stale cards/relationships, unregistered direct children, archive candidates, and old signals. Report only; each fix requires approval. A weekly reminder may offer this skill but cannot invoke it automatically.

- [ ] **Step 7: Run skill safety tests**

Run: `bash scripts/hub-smoke-test.sh`

Expected: PASS.

- [ ] **Step 8: Commit routing workflows**

```bash
git add hub-template/ai/skills scripts/hub-smoke-test.sh
git commit -m "feat: add hub routing workflows"
```

---

### Task 4: Info Update, Cross-Project Signals, and Local Router

**Files:**
- Create: `hub-template/ai/skills/info-update/SKILL.md`
- Create: `hub-template/ai/skills/local-router-install/SKILL.md`
- Modify: `hub-template/ai/cross-project-signals.md`
- Modify: `hub-template/ai/architecture.md`
- Modify: `scripts/hub-smoke-test.sh`

**Interfaces:**
- Consumes: pasted temporary meeting text, selected project memories, and signal schema.
- Produces: a review-only proposal grouped by project, followed by approved writes in implementation mode; optional local-router files under `<project>/ai/local-router/`.

- [ ] **Step 1: Add failing behavior assertions**

```bash
INFO="$ROOT/hub-template/ai/skills/info-update/SKILL.md"
LOCAL="$ROOT/hub-template/ai/skills/local-router-install/SKILL.md"
assert_file "$INFO"
assert_file "$LOCAL"
grep -Fq 'Do not save the source transcript by default' "$INFO" || fail 'transcript retention gate missing'
grep -Fq 'Confirm each affected project separately' "$INFO" || fail 'per-project approval missing'
grep -Fq 'must not replace the current task' "$INFO" || fail 'current-task protection missing'
grep -Fq 'at least three stable independent areas' "$LOCAL" || fail 'local-router threshold missing'
grep -Fq 'no separate current task' "$LOCAL" || fail 'local-router task boundary missing'
```

- [ ] **Step 2: Run and verify missing workflow files**

Run: `bash scripts/hub-smoke-test.sh`

Expected: FAIL on missing `info-update/SKILL.md`.

- [ ] **Step 3: Implement `info-update`**

Define the exact output order: meeting summary; affected projects; facts; decisions; current-task refinements; future tasks; signals; hypotheses; uncertain interpretations; per-file proposed edits; per-project confirmation. Map approved writes to existing controlled-memory rules and require `task-switch` or `task-finish` where appropriate.

- [ ] **Step 4: Implement local-router installation**

Require a confirmed active project and architecture-update approval. Create only `ai/local-router/index.md` and confirmed `ai/local-router/areas/<id>.md` files. Do not create another task store, Git repository, or global project card for an area.

- [ ] **Step 5: Verify minimal signal schema**

Assert the template contains no `expected_effect`, `review_after`, or `expires_at` fields and clearly separates optional hypotheses:

```bash
SIGNALS="$ROOT/hub-template/ai/cross-project-signals.md"
grep -Eq 'expected_effect|review_after|expires_at' "$SIGNALS" && fail 'fragile signal field present'
grep -Fq 'Hypotheses (optional)' "$SIGNALS" || fail 'hypothesis separation missing'
```

- [ ] **Step 6: Run focused smoke tests and commit**

Run: `bash scripts/hub-smoke-test.sh`

Expected: PASS.

```bash
git add hub-template/ai scripts/hub-smoke-test.sh
git commit -m "feat: add hub information and local routing workflows"
```

---

### Task 5: Optional Hub Installation

**Files:**
- Modify: `scripts/install.sh`
- Create: `scripts/install-hub.sh`
- Modify: `scripts/hub-smoke-test.sh`
- Modify: `scripts/smoke-test.sh`

**Interfaces:**
- Consumes: `--mode standalone|hub`, target directory, and repeatable `--root DIR` values.
- Produces: backward-compatible standalone installation or a new hub Git working tree with protected files copied and user-memory files initialized only when absent.

- [ ] **Step 1: Add failing installer tests**

Add these cases to `hub-smoke-test.sh`:

```bash
HUB_INSTALL="$TMP_DIR/installed-hub"
PROJECT_ROOT="$TMP_DIR/managed-projects"
mkdir -p "$PROJECT_ROOT/example-project" "$PROJECT_ROOT/example-backup"
bash "$ROOT/scripts/install.sh" --mode hub --root "$PROJECT_ROOT" "$HUB_INSTALL" > "$TMP_DIR/install.out"
assert_file "$HUB_INSTALL/AGENTS.md"
assert_file "$HUB_INSTALL/CLAUDE.md"
assert_file "$HUB_INSTALL/ai/project-registry.md"
assert_contains "$HUB_INSTALL/ai/allowed-roots.md" "$PROJECT_ROOT"
assert_contains "$TMP_DIR/install.out" 'Registration requires confirmation'
grep -Fq 'example-project' "$HUB_INSTALL/ai/project-registry.md" && fail 'installer auto-registered a project'
```

Retain the existing `bash scripts/install.sh "$PROJECT"` smoke case to prove old non-interactive usage still installs standalone mode.

- [ ] **Step 2: Run and verify `--mode` is rejected**

Run: `bash scripts/hub-smoke-test.sh`

Expected: FAIL because current `install.sh` treats `--mode` as the target or reports an unknown option after parsing is introduced.

- [ ] **Step 3: Add backward-compatible option parsing to `install.sh`**

Support:

```text
install.sh [--mode standalone|hub] [--root DIR ...] [TARGET_DIR]
```

Behavior:

- explicit `--mode hub` delegates to `install-hub.sh`;
- explicit `--mode standalone` uses current behavior;
- no mode in a terminal asks in Russian whether to install optional hub;
- no mode in non-interactive execution preserves the current standalone default;
- `--root` is rejected in standalone mode;
- existing files are never overwritten.

- [ ] **Step 4: Implement `install-hub.sh`**

Validate each root exists, canonicalize it with `pwd -P`, reject `/` and the user's home directory as roots, copy `hub-template/` with `rsync --ignore-existing`, append unique roots to `allowed-roots.md`, initialize Git only when `.git` is absent, and print direct child names as unregistered candidates without reading their contents. End with `Registration requires confirmation: run project-register in the hub.`

- [ ] **Step 5: Run standalone and hub install tests**

Run: `bash scripts/smoke-test.sh`

Expected: both `Smoke tests passed.` and `Hub smoke tests passed.`

- [ ] **Step 6: Commit optional installation support**

```bash
git add scripts/install.sh scripts/install-hub.sh scripts/smoke-test.sh scripts/hub-smoke-test.sh
git commit -m "feat: add optional personal hub installation"
```

---

### Task 6: Safe Hub Updates and Standalone-to-Hub Migration Preview

**Files:**
- Create: `scripts/update-installed-hub.sh`
- Modify: `scripts/update-installed-architecture.sh`
- Modify: `scripts/hub-smoke-test.sh`
- Modify: `scripts/smoke-test.sh`

**Interfaces:**
- Consumes: the same `--check`, `--dry-run`, `--apply`, `--commit`, `--source`, `--ref`, and dirty-tree controls as the standalone updater.
- Produces: hub protected-file diffs and updates without changing hub memory; a standalone updater message that offers, but never performs, migration to hub mode.

- [ ] **Step 1: Add failing preservation tests**

Install a fixture hub, write custom registry/card/signal/active-project data, update from the repository, and assert byte-for-byte preservation:

```bash
printf '%s\n' '# Project Registry' '' 'custom registry' > "$HUB_INSTALL/ai/project-registry.md"
printf '%s\n' 'Project ID: custom' > "$HUB_INSTALL/ai/active-project.md"
cp "$HUB_INSTALL/ai/project-registry.md" "$TMP_DIR/registry.before"
cp "$HUB_INSTALL/ai/active-project.md" "$TMP_DIR/active.before"
bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$ROOT" --apply > "$TMP_DIR/update.out"
cmp -s "$TMP_DIR/registry.before" "$HUB_INSTALL/ai/project-registry.md" || fail 'hub update overwrote registry'
cmp -s "$TMP_DIR/active.before" "$HUB_INSTALL/ai/active-project.md" || fail 'hub update overwrote active project'
```

- [ ] **Step 2: Run and verify the hub updater is missing**

Run: `bash scripts/hub-smoke-test.sh`

Expected: FAIL with missing `update-installed-hub.sh`.

- [ ] **Step 3: Implement protected and memory file lists**

Hub protected files are `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, and `ai/skills/**`. Hub memory is `allowed-roots.md`, `active-project.md`, `project-registry.md`, `project-cards/**`, `cross-project-signals.md`, and `archive/**`. Dry-run compares only protected files and reports missing memory templates without overwriting existing files.

- [ ] **Step 4: Add migration preview messaging to the standalone updater**

Add an informational `--offer-hub` option that prints the hub install command and states that conversion of existing projects is separate, previewed, and never removes project entry files automatically. It must not alter current standalone update behavior.

- [ ] **Step 5: Run update preservation and legacy updater tests**

Run: `bash scripts/smoke-test.sh`

Expected: existing standalone checks pass; hub memory preservation checks pass.

- [ ] **Step 6: Commit hub update support**

```bash
git add scripts/update-installed-hub.sh scripts/update-installed-architecture.sh scripts/hub-smoke-test.sh scripts/smoke-test.sh
git commit -m "feat: add safe personal hub updates"
```

---

### Task 7: Scale Fixtures, Forbidden-Read Scenarios, and Consistency Checks

**Files:**
- Modify: `scripts/hub-smoke-test.sh`
- Modify: `scripts/check-consistency.sh`
- Modify: `scripts/check-hub-registry.sh`
- Modify: `scripts/smoke-test.sh`

**Interfaces:**
- Consumes: synthetic registry sizes `5`, `20`, `50`, and `100` and fixture paths containing sentinel secrets.
- Produces: deterministic pass/fail evidence for schema, path boundaries, project count, token-size budget, entry parity, and preservation behavior.

- [ ] **Step 1: Add synthetic registry generation**

Add a Bash function that creates compact entries and cards without real user data:

```bash
generate_registry() {
  local hub="$1" root="$2" count="$3" i id
  printf '%s\n' '# Project Registry' > "$hub/ai/project-registry.md"
  i=1
  while [ "$i" -le "$count" ]; do
    id="fixture-project-$i"
    mkdir -p "$root/$id"
    printf '\n## %s\nName: Fixture %s\nType: work\nStatus: active\nPath: %s/%s\nTags: fixture, area-%s\nCard: ai/project-cards/%s.md\n' \
      "$id" "$i" "$root" "$id" "$i" "$id" >> "$hub/ai/project-registry.md"
    printf '# Fixture %s\n\nProject ID: %s\n\n## Purpose\nSynthetic test project.\n' \
      "$i" "$id" > "$hub/ai/project-cards/$id.md"
    i=$((i + 1))
  done
}
```

- [ ] **Step 2: Add exact size budgets**

For `5`, `20`, `50`, and `100`, run the validator and enforce registry byte ceilings of `2,400`, `9,600`, `24,000`, and `48,000` respectively. Report measured bytes in test output. These ceilings approximate the approved 30–60-token entry budget without requiring a tokenizer dependency.

- [ ] **Step 3: Add forbidden-read sentinels**

Create `.env`, `credentials.txt`, an unregistered folder, and a backup folder containing the marker `MUST_NOT_BE_READ`. Ensure install/validation outputs never contain that marker. Use shell tracing or explicit command scope checks rather than relying on agent claims.

- [ ] **Step 4: Extend consistency checks**

Check:

- root/template standalone canonical blocks remain equal;
- hub `AGENTS.md` and `CLAUDE.md` have semantic parity after allowed tool-name normalization;
- every hub skill listed in hub architecture exists;
- no hub memory file appears in the hub protected update list;
- no standalone controlled-memory file is overwritten by either updater.

- [ ] **Step 5: Run all deterministic checks**

Run:

```bash
bash scripts/check-consistency.sh
bash scripts/smoke-test.sh
git diff --check
```

Expected: all canonical lists consistent, standalone smoke tests pass, hub smoke tests pass, no whitespace errors.

- [ ] **Step 6: Commit scale and safety tests**

```bash
git add scripts/check-consistency.sh scripts/check-hub-registry.sh scripts/hub-smoke-test.sh scripts/smoke-test.sh
git commit -m "test: cover hub scale and safety boundaries"
```

---

### Task 8: Architecture Version, README, and User Instructions

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `ai/architecture.md`
- Modify: `ai/external-tools.md`
- Modify: `ai/skills/environment-check/SKILL.md`
- Modify: `ai/skills/architecture-update/SKILL.md`
- Modify: `template/AGENTS.md`
- Modify: `template/CLAUDE.md`
- Modify: `template/ai/architecture.md`
- Modify: `template/ai/external-tools.md`
- Modify: `template/ai/skills/environment-check/SKILL.md`
- Modify: `template/ai/skills/architecture-update/SKILL.md`
- Modify: `README.md`
- Modify: `docs/install.md`
- Modify: `docs/update.md`
- Modify: `docs/update-installed-projects.md`
- Modify: `docs/file-roles.md`
- Modify: `docs/concepts.md`
- Modify: `docs/prompts.md`
- Modify: `docs/start-prompts.md`
- Modify: `getting-started/getting-started.md`
- Modify: `scripts/check-consistency.sh`
- Modify: `scripts/smoke-test.sh`

**Interfaces:**
- Consumes: all implemented hub commands and schemas from Tasks 1–7.
- Produces: architecture version `7.0`, synchronized standalone rules, complete Russian onboarding, and English technical documentation for both modes.

- [ ] **Step 1: Add failing documentation assertions**

Extend smoke tests to require:

```bash
assert_contains "$ROOT/README.md" 'Personal hub'
assert_contains "$ROOT/README.md" 'Обычная архитектура для одного проекта'
assert_contains "$ROOT/README.md" 'единая точка входа'
assert_contains "$ROOT/docs/install.md" '--mode hub'
assert_contains "$ROOT/docs/update.md" 'update-installed-hub.sh'
assert_contains "$ROOT/docs/file-roles.md" 'Hub-managed project memory'
assert_contains "$ROOT/getting-started/getting-started.md" 'personal hub'
```

- [ ] **Step 2: Run and verify documentation checks fail**

Run: `bash scripts/smoke-test.sh`

Expected: FAIL on the first missing hub instruction.

- [ ] **Step 3: Update architecture rules and version**

Set root and standalone template `ai/architecture.md` to `Version: 7.0`. Add concise entry routing that says the current files describe standalone mode and links users to optional hub installation; do not make standalone depend on hub. Add hub presence/version checks to environment-check without scanning sibling folders.

- [ ] **Step 4: Update README and installation instructions**

In Russian README content, explain in plain language:

- what standalone and personal hub modes are;
- that hub is optional and asked about during first installation;
- that hub mode always starts in `_ai-hub`;
- that project selection always waits for confirmation;
- that existing projects require a previewed migration;
- exact standalone and hub install commands;
- exact update/dry-run commands;
- that README/instructions contain no promise of automatic cleanup or reminders.

- [ ] **Step 5: Update technical docs and prompts**

Keep technical docs in English. Add copyable prompts for install hub, register projects, run registry-check, preview standalone-to-hub conversion, and use info-update. Update file-role tables with separate standalone and hub protected/memory classes.

- [ ] **Step 6: Synchronize root and template copies**

Run exact comparisons after editing:

```bash
cmp AGENTS.md template/AGENTS.md
cmp CLAUDE.md template/CLAUDE.md
cmp ai/architecture.md template/ai/architecture.md
cmp ai/external-tools.md template/ai/external-tools.md
cmp ai/skills/environment-check/SKILL.md template/ai/skills/environment-check/SKILL.md
cmp ai/skills/architecture-update/SKILL.md template/ai/skills/architecture-update/SKILL.md
```

Expected: all commands exit `0`.

- [ ] **Step 7: Run final verification**

```bash
bash scripts/check-consistency.sh
bash scripts/smoke-test.sh
git diff --check
git diff --name-only
```

Expected:

- consistency passes;
- standalone and hub smoke tests pass;
- no whitespace errors;
- changed protected files are exactly those approved by this architecture-update;
- controlled memory changes are limited to `ai/current-task.md` through task-intake and later task progress.

- [ ] **Step 8: Run a manual fixture review**

Use synthetic requests for all 18 scenarios from the design spec. Record only pass/fail and files-read evidence in the plan progress notes; never use real personal project contents.

- [ ] **Step 9: Commit the release documentation and architecture**

```bash
git add AGENTS.md CLAUDE.md ai/architecture.md ai/external-tools.md ai/skills/environment-check/SKILL.md ai/skills/architecture-update/SKILL.md template README.md docs getting-started scripts/check-consistency.sh scripts/smoke-test.sh
git commit -m "feat: release optional personal AI hub architecture"
```

---

## Final Release Gate

- [ ] Run `bash scripts/check-consistency.sh` and confirm success.
- [ ] Run `bash scripts/smoke-test.sh` and confirm both standalone and hub suites pass.
- [ ] Run `git diff --check` and confirm no formatting errors.
- [ ] Run `git status --short` and inspect every changed/untracked path.
- [ ] Confirm no real project, backup, transcript, secret, or absolute personal path was added to fixtures.
- [ ] Confirm no migration, archival, deletion, or reminder automation was performed.
- [ ] Request code review using `superpowers:requesting-code-review`.
- [ ] Present the completed implementation for user review; do not run `task-finish` without confirmation.
