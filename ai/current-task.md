# Current Task

Status: active

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: review

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

What changed: Foundation реализован в отдельной ветке и проходит финальное
независимое ревью. Пользователь разрешил автономно вести этот объём работ.

Open risks: EventKit full access шире allowlist MCP; будущая интеграция Calendar
нуждается в test calendar. Существующий vault не мигрируется до отдельного
content-aware review и подтверждения.

Next agent should check: Запустить финальные проверки и ревью; затем предложить
безопасную интеграцию ветки. Не применять её к live hub без отдельного решения.
