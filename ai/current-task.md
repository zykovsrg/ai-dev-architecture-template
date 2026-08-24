# Current Task

Status: done

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: task-finish

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

architecture-update

## Goal

Завершить foundation: каноническую модель задач и архипроектов, безопасный
компактный индекс и валидаторы. Не реализовывать Obsidian, Calendar, миграцию
vault или аудит чатов.

## Use Superpowers

yes — brainstorming, writing-plans, subagent-driven-development

## Relevant files

- `docs/superpowers/specs/2026-08-23-unified-assistant-architecture.md`
- `docs/superpowers/specs/2026-08-23-work-model-design.md`
- `docs/superpowers/specs/2026-08-23-routing-and-search-design.md`
- `docs/superpowers/plans/2026-08-23-unified-assistant-foundation.md`

## Done criteria

- Реализованы и протестированы work/archiproject contract, безопасный компактный
  индекс, проверки реестра и сохранение этих файлов при update.
- Защищённые правила маршрутизации используют только compact index до явного
  подтверждения проекта.
- Не выполнены изменения в live hub, Obsidian, Calendar, vault или аудит чатов.

## Agent handoff

Last agent: Codex

What changed: Foundation merged into local `main` at `6f8c622` and was closed
through `hub-task-finish`. Fresh `scripts/check-consistency.sh` and full
`scripts/hub-smoke-test.sh` passed. No live hub, Obsidian vault, Apple
Calendar, MCP, or external system was changed.

Open risks: EventKit full access шире allowlist MCP; будущая интеграция Calendar
нуждается в test calendar. Существующий vault не мигрируется до отдельного
content-aware review и подтверждения.

Next agent should check: After a separate confirmation, promote the Obsidian
phase from `ai/future-tasks.md` through task-intake/task-switch. Start with
the copied vault's read-only inventory and an approved implementation plan;
do not migrate notes, write task data, or enable Apple Calendar without a new
explicit confirmation.
