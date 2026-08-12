# Hub Project Create — Design

## Goal

Let a user create a new hub-managed project from `_ai-hub` through one
confirmation-gated workflow. The result is a new project folder with only its
`ai/` memory, plus a matching hub card and registry entry.

## Workflow

`project-create` starts in `Mode: routing` when the user explicitly asks to
create a new project.

1. Read only hub metadata needed to select a confirmed allowed root and avoid
   ID/path collisions. Do not read any other project's files or memory.
2. Propose one preview with project name, ID, type, exact path, the minimal
   project `ai/` files, a draft card, and a draft registry entry.
3. Require one explicit confirmation for the complete preview.
4. After confirmation, create the project folder and its `ai/` memory, write
   the card and registry entry, validate the hub registry, and select the new
   project as active.
5. Enter the selected project through the existing hub-owned
   `environment-check` and `task-intake` workflows.

## Project Contents

By default, a created project contains only its `ai/` memory files. It does
not create a Git repository, application code, dependencies, services,
`AGENTS.md`, `CLAUDE.md`, or duplicated shared skills.

The hub remains the only entry point and owns shared rules, routing, and
workflow skills.

## Safety Boundaries

- The requested path must be a new direct child of one confirmed allowed root.
- Reject absolute or nested project names, traversal segments, symlinks, and
  any path outside the confirmed root.
- If the target path already exists, do not write or overwrite anything. Offer
  `project-register` for an existing project or a different name.
- The preview is not permission to create files. No write occurs before its
  explicit confirmation.
- One confirmation covers exactly the displayed folder, project-memory files,
  card, registry entry, and active-project selection. Any Git initialization,
  code scaffolding, dependency installation, or external service setup needs a
  separate user request and confirmation.
- Keep project confirmation, allowed-root, secret-handling, and memory
  isolation rules higher priority than convenience or minimalism.

## Minimal Files

The new project's `ai/` directory receives only the six minimal project-memory
files required by hub-owned workflows. Their small initial contents are embedded
in `project-create`; an installed hub must not depend on the source
repository's standalone `template/` directory:

- `current-task.md`
- `paused-tasks.md`
- `future-tasks.md`
- `project-context.md`
- `decisions.md`
- `changelog.md`

No additional file is created unless a later confirmed workflow requires it.

## Integration

- Add `project-create` as a required hub skill and route it from hub entry
  rules and hub architecture.
- Reuse the existing registry-card schema and validator; do not add a second
  registry or project format.
- Keep `project-register` for already existing folders only.
- Extend hub smoke tests with creation-boundary and creation-result checks.
- Update public documentation and installation/update guidance where hub skills
  or new-project behavior are listed.

## Verification

- A creation request shows a complete preview and causes no write before
  confirmation.
- Confirmed creation produces exactly one direct-child project folder, the six
  listed memory files, one card, one registry entry, and a valid active-project
  record.
- Existing target paths, unsafe names, and outside-root paths are rejected
  without writes.
- `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, and
  `git diff --check` pass.
