# Current Task

Status: active

Task ID: TASK-ai-dev-architecture-20260913-008

Allowed statuses: empty / active / review / blocked / done / paused

Stage: spec

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

implementation / review / task-finish / architecture-update

## Goal

Исправить мост Apple Calendar: возвращать время событий с корректным часовым
поясом календаря, чтобы планы дня не сдвигались по времени.

## Use Superpowers

yes

## Relevant files

- `calendar-policy/bridge/hub_eventkit_bridge.swift`
- `calendar-policy/tests/`
- `docs/superpowers/specs/2026-09-13-calendar-timezone-design.md`

## Done criteria

- Время события, возвращённое мостом, содержит смещение часового пояса события.
- Тест подтверждает правильное время для `Europe/Kirov`.
- Текущие проверки календарной политики проходят.

## Agent handoff

Last agent: Codex

What changed: Started the calendar timezone correction task.

Open risks: EventKit all-day event boundaries must retain their existing behavior.

Next agent should check: bridge output and timezone regression tests.
