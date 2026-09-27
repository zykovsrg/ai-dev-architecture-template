# Current Task

Task ID: TASK-ai-dev-architecture-20260927-004

Status: active
Stage: intake

## Goal

Этап 7 модульной архитектуры (FT-20260926-004): разрезать
`hub-template/ai/architecture.md`. В нём остаются только общие правила ядра;
правила модулей уходят в `modules/<id>/rules.md` (ставятся как
`ai/rules/<id>.md`). Убрать повторы правил: «сначала маршрут, потом
подтверждение» живёт только в `hub-project-router`, в остальных местах —
ссылка в одну строку.

## Relevant files

- `hub-template/ai/architecture.md`
- `modules/<id>/rules.md`
- `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`

## Done criteria

- Каждое правило записано в одном месте.
- Замерено, насколько уменьшился объём, который агент читает в типичной сессии.
- Результаты тестов не хуже, чем в начале ветки.
- CI зелёный в pull request до слияния в `main`.
- Рабочий хаб обновляется только после «да» пользователя; после этого
  `hub_release.py drift` даёт exit 0.

## Agent handoff

Last agent: Claude (Opus 5.5)

What changed: задача взята из FT-20260926-004.

Open risks: нет.

Next agent should check: спецификация (Stage 4–6 details), записи 2026-09-27
в `ai/changelog.md` и `ai/decisions.md`; перед удалением файла — поиск по
`ai/decisions.md`.
