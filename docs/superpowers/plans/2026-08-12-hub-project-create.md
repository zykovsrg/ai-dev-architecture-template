# Hub Project Create Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `_ai-hub` create a confirmed new hub-managed project folder with only its six `ai/` memory files, a project card, a registry entry, and an active-project selection.

**Architecture:** Add one declarative hub-owned `project-create` workflow. It reuses the existing root list, registry/card schema, validator, active-project record, and shared post-confirmation workflows. No new installer, registry format, service, or standalone project entry files are added.

**Tech Stack:** Markdown instructions, existing Bash hub validator and smoke tests, Git.

## Global Constraints

- Start only on explicit user request in `Mode: routing`.
- Before confirmation, read only hub metadata needed for the confirmed allowed root and collision checks; do not read existing project content or memory.
- The target is a new non-symlink direct child of one confirmed allowed root; reject absolute, nested, traversal, hidden, glob, and unsafe names.
- One explicit confirmation covers only the displayed folder, six memory files, card, registry entry, validation, and active-project selection.
- Create exactly: `current-task.md`, `paused-tasks.md`, `future-tasks.md`, `project-context.md`, `decisions.md`, and `changelog.md` in `<project>/ai/`.
- Do not create Git, application code, dependencies, services, `AGENTS.md`, `CLAUDE.md`, shared skills, or other files.
- If the target exists, write nothing and offer `project-register` or a different name.
- Hub confirmation, allowed-root, secret, and memory-isolation rules outrank convenience.
- Persistent AI-facing rules are English; user-facing templates are Russian.

---

### Task 1: Define the creation contract

**Files:**
- Modify: `scripts/hub-smoke-test.sh`

- [ ] Add a failing structural contract for `hub-template/ai/skills/project-create/SKILL.md`.

It must require: routing mode; a confirmed allowed root; a new direct-child path; no project reads before confirmation; one explicit confirmation; collision rejection; `project-register` for existing paths; the existing `scripts/check-hub-registry.sh`; all six named memory files; active-project update only after successful validation; hub-owned `environment-check` and `task-intake` after creation.

It must prohibit: Git, application code, dependencies, services, `AGENTS.md`, `CLAUDE.md`, and shared skills.

Add negative fixtures that remove the unsafe-name rejection and the no-Git guarantee; each fixture must fail the contract check.

- [ ] Add `project-create` to both existing required-hub-skill lists in `scripts/hub-smoke-test.sh` and `scripts/check-consistency.sh`.
- [ ] Run `bash scripts/hub-smoke-test.sh`; expect failure because the skill does not yet exist.
- [ ] Commit: `test: define hub project creation contract`.

### Task 2: Add project-create

**Files:**
- Create: `hub-template/ai/skills/project-create/SKILL.md`

- [ ] Write a `project-create` workflow with these steps:

  1. In `Mode: routing`, read only `ai/allowed-roots.md`, `ai/project-registry.md`, and `ai/active-project.md`; ask the user to confirm one root.
  2. Derive a lowercase kebab-case ID from the confirmed project name. Validate the target as a new direct child within that root and reject unsafe names, symlinks, collisions, and existing paths without writes.
  3. Show one preview with name, ID, type, canonical path, exactly six `<path>/ai/` files, draft card, draft registry entry, and active-project selection. State exclusions explicitly.
  4. Wait for confirmation repeating the ID and exact path.
  5. Revalidate, create `<path>/ai/`, and copy only the six standard memory templates from `template/ai/`; do not copy `ai/architecture.md` or `ai/external-tools.md`.
  6. Write the approved existing-schema card and registry entry, with `Memory entry point: <path>/ai/current-task.md`; run `scripts/check-hub-registry.sh`.
  7. Only after successful validation, update `ai/active-project.md` with confirmed ID/path and invoke hub-owned `environment-check` and `task-intake`.

- [ ] Include this Russian confirmation shape:

```text
Режим: routing
Новый проект: <project-name>
ID: <project-id>
Тип: <type>
Путь: <canonical-path>

Будет создано: папка <canonical-path>/ai/; шесть файлов памяти; карточка;
запись в реестре; активный проект.
Не будет создано: Git, код, зависимости, сервисы, AGENTS.md, CLAUDE.md или общие skills.

Подтвердите: «Создать <project-id> по пути <canonical-path>».
```

- [ ] Run `bash scripts/hub-smoke-test.sh`; expect `Hub smoke tests passed.`
- [ ] Commit: `feat: add hub project creation workflow`.

### Task 3: Route and document it

**Files:**
- Modify: `hub-template/AGENTS.md`
- Modify: `hub-template/CLAUDE.md`
- Modify: `hub-template/ai/architecture.md`
- Modify: `docs/prompts.md`
- Modify: `README.md`

- [ ] Add one identical compact routing line to both hub entry files: a requested new project uses `project-create`; an existing folder uses `project-register`.
- [ ] Add to hub architecture: `project-create` makes a new direct-child project with only six memory files, card, registry entry, and selection after one preview confirmation; existing folders stay with `project-register`; no Git/code/dependencies/services/duplicate entries are created.
- [ ] Add a `Create a new project in a personal hub` prompt to `docs/prompts.md`.
- [ ] Add one README sentence stating that hub-created projects contain only their `ai/` memory by default.
- [ ] Do not modify either updater: it already distributes all files under `hub-template/ai/skills/`.
- [ ] Run `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, and `git diff --check`.
- [ ] Commit: `feat: route and document hub project creation`.

### Task 4: Final review

**Files:**
- Review: all Task 1–3 changes

- [ ] Verify every constraint in the approved specification: exact six files, one confirmation, no pre-confirmation project reads, safe target containment, no Git/code/dependency/entry-file creation, existing-path safety, reused validator/card schema, and unchanged hub security precedence.
- [ ] Run fresh checks: `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `git diff --check`, and `git status --short`.
- [ ] Request whole-branch review with the approved spec and complete diff. Fix verified Critical/Important findings and rerun affected tests.
- [ ] Propose `task-finish`; do not merge, push, or delete the worktree/branch without explicit confirmation.
