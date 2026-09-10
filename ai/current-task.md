# Current Task

Status: done

Task ID: TASK-ai-dev-architecture-20260910-007

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: task-finish

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

implementation / review / task-finish / architecture-update

## Goal

Сделать обязательный автоматический цикл аналитики и обучения для вечернего ревью.

## Use Superpowers

no

## Relevant files

- `docs/superpowers/specs/2026-09-10-evening-review-learning-design.md`
- `scripts/assistant-workflows.sh`
- `calendar-policy/`

## Done criteria

- Запуск вечернего ревью автоматически получает календарные события, сохраняет снимок и возвращает историю снимков и нерассмотренные наблюдения.
- Модель получает структурированные данные для анализа без ручного вызова вспомогательных скриптов.
- Новые наблюдения и изменения правил остаются предложениями до явного подтверждения пользователя.
- Интеграционный тест доказывает полный цикл и предотвращает регрессию.

## Agent handoff

Last agent:

What changed:

Open risks:

Next agent should check:
- Session review: ai/session-reviews/2026-09-10-automatic-evening-review-learning.md
- Live evening-review execution after the application restart.
