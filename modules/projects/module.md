# Модуль: projects

Id: projects
Required: yes
Switchable: no
Depends: core
Uses if present: planning
Rules: ai/rules/projects.md
Keywords: —

## Purpose

Реестр и карточки проектов: создавать, регистрировать, переносить, переключать
и проверять зарегистрированные проекты Хаба.

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
- modules/projects/skills/hub-full-sync/ -> ai/skills/hub-full-sync/

## Repository only

- —

## Reads

- реестр и карточки проектов

## Writes

- реестр и карточки проектов

## Subscribes

- —
