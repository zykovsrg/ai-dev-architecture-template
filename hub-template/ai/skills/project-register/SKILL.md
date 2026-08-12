---
name: project-register
description: Propose a safe, approval-gated registration for one direct child of a confirmed allowed root.
---

# Project Register

Use this skill only for a user-requested registration. Registration starts in
`Mode: routing` and requires explicit confirmation for every action that reads
project context or changes hub metadata.

## Discovery boundary

1. Read `ai/allowed-roots.md` and show its registered roots. Ask the user to
   confirm one root before inspecting it.
2. After that confirmation, inspect direct child directory names only. A
   requested candidate must be one direct child directory name only, not an
   absolute path, nested path, glob, `.`/`..`, or symlink target. Do not
   recurse, list files inside candidates, or read project content.
3. Classify candidates from the directory name and Git-directory presence
   without reading content:
   - likely project: a normal direct-child name with a `.git` directory;
   - likely backup: a name containing a backup/archive/copy/time-stamp signal,
     with or without `.git`;
   - unknown: any other direct child.
4. Present the name, proposed canonical path, classification, and the narrow
   next action. The classification is an inference, never registration.

Never auto-register backups. Do not infer a project ID, purpose, card content,
or relationship from project files.

## Approval gates

Obtain separate explicit approval before reading project context, before
creating a project card, and before adding registry data. For an approved
registration, first validate the canonical direct-child path against allowed
roots, then read only the smallest project entry/context information needed to
draft metadata. Show the proposed card and registry entry before writing them.
Run `scripts/check-hub-registry.sh` after an approved write; report its result
without reading unrelated projects.

## Russian response template

```text
Режим: routing
Разрешённый корень: <confirmed-root>
Найдена папка: <child-name>
Предполагаемый путь: <canonical-path>
Классификация: вероятный проект|вероятная резервная копия|неизвестно.

Это только предварительная проверка по имени и наличию папки .git; содержимое проекта не читалось. Подтвердите следующий шаг: <точное действие>.
```
