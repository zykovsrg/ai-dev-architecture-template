# Module: projects

Id: projects
Required: yes
Switchable: no
Depends: core
Uses if present: —
Rules: ai/rules/projects.md
Keywords: —

## Purpose

Project registry and project cards: create, register, migrate, switch and
audit the registered hub projects.

## Installs

- modules/projects/rules.md -> ai/rules/projects.md
- modules/projects/data/ai/project-registry.md -> ai/project-registry.md
- modules/projects/data/ai/project-cards/.gitkeep -> ai/project-cards/.gitkeep
- modules/projects/data/ai/archiprojects.md -> ai/archiprojects.md
- modules/projects/scripts/archiprojects.py -> scripts/archiprojects.py
- modules/projects/data/ai/cross-project-signals.md -> ai/cross-project-signals.md
- modules/projects/skills/hub-project-create/ -> ai/skills/hub-project-create/
- modules/projects/skills/hub-project-register/ -> ai/skills/hub-project-register/
- modules/projects/skills/hub-project-migrate/ -> ai/skills/hub-project-migrate/
- modules/projects/skills/hub-project-switch/ -> ai/skills/hub-project-switch/
- modules/projects/skills/hub-registry-check/ -> ai/skills/hub-registry-check/
- modules/projects/skills/hub-local-router-install/ -> ai/skills/hub-local-router-install/

## Repository only

- —

## Reads

- the project registry and project cards

## Writes

- the project registry and project cards

## Subscribes

- —
