---
name: hub-project-register
description: Safely register one direct child of the hub's validated projects root.
---

# Project Register

Use this skill only for a user-requested registration. Registration starts in
`Mode: routing` and requires explicit confirmation before reading project context. Writing the card
and registry entry needs no separate confirmation.

Module rules: `ai/rules/projects.md`.

## Primary inventory (before individual project confirmation)

1. Read `ai/allowed-roots.md` and canonicalize the hub directory. Require that
   the file has exactly one entry, exactly `<canonical-hub>/projects`; reject
   missing, duplicate, external, or noncanonical roots. Show this sole allowed
   root and ask the user to confirm its narrow name-only inventory before
   inspecting it. Do not offer a root choice.
2. After that confirmation, inspect direct child directory names only. A
   requested candidate must be one direct child directory name only, not an
   absolute path, nested path, glob, `.`/`..`, or symlink target. Do not
   recurse, list files inside candidates, or read project content. Directory
   names are the entire inventory in this phase.
3. Classify candidates from the directory name only:
   - likely backup: a name containing a backup/archive/copy/time-stamp signal;
   - possible project: a normal direct-child name with no backup signal;
   - unknown: an ambiguous direct-child name.
4. Present the name, proposed canonical path, classification, and the narrow
   next action: confirm this individual project and exact path. The
   classification is an inference, never registration.

Never auto-register backups. Do not infer a project ID, purpose, card content,
or relationship from a directory name.

## After individual project confirmation

After the user explicitly confirms one displayed direct child and exact path,
revalidate the sole allowed root and require that the canonical path remains a
direct child of `<canonical-hub>/projects`. Only then may the agent inspect narrow `.git`
metadata and the smallest project context needed to classify that confirmed
candidate. This confirmation is not permission to read unrelated projects or
to recurse through the confirmed project.

## Read gate and writes

The individual confirmation above is the explicit approval before reading project context.
Read only the smallest project entry/context information needed to draft
metadata, then write the card and registry entry directly and show them in the
report. Run `scripts/check-hub-registry.sh` after the write; report its result
without reading unrelated projects.

The card must contain exactly these required fields: `Project ID:`,
`Name:`, `Type:`, `Status:`, `Last updated:`, `Purpose:`, `Typical tasks:`,
and `Memory entry point:`. `Project ID`, `Name`, `Type`, and `Status` must
match the registry entry. The memory entry point must be an absolute path
beneath the confirmed project's `ai/` directory; the validator must not read the memory entry point. `Boundaries:` and `Related
projects:` are optional, compact fields. The optional archiproject field is
`primary_archiproject: <group-id|none>`. Use `none` where absent. A project
belongs to exactly one, most specific group; it is also a member of every
ancestor group.

## Russian response template

```text
Режим: routing
Разрешённый корень: <confirmed-root>
Найдена папка: <child-name>
Предполагаемый путь: <canonical-path>
Классификация: возможный проект|вероятная резервная копия|неизвестно.

Это только предварительная проверка по имени папки; содержимое проекта не читалось. Подтвердите следующий шаг: проверить <child-name> по пути <canonical-path>.
```

## Readiness after registration

Registration proves identity and location, not readiness of project memory.
After individual project/path confirmation and registry validation, check only
this project's six canonical memory paths: `ai/current-task.md`,
`ai/future-tasks.md`, `ai/paused-tasks.md`, `ai/project-context.md`,
`ai/decisions.md`, and `ai/changelog.md`. Reject symlinks or paths escaping the
confirmed project. Preserve every existing file and project-specific instruction.

Create missing memory files only, using the corresponding minimal templates
from `hub-project-create` (its `current-task.md` through `changelog.md`
sections). Use create-if-missing semantics; never overwrite an existing record.
Validate each task file with `python3 scripts/task_records.py --file <exact-path>
--project-id <id> --kind current|future|paused --strict-headings`. Report
`ready` only when all three checks pass and all six memory files are available;
otherwise report `registered; adaptation needed` with exact affected paths.
Do not rewrite invalid existing tasks automatically or scan application code.

`resources/registered-project-entry.md` and
`resources/registered-project-architecture.md` explain optional compatibility
pointers; registration does not overwrite entry files. If a confirmed project
has conflicting legacy shared rules, use the optional cleanup phase in
`hub-project-migrate`, including its separate deletion confirmation.
