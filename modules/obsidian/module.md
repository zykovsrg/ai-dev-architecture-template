# Module: obsidian

Id: obsidian
Required: no
Switchable: yes
Depends: core, projects, tasks
Uses if present: —
Rules: ai/rules/obsidian.md
Keywords: Obsidian, obsidian-vault

## Purpose

Read-only projection of projects and tasks into the central Obsidian vault;
manual board edits become proposals back, never direct task writes.

## Installs

- modules/obsidian/scripts/obsidian-task-sync.sh -> scripts/obsidian-task-sync.sh
- modules/obsidian/scripts/generate-obsidian-projects-kanban.sh -> scripts/generate-obsidian-projects-kanban.sh
- modules/obsidian/rules.md -> ai/rules/obsidian.md

## Repository only

- modules/obsidian/scripts/obsidian-task-sync-watch.sh
- modules/obsidian/scripts/install-obsidian-task-sync.sh
- modules/obsidian/tests/

## Reads

- registry and project cards (projects)
- project task files (tasks)

## Writes

- the central vault `projects/ai-dev-architecture/obsidian-vault`
- task files only through a confirmed reverse proposal applied by the user

## Subscribes

- after-task-write: bash scripts/generate-obsidian-projects-kanban.sh --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault --write --refresh-from-architecture
