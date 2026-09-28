# Current Task

Task ID: TASK-ai-dev-architecture-20260928-002

Status: active
Stage: implementation

## Goal

1. Сделать модули knowledge, goals, learning выключаемыми
   (`Switchable: yes`, `--with`/`--without` в обновлении хаба). Данные
   пользователя при выключении не удаляются.
2. Полностью обновить документацию инструмента (`README.md`,
   `getting-started/`, `docs/*.md`, кроме истории в `docs/superpowers/` и
   `docs/audits/`) под модульную архитектуру этапов 1–8.

## Relevant files

- `modules/{knowledge,goals,learning}/module.md`
- `tests/` (новый тест переключения)
- `README.md`, `getting-started/`, `docs/*.md`

## Done criteria

- Для каждого из трёх модулей тест: выключение убирает только его файлы,
  данные пользователя остаются, включение возвращает.
- Строгая проверка границ — 0; тесты не хуже начала ветки.
- Документация соответствует текущему коду (пути `modules/<id>/`, 10
  модулей, события, выключаемые модули); нет ссылок на `hub-template/`.
- CI зелёный в PR до слияния; рабочий хаб — только после «да», drift exit 0.

## Agent handoff

Last agent: Claude (Opus 5.5)

What changed: задача записана по согласию пользователя 2026-09-28.

Open risks: нет.

Next agent should check: исторические записи (changelog, decisions, старые
спеки и планы) не переписывать.
