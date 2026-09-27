# Current Task

Task ID: TASK-ai-dev-architecture-20260927-002
Status: active
Stage: intake

## Goal

Этап 5 модульной архитектуры: планирование и календарь переезжают в
`modules/planning` и `modules/calendar` и становятся выключаемыми; навыки задач
больше не строят календарный предпросмотр сами, а вызывают событие
`before-task-confirmation`; сервер календаря больше не делает копии за день и
заметки самообучения.

Источник: FT-20260926-002 (решение пользователя 2026-09-27). Спецификация:
`docs/superpowers/specs/2026-09-26-modular-architecture-design.md`.

## Relevant files

- `modules/planning/module.md`, `modules/calendar/module.md`
- `hub-template/ai/skills/hub-workflows/`, `hub-template/ai/skills/hub-calendar/`
- `hub-template/ai/skills/hub-task-intake|hub-task-switch|hub-task-finish/SKILL.md`
- `calendar-policy/` (`evening_review.py`, `server.py`), `scripts/snapshot-calendar.sh`
- `scripts/module_passports.py`, `scripts/hub_release.py`, `scripts/update-installed-hub.sh`

## Done criteria

- Хаб ставится без планирования и календаря, и навыки задач работают.
- Копии календаря пишет только планирование.
- Выключение модуля показывает удаляемые файлы и требует подтверждения.
- В рабочем хабе оба модуля остаются включены; `drift` → exit 0.
- Все тесты зелёные, CI зелёный до слияния в `main`.

## Agent handoff

Last agent: Claude (Opus 5.5)

What changed: задача открыта 2026-09-27 после закрытия
TASK-ai-dev-architecture-20260927-001.

Open risks: нет.

Next agent should check: уточнить с пользователем только то, чего нет в
спецификации, дописать раздел этапа 5 и написать план.
