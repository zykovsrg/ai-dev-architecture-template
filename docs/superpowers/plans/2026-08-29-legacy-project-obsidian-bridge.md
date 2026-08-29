# Legacy Project Obsidian Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every registered 7.3 legacy project opened inside the hub discover and scan its own central Obsidian Kanban board without requesting a path.

**Architecture:** A central migration script owns a short, identical Markdown bridge block. It discovers only registered direct-child projects with version 7.3, validates paired entry files before changing them, and updates both files atomically per project. The bridge instructs the agent to derive the hub root, use the existing central scoped sync script and checked-in scope file, and preserve proposal confirmation gates.

**Tech Stack:** Bash, Markdown entry rules, existing `obsidian-task-sync.sh`, Git.

## Global Constraints

- Do not copy sync code or vault configuration into legacy projects.
- Activate only within a validated `_ai-hub` layout and exact registry mapping.
- Use `--project-id <id>` for every scan and apply.
- Use `<hub>/ai/tmp/obsidian-scope.txt` as the validated installed scope file.
- Never write canonical project task records before explicit proposal-hash confirmation.
- Keep standalone behavior outside the hub unchanged.
- Update only projects whose local `ai/architecture.md` declares `Version: 7.3`.

---

### Task 1: Add a failing migration contract test

**Files:**
- Create: `scripts/legacy-hub-obsidian-bridge-test.sh`
- Test: `scripts/legacy-hub-obsidian-bridge-test.sh`

**Interfaces:**
- Consumes: `scripts/install-legacy-hub-obsidian-bridge.sh --hub <absolute-path> --dry-run|--apply`.
- Produces: a repeatable fake hub fixture and `PASS: legacy hub Obsidian bridge contract`.

- [ ] **Step 1: Write the failing test**

Create a temporary hub with `ai/project-registry.md`, `ai/tmp/obsidian-scope.txt`, and three direct-child projects: `legacy-project` at version 7.3 with matching `AGENTS.md` / `CLAUDE.md`; `modern-project` at version 7.4; and `broken-project` at version 7.3 with mismatched entry files. Invoke the missing installer in dry-run and apply modes.

```bash
"$INSTALLER" --hub "$HUB" --dry-run > "$TMP_DIR/dry-run.out"
assert_contains "$TMP_DIR/dry-run.out" 'legacy-project'
assert_not_contains "$TMP_DIR/dry-run.out" 'modern-project'
"$INSTALLER" --hub "$HUB" --apply
assert_contains "$LEGACY/AGENTS.md" '## Hub Obsidian Bridge'
cmp "$LEGACY/AGENTS.md" "$LEGACY/CLAUDE.md"
assert_not_contains "$MODERN/AGENTS.md" '## Hub Obsidian Bridge'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/legacy-hub-obsidian-bridge-test.sh`

Expected: FAIL because `scripts/install-legacy-hub-obsidian-bridge.sh` does not exist.

- [ ] **Step 3: Commit the failing test**

```bash
git add scripts/legacy-hub-obsidian-bridge-test.sh
git commit -m "test: define legacy Obsidian bridge contract"
```

### Task 2: Implement the safe central bridge installer

**Files:**
- Create: `scripts/install-legacy-hub-obsidian-bridge.sh`
- Modify: `scripts/legacy-hub-obsidian-bridge-test.sh`
- Test: `scripts/legacy-hub-obsidian-bridge-test.sh`

**Interfaces:**
- Consumes: `--hub DIR`, `--dry-run` (default), `--apply`.
- Produces: bridge block inserted exactly once in both entry files or a non-zero error with no partial project update.

- [ ] **Step 1: Implement argument and hub validation**

Implement `usage`, `die`, and `canonical_dir`. Require an absolute existing hub Git directory, regular non-symlink `ai/project-registry.md`, and regular `ai/tmp/obsidian-scope.txt`. Reject unknown arguments and missing option values.

```bash
case "$1" in
  --hub) shift; [ "$#" -gt 0 ] || die '--hub requires a directory'; HUB="$1" ;;
  --dry-run) MODE='dry-run' ;;
  --apply) MODE='apply' ;;
  *) die "unknown option: $1" ;;
esac
```

- [ ] **Step 2: Implement registry-driven selection and paired-file checks**

Read project IDs and exact absolute paths from registry headings. For every entry, require its canonical path to equal `<hub>/projects/<id>`, skip non-7.3 projects, and require matching regular `AGENTS.md` / `CLAUDE.md` before replacing either file. Ignore unregistered folders completely.

- [ ] **Step 3: Insert the fixed bridge block idempotently**

Add this block immediately after `## Installation Mode` section, exactly once in both entry files:

```markdown
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
```

Use a sibling temporary file and `mv` only after both rendered entry files pass
the paired equality check. Dry-run prints selected IDs and changed filenames
without writing.

- [ ] **Step 4: Run the focused contract test**

Run: `bash scripts/legacy-hub-obsidian-bridge-test.sh`

Expected: `PASS: legacy hub Obsidian bridge contract`.

- [ ] **Step 5: Commit the installer**

```bash
git add scripts/install-legacy-hub-obsidian-bridge.sh scripts/legacy-hub-obsidian-bridge-test.sh
git commit -m "feat: add legacy Obsidian bridge installer"
```

### Task 3: Roll out the bridge to installed legacy projects

**Files:**
- Modify: `<hub>/projects/<each-7.3-project>/AGENTS.md`
- Modify: `<hub>/projects/<each-7.3-project>/CLAUDE.md`
- Test: `scripts/legacy-hub-obsidian-bridge-test.sh`

**Interfaces:**
- Consumes: verified installer from Task 2 and installed hub registry.
- Produces: matching entry bridge blocks in all eligible legacy projects.

- [ ] **Step 1: Preview exact targets**

Run: `bash scripts/install-legacy-hub-obsidian-bridge.sh --hub /Users/zykovsrg/Documents/vibecode/_ai-hub --dry-run`

Expected: exactly the registered 7.3 projects; no version 7.4 or unregistered directory.

- [ ] **Step 2: Apply the migration**

Run: `bash scripts/install-legacy-hub-obsidian-bridge.sh --hub /Users/zykovsrg/Documents/vibecode/_ai-hub --apply`

Expected: two entry files updated per eligible project and no other files changed.

- [ ] **Step 3: Commit each modified project independently**

For every selected project, verify only `AGENTS.md` and `CLAUDE.md` changed, then commit:

```bash
git -C "/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/<project-id>" add AGENTS.md CLAUDE.md
git -C "/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/<project-id>" commit -m 'chore: add hub Obsidian bridge'
```

- [ ] **Step 4: Run installer test against the installed hub**

Run: `bash scripts/legacy-hub-obsidian-bridge-test.sh`

Expected: `PASS: legacy hub Obsidian bridge contract`.

### Task 4: Verify full behavior and document the migration

**Files:**
- Modify: `ai/changelog.md`
- Modify: `ai/decisions.md`
- Test: `scripts/legacy-hub-obsidian-bridge-test.sh`, `scripts/obsidian-task-sync-test.sh`, `scripts/obsidian-task-sync-watch-test.sh`, `scripts/obsidian-projects-kanban-test.sh`, `scripts/hub-smoke-test.sh`, `scripts/check-consistency.sh`, installed `scripts/check-hub-registry.sh`

**Interfaces:**
- Consumes: migrated entry rules and central scoped sync.
- Produces: verified, durable explanation of direct-project Obsidian behavior.

- [ ] **Step 1: Record the durable hub decision and change summary**

Add an `ai/decisions.md` entry stating that registered legacy projects may use
the central vault only after validating their enclosing hub and exact registry
path; standalone projects never infer a vault. Add a dated `ai/changelog.md`
summary of the 7.3 bridge rollout.

- [ ] **Step 2: Run focused and regression checks**

Run:

```bash
bash scripts/legacy-hub-obsidian-bridge-test.sh
bash scripts/obsidian-task-sync-test.sh
bash scripts/obsidian-task-sync-watch-test.sh
bash scripts/obsidian-projects-kanban-test.sh
bash scripts/hub-smoke-test.sh
bash scripts/check-consistency.sh
bash /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/scripts/check-hub-registry.sh
```

Expected: every command exits 0 and reports its PASS/success marker.

- [ ] **Step 3: Verify a direct-project scan command is usable**

Run a non-writing scan for `zdorove-businki` only after manually editing a
fixture copy of its board, not the live canonical board. Verify its proposal
contains `.project_id == "zdorove-businki"`, has no canonical-record changes
before confirmation, and rejects applying with any other project ID.

- [ ] **Step 4: Commit central documentation and push only on request**

```bash
git add ai/changelog.md ai/decisions.md docs/superpowers/plans/2026-08-29-legacy-project-obsidian-bridge.md
git commit -m "docs: record legacy Obsidian bridge rollout"
```

Do not push until the user explicitly asks.
