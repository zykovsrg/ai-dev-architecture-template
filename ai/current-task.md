# Current Task

Task ID: TASK-ai-dev-architecture-20260927-005

Status: active
Stage: intake

## Goal

Этап 8 модульной архитектуры (FT-20260926-005): перенести в `modules/`
оставшиеся модули — knowledge, goals, learning, затем core, projects, tasks.
Строгая проверка границ (`check-module-boundaries.py --strict`) становится
падающим тестом. Ядро подключается к строгой проверке «задачи и проекты не
называют планирование и календарь».

## Relevant files

- `modules/*/module.md`, `hub-template/`
- `scripts/check-module-boundaries.py`, `tests/test_module_events.py`
- `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`

## Done criteria

- Все модули в своих папках `modules/<id>/`.
- `check-module-boundaries.py --strict` даёт 0 предупреждений и входит в тесты.
- core в списке строгой проверки «не называет планирование и календарь».
- Результаты тестов не хуже, чем в начале ветки.
- CI зелёный в pull request до слияния в `main`.
- Рабочий хаб обновляется только после «да» пользователя; после этого
  `hub_release.py drift` даёт exit 0.

## Agent handoff

Last agent: Claude (Opus 5.5)

What changed: задача взята из FT-20260926-005.

Open risks: нет.

Next agent should check: спецификация (Stage 4–7 details), отложенные мелочи
этапа 7 (`hub-workflows` в `CLAUDE.md`/`AGENTS.md` шаблона, «calendar» в
`modules/tasks/rules.md`); перед удалением файла — поиск по `ai/decisions.md`.
