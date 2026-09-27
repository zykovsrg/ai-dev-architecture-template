# Module: core

Id: core
Required: yes
Switchable: no
Depends: —
Uses if present: —
Rules: ai/architecture.md
Keywords: —

## Purpose

Base Hub scaffolding: architecture rules, allowed roots, active-project pointer,
and the project router skill that every other module builds on.

## Installs

- hub-template/.gitignore -> .gitignore
- hub-template/AGENTS.md -> AGENTS.md
- hub-template/CLAUDE.md -> CLAUDE.md
- hub-template/ai/architecture.md -> ai/architecture.md
- hub-template/ai/allowed-roots.md -> ai/allowed-roots.md
- hub-template/ai/active-project.md -> ai/active-project.md
- hub-template/ai/archive/.gitkeep -> ai/archive/.gitkeep
- hub-template/projects/.gitkeep -> projects/.gitkeep
- hub-template/ai/skills/hub-project-router/ -> ai/skills/hub-project-router/
- scripts/check-hub-registry.sh -> scripts/check-hub-registry.sh
- scripts/read-compact-project-index.sh -> scripts/read-compact-project-index.sh

## Repository only

- —

## Reads

- nothing outside its own installed files

## Writes

- —

## Subscribes

- —
