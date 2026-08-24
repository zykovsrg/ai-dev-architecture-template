# Current Task

Status: active

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: planning

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

architecture-update

## Goal

Подготовить первый TDD-план фундаментальных изменений для единого AI-ассистента:
канонической модели задач и архипроектов, безопасного компактного индекса и
валидаторов. Не реализовывать Obsidian, Calendar, миграцию vault или аудит чатов
в этом плане.

## Use Superpowers

yes — brainstorming, writing-plans, subagent-driven-development

## Relevant files

- `docs/superpowers/specs/2026-08-23-unified-assistant-architecture.md`
- `docs/superpowers/specs/2026-08-23-work-model-design.md`
- `docs/superpowers/specs/2026-08-23-routing-and-search-design.md`
- `docs/superpowers/plans/2026-08-23-unified-assistant-foundation.md`

## Done criteria

- Пользователь одобрил сводную архитектуру и scope architecture-update.
- Написан проверяемый TDD-план foundation без задач Obsidian, Calendar, миграции
  vault и session audit.
- План перечисляет точные protected/controlled files, тесты, rollback и
  подтверждения перед заменой правил.

## Agent handoff

Last agent: Codex

What changed: Tasks 1–7 завершены и независимо проверены. Пользователь одобрил
сводную архитектуру и scope будущего architecture-update; сейчас пишется только
foundation plan.

Open risks: EventKit full access шире allowlist MCP; будущая интеграция Calendar
нуждается в test calendar. Существующий vault не мигрируется до отдельного
content-aware review и подтверждения.

Next agent should check: Проверить foundation plan against approved architecture,
показать точные replacement diffs protected files и запросить подтверждение перед
самой реализацией.
