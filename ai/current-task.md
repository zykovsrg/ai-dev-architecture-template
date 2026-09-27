# Current Task

Task ID: TASK-ai-dev-architecture-20260927-001
Status: active
Stage: intake

## Goal

Этап 4 модульной архитектуры с пилотом на Obsidian: паспорта (`module.md`)
для всех модулей из спецификации, генерация `ai/modules.md` при установке,
проверка границ в режиме предупреждения; Obsidian — первый модуль, который
можно выключить (не ставится в хаб), и в рабочем хабе он выключается.

Источник: FT-20260926-001 + часть FT-20260926-002 для Obsidian (решение
пользователя 2026-09-27). Спецификация:
`docs/superpowers/specs/2026-09-26-modular-architecture-design.md`.

## Relevant files

- `hub-template/ai/skills/hub-task-intake|hub-task-switch|hub-task-finish|hub-info-update/SKILL.md`
- `hub-template/ai/architecture.md` (раздел Central Obsidian Projection)
- `hub-template/ai/skills/hub-calendar/resources/joint-task-change.md`
- `scripts/hub_release.py`, `scripts/update-installed-hub.sh`, `scripts/install-hub.sh`
- `scripts/obsidian-task-sync.sh`, `scripts/generate-obsidian-projects-kanban.sh`

## Done criteria

- У каждого модуля есть паспорт; проверка границ печатает нарушения.
- В хабе есть `ai/modules.md`; навыки вызывают Obsidian только через событие
  `after-task-write` и только если модуль установлен.
- Обновление хаба без Obsidian показывает удаляемые файлы, требует
  подтверждения и не трогает хранилище Obsidian и данные.
- В рабочем хабе Obsidian выключен; навыки задач работают; `drift` → exit 0.
- Все тесты зелёные, CI зелёный.

## Agent handoff

Last agent: Claude (Opus 5.5)

What changed: задача открыта 2026-09-27 после закрытия
TASK-ai-dev-architecture-20260926-001.

Open risks: см. предыдущую передачу в `ai/changelog.md` (2026-09-27) —
локальная папка `ai/skills/` и `/ai/` в `.git/info/exclude` не решены.

Next agent should check: написать план (superpowers:writing-plans) по
спецификации; уточнить с пользователем только то, чего нет в спецификации.
