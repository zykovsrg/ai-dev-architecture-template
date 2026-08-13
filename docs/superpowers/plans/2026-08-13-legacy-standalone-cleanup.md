# Legacy Standalone Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, separately confirmed deletion of obsolete standalone rules after a project is migrated and registered in the portable hub.

**Architecture:** Extend the existing `project-migrate` workflow instead of adding another skill. The workflow inventories an explicit allowlist only after registration validation, shows a deletion preview, and deletes only separately confirmed existing candidate paths. Project memory remains outside the allowlist and must never be removed.

**Tech Stack:** Markdown skills and documentation; Bash smoke tests.

## Global Constraints

- Cleanup is optional and follows successful move, separate registration confirmation, and `scripts/check-hub-registry.sh` validation.
- Cleanup confirmation is separate from move, preflight, and registration confirmation.
- The only removable paths are the exact files `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, and `ai/external-tools.md` in the confirmed direct-child project.
- Preserve `ai/current-task.md`, `ai/paused-tasks.md`, `ai/future-tasks.md`, `ai/project-context.md`, `ai/decisions.md`, and `ai/changelog.md` unchanged.
- Preserve `ai/skills/`, `.claude/`, and `.codex/` unchanged because they can contain user-created skills or tool configuration.
- Do not delete `ai/` itself; never archive, back up, copy, follow a symlink, remove Git metadata, or remove unrelated project files.
- Stop without deletion if a path, registry result, project relationship, candidate list, or symlink check changes before cleanup.

---

### Task 1: Add cleanup workflow contract tests

**Files:**

- Modify: `scripts/hub-smoke-test.sh`
- Modify: `scripts/smoke-test.sh`

**Interfaces:**

- Consumes: `hub-template/ai/skills/project-migrate/SKILL.md`, hub entry files, and `hub-template/ai/architecture.md`.
- Produces: RED checks that the cleanup workflow is present, optional, allowlisted, separately confirmed, and memory-safe.

- [ ] **Step 1: Write failing checks for the migration cleanup contract**

Add a `legacy_cleanup_contract_valid` helper to `scripts/hub-smoke-test.sh` that requires these literal invariants in `project-migrate/SKILL.md`:

```bash
assert_contains "$MIGRATE" 'Optional legacy standalone cleanup'
assert_contains "$MIGRATE" 'A previous move, preflight, or registration confirmation never authorizes cleanup.'
assert_contains "$MIGRATE" '- `AGENTS.md`'
assert_contains "$MIGRATE" 'Preserve `ai/skills/`, `.claude/`, and `.codex/` unchanged.'
assert_contains "$MIGRATE" '- `ai/current-task.md`'
assert_contains "$MIGRATE" 'Do not delete `ai/` as a directory.'
assert_contains "$MIGRATE" 'Do not archive, back up, copy, replace, or follow symlinks.'
```

Parse only the `Optional legacy standalone cleanup` section. Require the exact four-candidate list and reject any added candidate, `ai/skills/` as a deletion candidate, `.claude/` as a deletion candidate, `.codex/` as a deletion candidate, wording that makes cleanup automatic, a cleanup without explicit confirmation, or a broad recursive project deletion. Require repeated path, registry, candidate-list, and symlink validation before deletion. Require the same ordered workflow reference in `hub-template/AGENTS.md`, `hub-template/CLAUDE.md`, and `hub-template/ai/architecture.md`.

- [ ] **Step 2: Run the focused smoke test to verify RED**

Run:

```bash
bash scripts/hub-smoke-test.sh
```

Expected: FAIL because `project-migrate` does not yet contain the optional cleanup section or its required safety wording.

- [ ] **Step 3: Update the required-skill count only if the test currently needs it**

Do not add a new skill or increase the current count of 12. Keep the existing required-skill assertion unchanged unless a test proves it no longer matches the real template.

- [ ] **Step 4: Commit the RED contract**

```bash
git add scripts/hub-smoke-test.sh scripts/smoke-test.sh
git commit -m "test: define legacy standalone cleanup contract"
```

### Task 2: Implement the optional cleanup phase

**Files:**

- Modify: `hub-template/ai/skills/project-migrate/SKILL.md`
- Modify: `hub-template/AGENTS.md`
- Modify: `hub-template/CLAUDE.md`
- Modify: `hub-template/ai/architecture.md`

**Interfaces:**

- Consumes: successful `project-migrate` move and separate `project-register` validation.
- Produces: an optional `project-migrate` cleanup phase that an agent can execute only after a specific final confirmation.

- [ ] **Step 1: Add the `Optional legacy standalone cleanup` section to `project-migrate`**

Place it after `Separate registration gate`. State that it is available only after the validator passes and the project remains usable through the hub if it is skipped. Include this exact candidate allowlist:

```text
AGENTS.md
CLAUDE.md
ai/architecture.md
ai/external-tools.md
```

Include the exact preserved-memory list from the global constraints and state that `ai/skills/`, `.claude/`, and `.codex/` are retained unchanged because they can contain user-created content. State that the agent inventories only existence/type of the four candidate files, never contents, and rejects candidate paths or path components that are symlinks.

- [ ] **Step 2: Define the preview and confirmation gate**

Add the Russian preview template:

```text
Режим: routing
Проект: <canonical-hub>/projects/<project-id>

Старые standalone-правила, предложенные к удалению:
- <exact existing candidate path>

Будут сохранены без изменений: ai/current-task.md, ai/paused-tasks.md,
ai/future-tasks.md, ai/project-context.md, ai/decisions.md, ai/changelog.md.
_ai-hub уже является источником актуальных правил и skills для этого проекта.

Рекомендация: удалить перечисленные старые правила, чтобы они не расходились с
правилами хаба. Архив и резервная копия не создаются.

Подтвердите удаление только перечисленных путей для <project-id>.
```

Require this confirmation to name both the project ID and exact displayed path list. State verbatim that previous move, preflight, or registration approval does not authorize cleanup.

- [ ] **Step 3: Define final revalidation and narrow removal rules**

Before removing anything, require checks of canonical direct-child location, current registry validation, unchanged allowlisted candidate list, and no symlinks. State that the workflow stops with no deletion on any mismatch. Remove only confirmed existing candidates; do not delete `ai/`, `ai/skills/`, `.claude/`, `.codex/`, project source, `.git`, dependencies, unrelated configuration, or preserved memory. Do not archive, back up, copy, replace, or follow symlinks. Report each removed path and preserved memory paths.

- [ ] **Step 4: Update entry routing and architecture overview**

In both hub entry files, append a compact phrase to the existing project-migrate routing line: after validated registration it may offer separately confirmed deletion of old standalone rules while preserving project memory. In `hub-template/ai/architecture.md`, document the four-gate order: move → registration confirmation → registry validation → optional cleanup confirmation.

- [ ] **Step 5: Run GREEN checks**

Run:

```bash
bash scripts/check-consistency.sh
bash scripts/hub-smoke-test.sh
bash scripts/smoke-test.sh
git diff --check
```

Expected: every command exits 0, the required skill count remains 12, and the smoke test accepts the cleanup contract.

- [ ] **Step 6: Commit the implementation**

```bash
git add hub-template/AGENTS.md hub-template/CLAUDE.md \
  hub-template/ai/architecture.md hub-template/ai/skills/project-migrate/SKILL.md
git commit -m "feat: add optional legacy standalone cleanup"
```

### Task 3: Document the cleanup behavior

**Files:**

- Modify: `README.md`
- Modify: `docs/install.md`
- Modify: `docs/update.md`
- Modify: `docs/concepts.md`
- Modify: `docs/prompts.md`

**Interfaces:**

- Consumes: the implemented `project-migrate` cleanup phase.
- Produces: public instructions that distinguish migration, registration, and optional cleanup confirmations.

- [ ] **Step 1: Describe the four independent gates**

Update portable hub documentation to say that a legacy project is moved only after move confirmation, is registered only after a separate confirmation, is validated, and then may offer a separately confirmed removal of old standalone rules. State that project memory is preserved and no cleanup is automatic.

- [ ] **Step 2: Add a safe user prompt**

In `docs/prompts.md`, add or amend the migration prompt with this request:

```text
После успешной регистрации покажи отдельный список старых standalone-файлов,
которые можно удалить. Ничего не удаляй без нового явного подтверждения;
сохрани все файлы памяти проекта.
```

- [ ] **Step 3: Verify documentation and full suite**

Run:

```bash
rg -n -- '--root|automatic cleanup|автоматическ.*удал' README.md docs hub-template
bash scripts/check-consistency.sh
bash scripts/hub-smoke-test.sh
bash scripts/smoke-test.sh
git diff --check
```

Expected: no documentation promises automatic cleanup or a second durable rules source; all checks exit 0.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md docs/install.md docs/update.md docs/concepts.md docs/prompts.md
git commit -m "docs: explain legacy standalone cleanup"
```

## Final Verification

- [ ] Verify a clean Git status except for intentional task-report artifacts, which must not be staged.
- [ ] Re-run `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, `bash scripts/smoke-test.sh`, and `git diff --check` on the final branch.
- [ ] Confirm no real user project is moved, registered, or cleaned during implementation.
- [ ] Use `superpowers:requesting-code-review` for an independent review before proposing task-finish.
