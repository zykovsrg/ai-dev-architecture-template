---
name: hub-project-create
description: Use when a user asks to create and register a new project directly beneath the hub's validated projects root.
---

# Project Create

Use this workflow only to create a new project. The user's request to create the
project authorizes creation; no separate confirmation step is needed (Write
Confirmation Policy in `ai/architecture.md`). `hub-project-register` is for an already existing project; do not
invoke it for this creation workflow.

Module rules: `ai/rules/projects.md`.

## Before creation: narrow read and validation boundary

1. Read only `ai/allowed-roots.md`, `ai/project-registry.md`,
   `ai/active-project.md`, `ai/modules.md`, and the rules file of each
   `after-project-create` subscriber it lists (needed to build the creation plan
   below). Do not read `ai/project-cards/`,
   `ai/cross-project-signals.md`, `ai/archive/`, or any project directory in
   this phase. Canonicalize the hub directory and require that
   `ai/allowed-roots.md` has exactly one entry, exactly
   `<canonical-hub>/projects`. This validated path is the allowed
   root; do not offer a root choice or accept an external root.
2. Obtain the project name and type if they were not already supplied. Derive the ID as lowercase kebab-case from the
   project name; ask for a safe name if no unambiguous ID can be derived.
3. Validate without writing:
   - Revalidate the canonical hub projects root and its sole allowed-root entry.
   - Construct exactly one new direct-child path as
     `<canonical-hub>/projects/<id>`.
     The ID must be nonempty lowercase kebab-case and contain no path
     separator, `.` or `..`, whitespace, control character, glob, shell
     expansion, or other unsafe project names.
   - Reject a symlink at the root, target, or any resolved target component;
     reject a collision with an existing registry ID, card path, filesystem
     entry, or existing path. Do not replace, merge with, or inspect a
     collision.
   - Do not list or recurse into the candidate. The agent must not read
     project memory, source code, or application code before creation.

Stop with no writes when any check fails. Never widen the root, follow a
symlink, or infer a different ID.

## Creation plan

After the checks succeed, build the plan: name, ID, type, canonical path,
exactly six `<path>/ai/` files, the items added by `after-project-create`
subscribers, the card, the registry entry, and the active-project decision.
Inspect `git status --short -- ai/active-project.md` without writing. Preserve
the current active-project selection unless the user asked to switch to the new
project; if that file has uncommitted changes, do not switch and say why.

Read `<hub>/ai/modules.md`; each subscriber listed under `after-project-create`
adds its own items to the plan by following its rules file. If a subscriber
cannot build its part, say which one and why and create nothing.

Proceed to creation without asking. The final report uses this shape:

```text
Новый проект: <project-name>
ID: <project-id>
Тип: <type>
Путь: <canonical-path>
Confirmation required on new chat: yes
```

The plan explicitly excludes `ai/architecture.md`,
`ai/external-tools.md`, project `AGENTS.md`, project `CLAUDE.md`, shared skills,
`ai/cross-project-signals.md`, and `ai/archive/`.

## Creation procedure

1. Revalidate the allowed root, canonical path, direct-child rule, ID, name,
   symlink safety, and collision absence. Stop with
   no writes if any value changed or is unsafe.
2. Create `<canonical-path>/ai/`. Create only the six standard memory files
   listed in the plan using the built-in memory templates below:
   `current-task.md`, `paused-tasks.md`, `future-tasks.md`,
   `project-context.md`, `decisions.md`, and `changelog.md`. Do not copy
   `ai/architecture.md` or `ai/external-tools.md`.
3. Do not copy generic workflow skills, project instructions, or any other
   project files into the new project.
4. Write the existing-schema card at
   `ai/project-cards/<project-id>.md` and the registry entry exactly as
   planned. The card must retain all required fields and its
   `Memory entry point: <canonical-path>/ai/current-task.md`. The optional
   `primary_archiproject:` field uses `none` where absent. A project belongs
   to exactly one, most specific group; it is also a member of every
   ancestor group. Do not read that memory entry point while validating.
5. Run `scripts/check-hub-registry.sh`. On a failure, stop and report the
   validator output. Do not update active-project selection or invoke a
   project workflow.
6. Only after successful validation and when the user asked to switch, update
   `ai/active-project.md` with the new ID and canonical path. It is a
   selection record, not permission for a future chat.
7. Run the `after-project-create` event: read `<hub>/ai/modules.md`; for each
   subscriber listed under `after-project-create`, read its rules file and
   apply exactly its planned items for the new project only. If one fails,
   stop and report it; do not initialize Git or continue.
   Then, when the card has a `primary_archiproject:`, run
   `python3 scripts/seed_stage_template.py --hub <hub> --project <project-id>`.
   It adds the stage template of that group or its nearest ancestor to
   `ai/future-tasks.md`, or reports `"template": null` and writes nothing.
   Report the created task IDs. On an error, stop and report it.
8. Initialize a local Git repository and commit only the created scaffold.
   If authenticated GitHub CLI access is available, verify that `<project-id>`
   is unused, create a private repository with that exact name, add `origin`,
   and push `main`. If this remote provisioning is unavailable, retain local
   Git and report `pending-sync`; never attach or overwrite an existing remote.
9. Only when the user asked to switch to the new project and step 6 selected
   it, invoke hub-owned `hub-environment-check` and then hub-owned
   `hub-task-intake` for it. Otherwise stop after the report: a create-only
   request does not select the project, and entering it later needs the
   normal routing confirmation. Those workflows operate only on the selected
   project's `ai/` memory and cannot override hub routing, allowed roots,
   secret, or memory-isolation rules.

## Non-negotiable exclusions

The workflow must not add application code, dependencies, services, AGENTS.md, CLAUDE.md, or shared
skills. It must not write cross-project signals, archives, another project's
memory, or any path outside the allowed root and hub metadata needed
for this creation.

## Built-in memory templates

Use these contents exactly as the initial six project-memory files. They are
embedded here because the repository distributes them from `modules/*/data/`,
not a standalone `template/` directory.

### current-task.md

```markdown
# Current Task

Status: empty
Stage: intake

## Goal

No active task.

## Relevant files

None yet.

## Done criteria

Define during task intake.
```

### paused-tasks.md

```markdown
# Paused Tasks

Use this file only for unfinished tasks intentionally paused through task-switch.

## Paused tasks

No paused tasks yet.
```

### future-tasks.md

```markdown
# Future Tasks

Use this file for confirmed future ideas that are outside the current task.

## Future tasks

No future tasks yet.
```

### project-context.md

```markdown
# Project Context

## What this project is

TBD

## Invariants

TBD
```

### decisions.md

```markdown
# Decisions

## Current decisions

No project decisions yet.
```

### changelog.md

```markdown
# Changelog

## Current changelog

No notable changes yet.
```
