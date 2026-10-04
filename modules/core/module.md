# Module: core

Id: core
Required: yes
Switchable: no
Depends: —
Uses if present: learning
Rules: ai/architecture.md
Keywords: —

## Purpose

Base Hub scaffolding: architecture rules, allowed roots, active-project pointer,
and the project router skill that every other module builds on.

## Installs

- modules/core/data/.gitignore -> .gitignore
- modules/core/data/AGENTS.md -> AGENTS.md
- modules/core/data/CLAUDE.md -> CLAUDE.md
- modules/core/data/ai/architecture.md -> ai/architecture.md
- modules/core/data/ai/allowed-roots.md -> ai/allowed-roots.md
- modules/core/data/ai/active-project.md -> ai/active-project.md
- modules/core/data/ai/archive/.gitkeep -> ai/archive/.gitkeep
- modules/core/data/projects/.gitkeep -> projects/.gitkeep
- modules/core/skills/hub-project-router/ -> ai/skills/hub-project-router/
- modules/core/scripts/check-hub-registry.sh -> scripts/check-hub-registry.sh
- modules/core/scripts/read-compact-project-index.sh -> scripts/read-compact-project-index.sh

## Repository only

- —

## Reads

- nothing outside its own installed files

## Writes

- —

## Subscribes

- —
