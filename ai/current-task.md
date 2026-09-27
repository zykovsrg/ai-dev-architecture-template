# Current Task

Task ID: TASK-ai-dev-architecture-20260927-003
Status: active
Stage: intake

## Goal

Этап 6 модульной архитектуры: вложенные группы архипроектов (`parent:`, не
глубже 3, без циклов), цели в `ai/goals.md` (модуль goals), шестое поле
`group` в коротком списке проектов, скрипт дерева групп, «что горит по
группе» и «план дня по группе». Разовый перенос данных (группа «Хадасса →
Промо», проекты, 2 цели) — только после отдельного подтверждения.

Источник: FT-20260926-003 (решение пользователя 2026-09-27). Спецификация:
`docs/superpowers/specs/2026-09-26-modular-architecture-design.md`, раздел
Archiprojects.

## Relevant files

- `hub-template/ai/archiprojects.md`, `hub-template/ai/goal-log.md`
- `scripts/check-hub-registry.sh`, `scripts/read-compact-project-index.sh`
- `hub-template/ai/skills/hub-goal-progress/`, `scripts/count-goal-progress.sh`
- `hub-template/ai/skills/hub-task-overview/`, `modules/planning/skills/hub-workflows/`
- `modules/*/module.md`

## Done criteria

- Проверка реестра отклоняет циклы, потерянных родителей и глубину больше 3.
- Цели живут в `ai/goals.md`; группы не ссылаются на цели; поля карточек
  `related_archiprojects` и `archiproject_contribution` убраны.
- Короткий список проектов показывает группу; скрипт печатает дерево групп.
- Обзор и план по группе читают задачи только проектов группы и подгрупп.
- Перенос данных в рабочем хабе сделан после отдельного подтверждения;
  `drift` → exit 0; тесты и CI зелёные до слияния.

## Agent handoff

Last agent: Claude (Opus 5.5)

What changed: задача открыта 2026-09-27.

Open risks: нет.

Next agent should check: уточнить пробелы спецификации, дописать раздел
этапа 6, написать план.
