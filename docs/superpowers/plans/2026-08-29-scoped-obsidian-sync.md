# Scoped Obsidian Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restrict Obsidian proposal scanning and applying to one confirmed hub project.

**Architecture:** The task synchronizer receives `--project-id` for `scan` and `apply`. It validates that ID before loading board or task inputs, narrows manifest reads to the matching board and tasks, and binds a proposal to that one ID. Hub workflow instructions derive the central vault from the confirmed hub root and never request a project-local vault path.

**Tech Stack:** Bash, jq, Markdown contract tests.

## Global Constraints

- The canonical task records remain unchanged until explicit proposal confirmation.
- The central vault is `<hub>/projects/ai-dev-architecture/obsidian-vault`.
- A selected-project scan must not hash or parse any other project's board or task files.
- Existing vault-level `status` and `dismiss` commands remain unchanged.

---

### Task 1: Add a scoped synchronizer contract

**Files:**

- Modify: `scripts/obsidian-task-sync-test.sh`
- Modify: `scripts/obsidian-task-sync.sh`

- [ ] **Step 1: Write failing tests**

Add a `scan --project-id ai-dev-architecture` fixture after both boards are
edited. Assert the proposal contains only `ai-dev-architecture`, the second
board is not hashed through the test `shasum` wrapper, and
`apply --project-id extra-project` rejects the pending proposal.

- [ ] **Step 2: Verify the test fails**

Run: `bash scripts/obsidian-task-sync-test.sh`

Expected: failure because `--project-id` is not accepted.

- [ ] **Step 3: Implement the selector**

Parse `--project-id`, require it for `scan` and `apply`, validate it
against registry and scope, and filter project-board and task manifest entries
before any board or source hash/read. Require the proposal's board hash and
operations to name only the selected project.

- [ ] **Step 4: Verify the test passes**

Run: `bash scripts/obsidian-task-sync-test.sh`

Expected: `PASS: Obsidian task sync contract`.

### Task 2: Make the central vault discoverable in hub workflows

**Files:**

- Modify: `hub-template/ai/architecture.md`
- Modify: `hub-template/ai/skills/hub-info-update/SKILL.md`
- Modify: `hub-template/ai/skills/hub-task-intake/SKILL.md`
- Modify: `hub-template/ai/skills/hub-task-switch/SKILL.md`
- Modify: `hub-template/ai/skills/hub-task-finish/SKILL.md`
- Modify: `scripts/smoke-test.sh`

- [ ] **Step 1: Keep the smoke assertion failing**

The existing new assertion requires `central Obsidian vault` in the shared
workflows and `Central Obsidian Projection` in the architecture.

- [ ] **Step 2: Add the minimal shared instructions**

Document the central vault, selected board path, mandatory selected project ID,
and proposal-only confirmation boundary. Do not introduce a per-project vault
setting.

- [ ] **Step 3: Verify the hub contract**

Run: `bash scripts/smoke-test.sh`

Expected: `PASS: smoke test`.

### Task 3: Verify, deploy, and preserve the fix

**Files:**

- Modify: live hub files through `scripts/update-installed-hub.sh`

- [ ] **Step 1: Run focused and complete checks**

Run: `bash scripts/obsidian-task-sync-test.sh`, `bash
scripts/obsidian-projects-kanban-test.sh`, `bash scripts/hub-smoke-test.sh`,
`bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, and
`git diff --check`.

- [ ] **Step 2: Apply the hub update**

Preview and then apply `scripts/update-installed-hub.sh` to the confirmed hub.
Run `bash scripts/check-hub-registry.sh` in the hub afterwards.

- [ ] **Step 3: Commit and push**

Commit the implementation and update commits, push `main`, and confirm clean
local and remote-tracking status.
