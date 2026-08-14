# Knowledge Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local, explicit `knowledge/` library and opt-in quality-review workflow to standalone and hub projects.

**Architecture:** New projects get four empty knowledge categories. Existing hub projects stay unchanged until their owner confirms `hub-knowledge-enable`; legacy standalone migration is out of scope. Markdown remains the source of truth; records and skills load on demand only.

**Tech Stack:** Markdown, Bash 3.2-compatible scripts, existing smoke-test framework.

## Global Constraints

- No index, MCP server, database, cloud service, background scan, or auto-capture.
- A record never crosses project boundaries and never stores secrets.
- Directories: `knowledge/research`, `knowledge/decisions`, `knowledge/risks`, `knowledge/runbooks`.
- Types: `research`, `decision`, `risk`, `runbook`; statuses: `draft`, `verified`, `needs-review`, `stale`, `superseded`.
- Capture, review-result edits, and existing-project enablement require explicit confirmation.
- Normal updater runs must not create or mutate `knowledge/` for existing projects.
- This plan does not migrate legacy standalone installations; that is a separately approved future task.

## File Structure

- Create `template/knowledge/README.md`, `template/knowledge/record-template.md`, and four tracked empty category directories.
- Create `template/ai/skills/hub-knowledge-capture/SKILL.md` and `template/ai/skills/hub-knowledge-review/SKILL.md`.
- Modify template and root `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, and `ai/skills/hub-task-finish/SKILL.md`.
- Create `hub-template/ai/skills/hub-knowledge-enable/SKILL.md`; modify hub entry rules, architecture, and `hub-project-create`.
- Modify `scripts/smoke-test.sh`, `scripts/hub-smoke-test.sh`, `scripts/update-installed-architecture.sh`, and `docs/{file-roles,install,update,concepts}.md`.

---

### Task 1: Standalone scaffold, rules, and skills

**Files:**
- Create: `template/knowledge/**`, `template/ai/skills/hub-knowledge-capture/SKILL.md`, `template/ai/skills/hub-knowledge-review/SKILL.md`
- Modify: `template/AGENTS.md`, `template/CLAUDE.md`, `template/ai/architecture.md`, `template/ai/skills/hub-task-finish/SKILL.md`, `scripts/smoke-test.sh`

**Interfaces:** Produces the canonical four-category scaffold and on-demand standalone workflows.

- [ ] **Step 1: Write failing installation assertions**

In `scripts/smoke-test.sh`, after `scripts/install.sh`, assert the four knowledge directories, `knowledge/README.md`, `knowledge/record-template.md`, and both skills exist.

- [ ] **Step 2: Verify the test fails**

Run: `bash scripts/smoke-test.sh`

Expected: a `FAIL: missing file` or missing-directory assertion for a knowledge path.

- [ ] **Step 3: Add the minimum canonical files**

Create a short README stating that knowledge is local, optional at read time, and not an automatic conversation archive. The record template must contain:

```yaml
type: research
status: draft
created: YYYY-MM-DD
reviewed: YYYY-MM-DD
sources: []
```

and `Statement`, `Evidence`, `Scope`, `Related records`, `Review notes` headings.

- [ ] **Step 4: Implement the two skills and layered rules**

`hub-knowledge-capture` requires active task, selected type/path, and write confirmation. `hub-knowledge-review` checks an explicit record/folder/task-linked set, reports freshness/status/contradictions, and waits for exact edit confirmation. Entry files say `knowledge/` is not default context; detailed architecture defines its relationship to `project-context.md`. `hub-task-finish` offers, never starts, review.

- [ ] **Step 5: Verify and commit**

Run: `bash scripts/check-consistency.sh && bash scripts/smoke-test.sh`

Expected: exit code 0 and `Smoke tests passed.`

```bash
git add template scripts/smoke-test.sh
git commit -m "feat: add standalone knowledge layer"
```

### Task 2: Hub creation and confirmed enablement

**Files:**
- Create: `hub-template/ai/skills/hub-knowledge-enable/SKILL.md`
- Modify: `hub-template/AGENTS.md`, `hub-template/CLAUDE.md`, `hub-template/ai/architecture.md`, `hub-template/ai/skills/hub-project-create/SKILL.md`, `scripts/hub-smoke-test.sh`

**Interfaces:** Consumes the Task 1 directory contract; produces safe hub creation and one-project migration.

- [ ] **Step 1: Write failing hub contracts**

Add `hub-smoke-test.sh` assertions requiring `hub-project-create` to preview/create all four directories and requiring `hub-knowledge-enable` to name a confirmed registered project, exact paths, no pre-confirmation writes, no unrelated reads, and no symlink following.

- [ ] **Step 2: Verify the test fails**

Run: `bash scripts/hub-smoke-test.sh`

Expected: a contract failure mentioning missing knowledge workflow or preview text.

- [ ] **Step 3: Implement hub behavior**

Amend `hub-project-create` preview and procedure to create only the empty scaffold in addition to its current six memory files. `hub-knowledge-enable` previews `knowledge/README.md`, `knowledge/record-template.md`, and the four directories; after exact confirmation it creates only absent scaffold files, never overwriting records.

- [ ] **Step 4: Verify and commit**

Run: `bash scripts/hub-smoke-test.sh && bash scripts/check-consistency.sh && bash scripts/smoke-test.sh`

Expected: all commands exit 0.

```bash
git add hub-template scripts/hub-smoke-test.sh
git commit -m "feat: add hub knowledge enablement"
```

### Task 3: Updater safety and user documentation

**Files:**
- Modify: `scripts/update-installed-architecture.sh`, `scripts/smoke-test.sh`, `docs/file-roles.md`, `docs/install.md`, `docs/update.md`, `docs/concepts.md`

**Interfaces:** Guarantees that a pre-knowledge project remains unchanged by normal architecture updates.

- [ ] **Step 1: Write failing updater non-mutation test**

Create a pre-knowledge fixture in `scripts/smoke-test.sh`; after `update-installed-architecture.sh --apply`, assert `knowledge/` remains absent and task memory remains unchanged.

- [ ] **Step 2: Verify the test fails**

Run: `bash scripts/smoke-test.sh`

Expected: failure from the new non-mutation assertion.

- [ ] **Step 3: Make the updater boundary explicit**

Keep knowledge paths outside `ARCHITECTURE_FILES` and `CONTROLLED_MEMORY_FILES`, and add output that says updating does not enable knowledge in existing projects. Document the separation from `project-context.md`, record vocabulary, explicit capture/review, optional task-finish offer, and confirmation requirement.

- [ ] **Step 4: Verify and commit**

Run: `bash scripts/check-consistency.sh && bash scripts/smoke-test.sh`

Expected: exit code 0.

```bash
git add scripts/update-installed-architecture.sh scripts/smoke-test.sh docs/file-roles.md docs/install.md docs/update.md docs/concepts.md
git commit -m "docs: define knowledge layer lifecycle"
```

### Task 4: Adopt the architecture repository's root copy

**Files:**
- Create: `knowledge/**`, `ai/skills/hub-knowledge-capture/SKILL.md`, `ai/skills/hub-knowledge-review/SKILL.md`
- Modify: `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, `ai/skills/hub-task-finish/SKILL.md`, `ai/project-context.md`

**Interfaces:** Keeps the self-hosting repository aligned with its distributed template.

- [ ] **Step 1: Add the approved root scaffold and rules**

Mirror the Task 1 scaffold, skills, and relevant template wording. In project context add only a short statement that `knowledge/` stores durable evidence; do not duplicate record contents.

- [ ] **Step 2: Verify parity and regression suite**

Run: `diff -ru template/knowledge knowledge && bash scripts/check-consistency.sh && bash scripts/smoke-test.sh`, then confirm the standalone knowledge-capture and knowledge-review skill directories under `template/ai/skills/` still match their root `ai/skills/` counterparts.

Expected: no diff output; both scripts exit 0.

- [ ] **Step 3: Commit adoption**

```bash
git add AGENTS.md CLAUDE.md ai knowledge
git commit -m "chore: adopt knowledge layer in architecture repo"
```

## Plan Self-Review

- Coverage: Tasks 1–2 deliver the scaffold, four types, capture/review, task-finish offer, new-project creation, and confirmed existing-project enablement. Task 3 protects updater behavior and documents it. Task 4 aligns this repository.
- Placeholder scan: no unspecified paths, deferred requirements, or auto-capture behavior remain.
- Consistency: `hub-knowledge-capture`, `hub-knowledge-review`, and `hub-knowledge-enable` have separate, non-overlapping write authority.
