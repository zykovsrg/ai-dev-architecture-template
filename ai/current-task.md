# Current Task

Status: active

Task ID: FT-20260828-001

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: planning

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

architecture-update

## Goal

Заменить перегруженный `Tasks-Kanban` компактным обзором всех проектов.

## Use Superpowers

yes

## Relevant files

- scripts/generate-obsidian-projects-kanban.sh
- scripts/obsidian-projects-kanban-test.sh
- hub-template/ai/archiprojects.md

## Done criteria

- Обзор содержит только название проекта со ссылкой на его отдельную
  канбан-доску, архипроект и текущую задачу.
- В обзоре представлены все зарегистрированные проекты.
- Старый `Tasks-Kanban` больше не используется.
- Автоматические тесты и проверки проекта проходят.

## Agent handoff

Last agent: Codex

What changed: задача создана по запросу пользователя; старая задача приостановлена через task-switch.

Open risks: Нужно определить точный источник ссылок на отдельные канбан-доски и трактовку удаления старого `Tasks-Kanban`.

Next agent should check: текущий генератор обзора, тесты, реестр архипроектов и формат файлов Obsidian.
