---
name: project-register
description: Propose a safe, approval-gated registration for one direct child of a confirmed allowed root.
---

# Project Register

Use this skill only for a user-requested registration. Registration starts in
`Mode: routing` and requires explicit confirmation for every action that reads
project context or changes hub metadata.

## Primary inventory (before individual project confirmation)

1. Read `ai/allowed-roots.md` and show its registered roots. Ask the user to
   confirm one root before inspecting it.
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
validate that canonical path against allowed roots and that it remains a direct
child of the confirmed root. Only then may the agent inspect narrow `.git`
metadata and the smallest project context needed to classify that confirmed
candidate. This confirmation is not permission to read unrelated projects or
to recurse through the confirmed project.

## Approval gates

The individual confirmation above is the explicit approval before reading project context.
Obtain separate explicit approval before creating a project card and before
adding registry data. For an approved registration, read only the smallest
project entry/context information needed to draft metadata. Show the proposed
card and registry entry before writing them. Run
`scripts/check-hub-registry.sh` after an approved write; report its result
without reading unrelated projects.

## Russian response template

```text
Режим: routing
Разрешённый корень: <confirmed-root>
Найдена папка: <child-name>
Предполагаемый путь: <canonical-path>
Классификация: возможный проект|вероятная резервная копия|неизвестно.

Это только предварительная проверка по имени папки; содержимое проекта не читалось. Подтвердите следующий шаг: проверить <child-name> по пути <canonical-path>.
```
