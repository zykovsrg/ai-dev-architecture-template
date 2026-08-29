# Current Task

Status: active

Task ID: FT-20260826-002

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: planning

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

architecture-update

## Goal

Реализовать локальный Apple Calendar MCP для Personal AI Hub через проверенную
локальную копию `s-morgan-jeffries/apple-calendar-mcp` v0.9.0 и безопасную
policy-прослойку. Прослойка читает только явно выбранные календари, показывает
timezone и источник, предлагает свободные слоты, а create/update/delete будущих
событий выполняет только после отдельного preview и явного подтверждения.

## Use Superpowers

yes

## Relevant files

- `docs/superpowers/specs/2026-08-29-apple-calendar-mcp-design.md`
- `docs/superpowers/plans/2026-08-29-apple-calendar-mcp.md`
- `vendor/apple-calendar-mcp/`
- `calendar-policy/`
- `hub-template/ai/architecture.md`
- `hub-template/ai/skills/hub-calendar/SKILL.md`
- `hub-template/ai/skills/hub-workflows/SKILL.md`

## Done criteria

- Закреплена, проверена и локально сохранена версия MCP без автообновлений.
- Доступны только явно выбранные calendar ID; нет fallback на default/all.
- Чтение и free-time показывают timezone и `Apple Calendar / EventKit`.
- Create, update и future delete требуют одноразовый preview и отдельное подтверждение.
- Прошлое событие нельзя удалить или перенести в будущее для обхода запрета.
- Recurring-операция требует `this` или `future` и дату экземпляра.
- Пройдены обязательные unit, contract, architecture и smoke tests.
- Живая установка, macOS permission и выбор календарей сделаны только через отдельные подтверждения.

## Agent handoff

Last agent:

What changed:

Open risks:

Next agent should check:
