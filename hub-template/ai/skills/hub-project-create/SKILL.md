---
name: hub-project-create
description: Use when a user asks to create and register a new project directly beneath the hub's validated projects root.
---

# Project Create

Use this workflow only to create a new project. It starts and remains in
`Mode: routing` until one explicit confirmation authorizes the displayed ID
and exact path. `hub-project-register` is for an already existing project; do not
invoke it for this creation workflow.

## Before confirmation: narrow read and validation boundary

1. Read only `ai/allowed-roots.md`, `ai/project-registry.md`, and
   `ai/active-project.md`. Do not read `ai/project-cards/`,
   `ai/cross-project-signals.md`, `ai/archive/`, or any project directory in
   this phase. Canonicalize the hub directory and require that
   `ai/allowed-roots.md` has exactly one entry, exactly
   `<canonical-hub>/projects`. This validated path is the confirmed allowed
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
     project memory, source code, or application code before confirmation.

Stop with no writes when any check fails. Never widen the root, follow a
symlink, infer a different ID, or treat a remembered active project as
confirmation.

## Single preview and approval gate

Show one complete preview after the checks succeed. It must include the name,
ID, type, canonical path, exactly six `<path>/ai/` files, the empty knowledge
scaffold, the draft card, the draft registry entry, and the active-project
selection. Use this shape:

```text
Режим: routing
Новый проект: <project-name>
ID: <project-id>
Тип: <type>
Путь: <canonical-path>

Будет создано: папка <canonical-path>/ai/; шесть файлов памяти; пустой
knowledge-scaffold; карточка; запись в реестре; активный проект; локальный Git.
При доступной авторизации GitHub: приватный репозиторий <project-id>, первый
commit и push ветки main. Иначе результат будет отмечен как pending-sync.
Не будут созданы: код, зависимости, сервисы, AGENTS.md, CLAUDE.md или общие skills.

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

Knowledge scaffold:
- <canonical-path>/knowledge/README.md
- <canonical-path>/knowledge/record-template.md
- <canonical-path>/knowledge/research/
- <canonical-path>/knowledge/decisions/
- <canonical-path>/knowledge/risks/
- <canonical-path>/knowledge/runbooks/

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

1. Revalidate the confirmed allowed root, canonical path, direct-child rule, ID, name,
   symlink safety, collision absence, and the matching confirmation. Stop with
   no writes if any value changed or is unsafe.
2. Create `<canonical-path>/ai/`. Create only the six standard memory files
   shown in the preview using the built-in memory templates below:
   `current-task.md`, `paused-tasks.md`, `future-tasks.md`,
   `project-context.md`, `decisions.md`, and `changelog.md`. Do not copy
   `ai/architecture.md` or `ai/external-tools.md`.
3. Create only the absent knowledge scaffold at `<canonical-path>/knowledge/`:
   `README.md`, `record-template.md`, and the empty `research/`, `decisions/`,
   `risks/`, and `runbooks/` directories. Use the canonical contents below for
   the two files. It must never overwrite records or any existing scaffold
   file. The created project uses the hub-owned `hub-knowledge-capture` and
   hub-owned `hub-knowledge-review` workflows; do not copy generic workflow skills,
   project instructions, or any other project files into it.
4. Write the approved existing-schema card at
   `ai/project-cards/<project-id>.md` and the approved registry entry exactly
   as previewed. The card must retain all required fields and its
   `Memory entry point: <canonical-path>/ai/current-task.md`. Do not read that
   memory entry point while validating.
5. Run `scripts/check-hub-registry.sh`. On a failure, stop and report the
   validator output. Do not update active-project selection or invoke a
   project workflow.
6. Only after successful validation, update `ai/active-project.md` with the
   confirmed ID and canonical path. `active-project.md only after successful validation`;
   it is a selection record, not permission for a future chat.
7. Initialize a local Git repository and commit only the approved scaffold.
   If authenticated GitHub CLI access is available, verify that `<project-id>`
   is unused, create a private repository with that exact name, add `origin`,
   and push `main`. If this remote provisioning is unavailable, retain local
   Git and report `pending-sync`; never attach or overwrite an existing remote.
8. Invoke hub-owned `hub-environment-check` and then hub-owned `hub-task-intake` for
   the confirmed selected project. Those workflows operate only on the selected
   project's `ai/` memory and cannot override hub confirmation, allowed roots,
   secret, or memory-isolation rules.

## Non-negotiable exclusions

The workflow must not add application code, dependencies, services, AGENTS.md, CLAUDE.md, or shared
skills. It must not write cross-project signals, archives, another project's
memory, or any path outside the confirmed allowed root and hub metadata needed
for this approved creation.

## Built-in memory templates

Use these contents exactly as the initial six project-memory files. They are
embedded here because an installed hub contains `hub-template/`, not the source
repository's standalone `template/` directory.

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

### knowledge/README.md

```markdown
# Project Knowledge

This local knowledge base is optional reference material. Read it only when a
task or the user explicitly needs it. It is not default context and is not an
automatic archive of conversations.

Store records in the category that matches their purpose:

- `research/` — investigated questions and evidence.
- `decisions/` — durable choices and their rationale.
- `risks/` — known risks, assumptions, and mitigations.
- `runbooks/` — repeatable operational procedures.

Create and update records only through the hub-owned `hub-knowledge-capture` or
`hub-knowledge-review` workflow after its exact confirmation. Do not copy generic
workflow skills into this project.

Knowledge records must contain no secrets, personal data or client data. Never
store credentials, passwords, tokens, private keys, raw environment values,
personally identifying material, or client-confidential material. Omit or
redact prohibited content without echoing the rejected value; refer to an
approved secure location instead of recording it.

The only allowed statuses are `draft`, `verified`, `needs-review`, `stale`, or
`superseded`. Retain stale and superseded records at their original paths and
link each one to its replacement under `Related records`; never silently delete
it.
```

### knowledge/record-template.md

```markdown
---
type: research
status: draft
created: YYYY-MM-DD
reviewed: YYYY-MM-DD
sources: []
---

# Record title

## Statement

## Evidence

## Scope

## Related records

## Review notes
```
