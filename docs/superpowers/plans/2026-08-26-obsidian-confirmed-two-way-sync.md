# Obsidian Confirmed Two-Way Task Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Automatically refresh generated Obsidian views after architecture task writes and make Obsidian card edits confirmable changes to canonical task records.

**Architecture:** ai/ remains canonical. The generator gives every card an immutable task ID and stores source fingerprints in manifest v3. A separate sync script turns a board delta into a local proposal, validates it at application, updates only the named records, then calls the guarded generator refresh. An optional user-level launchd timer only scans; it never applies a change.

**Tech Stack:** Bash, Awk, shasum, jq, macOS launchd, shell contract tests.

## Global Constraints

- Only ai/current-task.md, ai/future-tasks.md, and ai/paused-tasks.md are canonical task records.
- Regeneration writes only Tasks-Kanban.md, Projects-Overview.md, and AI-Architecture.manifest.json.
- Existing cards are matched only by immutable ID, never title.
- Obsidian-originated changes require an explicit, fresh proposal-hash confirmation.
- Stale, missing, duplicate, ambiguous, and unsupported edits are blocked without guessing.
- Runtime state and watcher logs are local-only and ignored by Git.
- No new component reads project code, knowledge, secrets, network, or Calendar data.

---

## File structure

| File | Responsibility |
| --- | --- |
| scripts/generate-obsidian-projects-kanban.sh | Render IDs, manifest v3, and a protected architecture refresh. |
| scripts/obsidian-task-sync.sh | Scan, show, dismiss, and apply an Obsidian proposal. |
| scripts/obsidian-task-sync-watch.sh | One debounced, non-writing scan for the local timer. |
| scripts/install-obsidian-task-sync.sh | Preview, install, status, and uninstall the user-level timer. |
| scripts/obsidian-projects-kanban-test.sh | Generated view and trusted-refresh contract. |
| scripts/obsidian-task-sync-test.sh | Proposal, apply, stale-state, and watcher contract. |
| template/ai/*.md, hub task skills, user docs | Task-ID schema and directional rules. |

## Task 1: Add stable task IDs and manifest v3

**Files:**

- Modify: scripts/generate-obsidian-projects-kanban.sh
- Modify: scripts/obsidian-projects-kanban-test.sh

**Interfaces:**

- Future IDs are their existing FT-YYYYMMDD-NNN heading.
- Current and paused tasks provide exactly one Task ID: TASK-... field.
- Manifest v3 has tasks entries containing task_id, project_id, source_file, and source_sha256.

- [ ] **Step 1: Write failing contract assertions**

Add fixture records:

~~~bash
$'Status: active\nTask ID: TASK-20260826-001\ndue: 2026-08-26\n\n## Goal\n\nCurrent architecture task'
$'### 2026-08-20 — Paused task\n\nTask ID: TASK-20260820-001\n\nStatus: paused'
~~~

Assert preview output contains:

~~~bash
assert_contains "$TMP_DIR/preview.txt" '<!-- ai-task-id: TASK-20260826-001 -->'
assert_contains "$TMP_DIR/preview.txt" '<!-- ai-task-id: FT-20260826-001 -->'
assert_contains "$TMP_DIR/preview.txt" '<!-- ai-task-id: TASK-20260820-001 -->'
assert_contains "$TMP_DIR/preview.txt" '"format_version": 3'
~~~

- [ ] **Step 2: Run the focused test**

Run: bash scripts/obsidian-projects-kanban-test.sh

Expected: FAIL because renderer and manifest v2 do not contain stable IDs.

- [ ] **Step 3: Implement ID-aware parsing and rendering**

Replace the parallel record setup with:

~~~bash
TASK_IDS=() TASK_COLUMNS=() TASK_TITLES=() TASK_PROJECTS=() TASK_DUES=() TASK_DONE=()
add_task() {
  TASK_IDS+=("$1"); TASK_COLUMNS+=("$2"); TASK_TITLES+=("$3")
  TASK_PROJECTS+=("$4"); TASK_DUES+=("$5"); TASK_DONE+=("$6")
}
~~~

Make future_records return ID, status, title, due; make paused_records return ID and title; add a current-ID parser. Refuse a renderable current or paused record with absent/duplicate ID. Render:

~~~bash
printf '  - project: %s\n' "$task_project"
printf '  <!-- ai-task-id: %s -->\n' "$task_id"
~~~

Create manifest v3 task entries with ID, project ID, source path, and source hash. Reject v2 manifests as requiring a fresh confirmed rebuild.

- [ ] **Step 4: Verify and commit**

Run: bash scripts/obsidian-projects-kanban-test.sh

Expected: PASS: Obsidian task Kanban and project overview contract.

~~~bash
git add scripts/generate-obsidian-projects-kanban.sh scripts/obsidian-projects-kanban-test.sh
git commit -m "feat: add stable IDs to generated task cards"
~~~

## Task 2: Permit safe architecture-originated refresh

**Files:**

- Modify: scripts/generate-obsidian-projects-kanban.sh
- Modify: scripts/obsidian-projects-kanban-test.sh

**Interfaces:**

- --refresh-from-architecture requires --write.
- It bypasses only the interactive write-confirmation flag, never manifest validation.

- [ ] **Step 1: Write the failing test**

After a successful generated write, change a canonical fixture title, then run:

~~~bash
"$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" \
  --write --refresh-from-architecture > "$TMP_DIR/refresh.out"
~~~

Assert the board contains the changed title. Append manual task edit to the board and assert the same refresh fails with proposal pending: manual task board edit detected.

- [ ] **Step 2: Run the test**

Run: bash scripts/obsidian-projects-kanban-test.sh

Expected: FAIL with an unknown-flag or usage error.

- [ ] **Step 3: Implement the guarded flag**

Add:

~~~bash
--refresh-from-architecture) REFRESH_FROM_ARCHITECTURE=1; shift;;
~~~

Require MODE=write. Permit write if CONFIRM=1 or REFRESH_FROM_ARCHITECTURE=1. Do not alter the manifest hash comparisons: a manual board edit must still block automatic replacement.

- [ ] **Step 4: Verify and commit**

Run: bash scripts/obsidian-projects-kanban-test.sh

Expected: PASS.

~~~bash
git add scripts/generate-obsidian-projects-kanban.sh scripts/obsidian-projects-kanban-test.sh
git commit -m "feat: allow guarded architecture board refresh"
~~~

## Task 3: Create a non-writing Obsidian proposal scanner

**Files:**

- Create: scripts/obsidian-task-sync.sh
- Create: scripts/obsidian-task-sync-test.sh

**Interfaces:**

- scan --hub ABS --scope ABS --vault ABS creates a local proposal only.
- status --vault ABS prints the exact diff and proposal hash.
- dismiss --vault ABS removes only .ai-architecture-sync/pending-proposal.json.

- [ ] **Step 1: Write failing fixture cases**

Generate a fixture board, then separately rename a known-ID card, move it from Ideas to Ready, change its date, and create a card with a valid project: line. For each run scan and assert:

~~~bash
assert_file "$VAULT/.ai-architecture-sync/pending-proposal.json"
assert_contains "$PROPOSAL" '"operation": "rename"'
assert_contains "$PROPOSAL" '"operation": "set_status"'
assert_contains "$PROPOSAL" '"operation": "set_due"'
assert_contains "$PROPOSAL" '"operation": "create_future"'
~~~

Record source hashes before scanning and assert they are unchanged. Add missing-ID, duplicate-ID, unknown-column, and unknown-project cases that produce "state": "blocked".

- [ ] **Step 2: Run the test**

Run: bash scripts/obsidian-task-sync-test.sh

Expected: FAIL because the sync command does not exist.

- [ ] **Step 3: Implement scanner and proposal format**

Implement exactly these command boundaries:

~~~bash
scan()    { require_safe_paths; parse_cards; diff_cards; write_proposal; }
status()  { require_safe_vault; jq -e . "$PROPOSAL"; }
dismiss() { require_safe_vault; rm -f -- "$PROPOSAL"; }
~~~

Use jq -n for a proposal with proposal_sha256, board hash, manifest hash, affected source hashes, and operations. Accept only existing board columns. Match a known card only by its exact HTML ID comment. A new card must map to exactly one registered project by its project line. Scanner code must not write below $HUB/projects/*/ai.

- [ ] **Step 4: Verify and commit**

Run: bash scripts/obsidian-task-sync-test.sh

Expected: PASS: Obsidian confirmed task sync contract.

~~~bash
git add scripts/obsidian-task-sync.sh scripts/obsidian-task-sync-test.sh
git commit -m "feat: propose Obsidian task board changes"
~~~

## Task 4: Apply a specifically confirmed proposal

**Files:**

- Modify: scripts/obsidian-task-sync.sh
- Modify: scripts/obsidian-task-sync-test.sh

**Interfaces:**

- apply --hub ABS --scope ABS --vault ABS --confirm-proposal SHA256 is the sole reverse-sync writer.
- On success it updates named canonical task files, refreshes the three views, and clears the proposal.

- [ ] **Step 1: Add failing apply and stale tests**

Get the hash using jq -r '.proposal_sha256' "$PROPOSAL", call apply, and assert the specific canonical change plus regenerated board. In separate fixtures edit a canonical source or board after scan; expect proposal is stale, retained proposal, and no additional source modification.

- [ ] **Step 2: Run the test**

Run: bash scripts/obsidian-task-sync-test.sh

Expected: FAIL because apply does not exist.

- [ ] **Step 3: Implement transactional apply**

Use this sequence:

~~~bash
require_safe_paths
load_proposal
[ "$CONFIRM_PROPOSAL" = "$(jq -r '.proposal_sha256' "$PROPOSAL")" ] || die 'confirmation does not match proposal'
verify_board_hash; verify_manifest_hash; verify_every_affected_source_hash
apply_operations_to_temporary_files; validate_temporary_records
replace_named_source_files
"$GENERATOR" --hub "$HUB" --scope "$SCOPE" --vault "$VAULT" --write --refresh-from-architecture
rm -f -- "$PROPOSAL"
~~~

Support rename, due date, valid new future task, and supported status moves. Promotion to Active pauses the existing active task and makes the promoted task current in one transaction. Refuse deletion and blocked operations.

- [ ] **Step 4: Verify and commit**

Run: bash scripts/obsidian-task-sync-test.sh && bash scripts/obsidian-projects-kanban-test.sh

Expected: both PASS.

~~~bash
git add scripts/obsidian-task-sync.sh scripts/obsidian-task-sync-test.sh
git commit -m "feat: apply confirmed Obsidian task proposals"
~~~

## Task 5: Add optional local detection and integrate workflows

**Files:**

- Create: scripts/obsidian-task-sync-watch.sh
- Create: scripts/install-obsidian-task-sync.sh
- Modify: .gitignore
- Modify: scripts/obsidian-task-sync-test.sh
- Modify: template/ai/current-task.md
- Modify: template/ai/paused-tasks.md
- Modify: hub-template/ai/skills/hub-task-intake/SKILL.md
- Modify: hub-template/ai/skills/hub-task-switch/SKILL.md
- Modify: hub-template/ai/skills/hub-task-finish/SKILL.md
- Modify: docs/concepts.md, docs/install.md, docs/update.md, scripts/smoke-test.sh

**Interfaces:**

- Watch command: obsidian-task-sync-watch.sh --hub ABS --scope ABS --vault ABS --once.
- Install command has --preview|--install|--status|--uninstall; install and uninstall each require a matching explicit confirmation flag.

- [ ] **Step 1: Write failing watcher, template, and docs contracts**

For a changed board, watch --once must create a proposal but leave sources unchanged. With a matching board it creates no proposal. With refresh.lock present it exits before scanning. Add smoke assertions for Task ID: TASK-YYYYMMDD-NNN in both templates and the trusted/confirmed direction distinction in hub skills and documentation.

- [ ] **Step 2: Run test suite**

Run:

~~~bash
bash scripts/obsidian-task-sync-test.sh
bash scripts/smoke-test.sh
~~~

Expected: failure because watcher, installer, templates, and instructions are not yet updated.

- [ ] **Step 3: Implement optional watcher and workflow hook**

Make watcher --once do exactly:

~~~bash
require_safe_vault
[ -e "$RUNTIME/refresh.lock" ] && exit 0
"$SYNC" scan --hub "$HUB" --scope "$SCOPE" --vault "$VAULT"
~~~

Installer preview prints the user plist; install uses StartInterval 10 and requires --confirm-launchd-install; uninstall requires --confirm-launchd-uninstall. Add .ai-architecture-sync/ to .gitignore. Add Task ID fields below each template status. In each hub task workflow, after an approved selected-project task write, invoke the guarded refresh; if manifest validation finds an Obsidian edit, report the pending proposal and do not overwrite it.

- [ ] **Step 4: Document use and verify the full change**

Document scan, status, apply --confirm-proposal, watcher preview/install/status/uninstall, and the separate confirmation boundary. Run:

~~~bash
bash scripts/obsidian-projects-kanban-test.sh
bash scripts/obsidian-task-sync-test.sh
bash scripts/smoke-test.sh
git diff --check
~~~

Expected: all tests print PASS and the final command prints nothing.

- [ ] **Step 5: Commit integration**

~~~bash
git add scripts template/ai/current-task.md template/ai/paused-tasks.md hub-template/ai/skills \
  docs/concepts.md docs/install.md docs/update.md .gitignore
git commit -m "feat: add confirmed Obsidian task synchronization"
~~~

## Task 6: Review and release the live vault separately

**Files:**

- Verify: all files changed in Tasks 1–5

- [ ] **Step 1: Run final checks**

~~~bash
git status --short
git diff --check HEAD~5..HEAD
bash scripts/obsidian-projects-kanban-test.sh
bash scripts/obsidian-task-sync-test.sh
bash scripts/smoke-test.sh
~~~

Expected: clean status, no whitespace errors, and three PASS results.

- [ ] **Step 2: Check hard boundaries**

~~~bash
rg -n 'curl|http|https|Calendar|knowledge|project code' \
  scripts/obsidian-task-sync.sh scripts/obsidian-task-sync-watch.sh \
  scripts/install-obsidian-task-sync.sh
~~~

Expected: no executable network, Calendar, knowledge, or project-code access.

- [ ] **Step 3: Request separate live-vault approval**

Show a preview and diff for exactly:

~~~text
obsidian-vault/Obsidian/Tasks-Kanban.md
obsidian-vault/Obsidian/Projects-Overview.md
obsidian-vault/Obsidian/AI-Architecture.manifest.json
~~~

Do not write these files or install the watcher until the user separately confirms the exact operation.

