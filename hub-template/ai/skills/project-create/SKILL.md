---
name: project-create
description: Use when a user asks to create and register a new project directly beneath one confirmed allowed root.
---

# Project Create

Use this workflow only to create a new project. It starts and remains in
`Mode: routing` until one explicit confirmation authorizes the displayed ID
and exact path. `project-register` is for an already existing project; do not
invoke it for this creation workflow.

## Before confirmation: narrow read and validation boundary

1. Read only `ai/allowed-roots.md`, `ai/project-registry.md`, and
   `ai/active-project.md`. Do not read `ai/project-cards/`,
   `ai/cross-project-signals.md`, `ai/archive/`, or any project directory in
   this phase. Show the registered roots and ask the user to confirm one root.
2. After the root is confirmed, obtain the project name and type if they were
   not already supplied. Derive the ID as lowercase kebab-case from the
   project name; ask for a safe name if no unambiguous ID can be derived.
3. Validate without writing:
   - Canonicalize the confirmed allowed root and require that it is still one
     listed allowed root.
   - Construct exactly one new direct-child path as `<canonical-root>/<id>`.
     The ID must be nonempty lowercase kebab-case and contain no path
     separator, `.` or `..`, whitespace, control character, glob, shell
     expansion, or other unsafe project names.
   - Reject a symlink at the root, target, or any resolved target component;
     reject a collision with an existing registry ID, card path, filesystem
     entry, or existing path. Do not replace, merge with, or inspect a
     collision.
   - Do not list or recurse into the candidate. The agent must not read
     project memory, source code, or application code before confirmation.

Stop with no writes when any check fails. Never widen the root, follow a
symlink, infer a different ID, or treat a remembered active project as
confirmation.

## Single preview and approval gate

Show one complete preview after the checks succeed. It must include the name,
ID, type, canonical path, exactly six `<path>/ai/` files, the draft card, the
draft registry entry, and the active-project selection. Use this shape:

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

Immediately below that Russian preview, show these exact draft contents before
waiting:

```text
Memory files:
- <canonical-path>/ai/current-task.md
- <canonical-path>/ai/paused-tasks.md
- <canonical-path>/ai/future-tasks.md
- <canonical-path>/ai/project-context.md
- <canonical-path>/ai/decisions.md
- <canonical-path>/ai/changelog.md

Card: ai/project-cards/<project-id>.md
Project ID: <project-id>
Name: <project-name>
Type: <type>
Status: active
Last updated: <YYYY-MM-DD>
Purpose: <approved-purpose>
Typical tasks: <approved-typical-tasks>
Memory entry point: <canonical-path>/ai/current-task.md

Registry entry:
## <project-id>
Name: <project-name>
Type: <type>
Status: active
Path: <canonical-path>
Tags: <approved-tags>
Card: ai/project-cards/<project-id>.md

Active-project selection:
Project ID: <project-id>
Path: <canonical-path>
Confirmation required on new chat: yes
```

The quoted Russian confirmation is the one explicit confirmation. Wait for it
to repeat both `<project-id>` and `<canonical-path>` exactly. Do not create any
directory, card, registry entry, or active-project record before that reply.
The preview also explicitly excludes `ai/architecture.md`,
`ai/external-tools.md`, project `AGENTS.md`, project `CLAUDE.md`, shared skills,
`ai/cross-project-signals.md`, and `ai/archive/`.

## Approved creation procedure

1. Revalidate the confirmed root, canonical path, direct-child rule, ID, name,
   symlink safety, collision absence, and the matching confirmation. Stop with
   no writes if any value changed or is unsafe.
2. Create `<canonical-path>/ai/`. Copy only these six standard memory templates
   from `template/ai/` to the six paths shown in the preview: `current-task.md`,
   `paused-tasks.md`, `future-tasks.md`, `project-context.md`, `decisions.md`,
   and `changelog.md`. Do not copy `ai/architecture.md` or
   `ai/external-tools.md`.
3. Write the approved existing-schema card at
   `ai/project-cards/<project-id>.md` and the approved registry entry exactly
   as previewed. The card must retain all required fields and its
   `Memory entry point: <canonical-path>/ai/current-task.md`. Do not read that
   memory entry point while validating.
4. Run `scripts/check-hub-registry.sh`. On a failure, stop and report the
   validator output. Do not update active-project selection or invoke a
   project workflow.
5. Only after successful validation, update `ai/active-project.md` with the
   confirmed ID and canonical path. `active-project.md only after successful validation`;
   it is a selection record, not permission for a future chat.
6. Invoke hub-owned `environment-check` and then hub-owned `task-intake` for
   the confirmed selected project. Those workflows operate only on the selected
   project's `ai/` memory and cannot override hub confirmation, allowed roots,
   secret, or memory-isolation rules.

## Non-negotiable exclusions

Git repositories must not be created or modified. The workflow must not add
application code, dependencies, services, AGENTS.md, CLAUDE.md, or shared
skills. It must not write cross-project signals, archives, another project's
memory, or any path outside the confirmed allowed root and hub metadata needed
for this approved creation.
