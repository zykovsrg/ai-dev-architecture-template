# Module: obsidian

Id: obsidian
Required: no
Switchable: yes
Depends: core, projects, tasks
Uses if present: —
Rules: —
Keywords: Obsidian, obsidian-vault

## Purpose

Read-only projection of projects and tasks into the central Obsidian vault;
manual board edits become proposals back, never direct task writes.

## Installs

- scripts/obsidian-task-sync.sh -> scripts/obsidian-task-sync.sh
- scripts/generate-obsidian-projects-kanban.sh -> scripts/generate-obsidian-projects-kanban.sh

## Repository only

- scripts/obsidian-task-sync-watch.sh
- scripts/install-obsidian-task-sync.sh

## Reads

- registry and project cards (projects)
- project task files (tasks)

## Writes

- the central vault `projects/ai-dev-architecture/obsidian-vault`
- task files only through a confirmed reverse proposal applied by the user

## Subscribes

- —
