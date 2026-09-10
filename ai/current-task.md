# Current Task

Status: active

Task ID: TASK-ai-dev-architecture-20260910-006

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: intake

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

implementation / review / task-finish / architecture-update

## Goal

Синхронизировать смоук-тест с действующими правилами скиллов, исправить
устаревшую ссылку в хендоффе и отдельно разобрать незакоммиченные изменения
основного хаба.

## Scope

- Запускать `scripts/hub-smoke-test.sh`, исправляя только устаревшие ожидания
  теста и не меняя правила скиллов ради прохождения.
- Исправить ссылку на коммит реализации в хендоффе: `ae295ce` → `58d57ab`.
- Проверить и отдельно закоммитить только согласованные изменения основного
  хаба, не смешивая их с работой проекта.

## Use Superpowers

yes

## Relevant files

- `scripts/hub-smoke-test.sh`
- `hub-template/ai/skills/`
- `docs/superpowers/2026-09-10-smoke-test-drift-handoff.md`

## Done criteria

- `bash scripts/hub-smoke-test.sh` проходит.
- `bash scripts/assistant-workflows-test.sh`, `bash scripts/architecture-test.sh`
  и `bash scripts/check-consistency.sh` проходят.
- Выполнены критерии приёмки спеки цикла редактирования дня.

## Agent handoff

Last agent:

What changed:

Open risks:

Next agent should check:
