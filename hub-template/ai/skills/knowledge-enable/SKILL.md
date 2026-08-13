---
name: knowledge-enable
type: implementation
description: |
  Use on demand to add the optional empty knowledge scaffold to an existing
  confirmed registered hub project. It never migrates standalone projects.
---

# Knowledge Enable

Use this workflow only for an existing confirmed registered project. Legacy
standalone migration is out of scope. Do not use this workflow to discover,
register, move, import, copy, or transform a project or its records.

## Preconditions and read boundary

1. The router must already have confirmed the registered project ID and exact
   registered path. If it has not, return to `Mode: routing`; do not infer a
   project from a remembered active-project record.
2. Revalidate the canonical hub, its sole `<canonical-hub>/projects` allowed
   root, the registry ID, and the exact registered path. The path must remain
   one direct child of that root.
3. Inspect metadata only for these exact paths: `knowledge/README.md`,
   `knowledge/record-template.md`, `knowledge/research/`,
   `knowledge/decisions/`, `knowledge/risks/`, and `knowledge/runbooks/`.
   Do not read unrelated project content, enumerate directories, or read an
   existing knowledge record.
4. Never follow a symlink. Stop with no writes if the hub root, projects root,
   project path, `knowledge/`, or any exact scaffold path is a symlink or
   resolves through one.
5. Do not write before confirmation. A prior router confirmation authorizes
   project access, not this scaffold change.

## Preview and confirmation

Show one complete preview with the confirmed registered project identity and
the exact registered path. It must name every scaffold path and identify which
ones are absent, without opening existing records:

```text
Project: <project-id>
Path: <exact-registered-path>
Mode: knowledge-enable

Будет создано только при отсутствии:
- <exact-registered-path>/knowledge/README.md
- <exact-registered-path>/knowledge/record-template.md
- <exact-registered-path>/knowledge/research/
- <exact-registered-path>/knowledge/decisions/
- <exact-registered-path>/knowledge/risks/
- <exact-registered-path>/knowledge/runbooks/

Не будет прочитано: существующие records, код, task memory и иной контент проекта.
Не будет изменено: существующие records, Git, инструкции проекта, skills,
реестр, карточка или active-project.

Подтвердите: «Включить knowledge для <project-id> по пути <exact-registered-path>».
```

Wait for one explicit confirmation that repeats both the confirmed ID and exact
registered path. Any mismatch, changed registry mapping, collision concern, or
symlink stops the workflow with no writes.

## Confirmed enablement

1. Revalidate every precondition, the matching confirmation, and the exact
   absent paths without reading record contents.
2. Create only absent scaffold files and directories: `knowledge/README.md`,
   `knowledge/record-template.md`, `knowledge/research/`,
   `knowledge/decisions/`, `knowledge/risks/`, and `knowledge/runbooks/`.
3. Write the canonical README and record template below only when that exact
   file is absent. It must never overwrite records, an existing README, or an existing
   record template; do not merge, rename, delete, or inspect existing records.
4. Report only the exact created and already-present scaffold paths.

## Non-negotiable exclusions

Do not create or modify Git, application code, dependencies, services,
`AGENTS.md`, `CLAUDE.md`, project skills, registry entries, cards, or
`ai/active-project.md`. Do not read task memory, source code, credentials,
environment files, or any unrelated project path. Do not create capture or
review workflows as part of enablement.

## Canonical scaffold files

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

Knowledge records must be secret-free. Never store credentials, passwords,
tokens, private keys, or raw environment values.
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
