# Модуль: obsidian

Id: obsidian
Required: no
Switchable: yes
Depends: core, projects, tasks
Uses if present: —
Rules: ai/rules/obsidian.md
Keywords: Obsidian, obsidian-vault

## Purpose

Проекция проектов и задач только для чтения в центральное хранилище Obsidian;
ручные изменения доски превращаются в обратные предложения, но никогда не записываются прямо в задачи.

## Installs

- modules/obsidian/scripts/obsidian-task-sync.sh -> scripts/obsidian-task-sync.sh
- modules/obsidian/scripts/generate-obsidian-projects-kanban.sh -> scripts/generate-obsidian-projects-kanban.sh
- modules/obsidian/rules.md -> ai/rules/obsidian.md

## Repository only

- modules/obsidian/scripts/obsidian-task-sync-watch.sh
- modules/obsidian/scripts/install-obsidian-task-sync.sh
- modules/obsidian/tests/

## Reads

- реестр и карточки проектов (projects)
- файлы задач проекта (tasks)

## Writes

- центральное хранилище `projects/ai-dev-architecture/obsidian-vault`
- файлы задач только через подтверждённое обратное предложение, применяемое пользователем

## Subscribes

- after-task-write: bash scripts/generate-obsidian-projects-kanban.sh --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault --write --refresh-from-architecture
