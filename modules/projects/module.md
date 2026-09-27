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
- hub-template/ai/project-registry.md -> ai/project-registry.md
- hub-template/ai/project-cards/.gitkeep -> ai/project-cards/.gitkeep
- hub-template/ai/archiprojects.md -> ai/archiprojects.md
- scripts/archiprojects.py -> scripts/archiprojects.py
- hub-template/ai/cross-project-signals.md -> ai/cross-project-signals.md
- hub-template/ai/skills/hub-project-create/ -> ai/skills/hub-project-create/
- hub-template/ai/skills/hub-project-register/ -> ai/skills/hub-project-register/
- hub-template/ai/skills/hub-project-migrate/ -> ai/skills/hub-project-migrate/
- hub-template/ai/skills/hub-project-switch/ -> ai/skills/hub-project-switch/
- hub-template/ai/skills/hub-registry-check/ -> ai/skills/hub-registry-check/
- hub-template/ai/skills/hub-local-router-install/ -> ai/skills/hub-local-router-install/

## Repository only

- —

## Reads

- the project registry and project cards

## Writes

- the project registry and project cards

## Subscribes

- —
