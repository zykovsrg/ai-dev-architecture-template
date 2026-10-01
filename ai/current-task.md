# Current Task

Task ID: TASK-ai-dev-architecture-20261001-002
Status: active
Stage: review

## Goal

Полный аудит архитектуры: найти мёртвый код и техдолг, оценить самообучение
(learning) и как его автоматизировать. Результат — предложения пользователю;
изменения только после его выбора.

## Relevant files

- `modules/`, `scripts/`, `tests/`, `docs/`, хаб `ai/`
- Отчёт: `docs/audits/2026-10-01-architecture-audit.md` (ждёт выбора пользователя)

## Done criteria

- Есть отчёт аудита с доказательствами (файлы/строки/проверки).
- Отдельно: мёртвый код, техдолг, самообучение + автоматизация.
- Для каждого пункта — можно ли и как, цена и риск.
- Ничего не удалено без выбора пользователя.

## Agent handoff

Last agent: Claude (Opus 5.5)

What changed: TASK-ai-dev-architecture-20261001-001 закрыта 2026-10-01 —
устаревшие копии архитектуры убраны из всех 33 проектов хаба.
Session review: `ai/session-reviews/2026-10-01-legacy-project-cleanup-closure.md`.

Open risks: дизайнерские скиллы больше нет ни в проектах, ни в хабе — перенос
отложен (FT-20261001-001).

Next agent should check: открытых задач архитектуры нет.

## Progress 2026-10-01

- A1/A2: ветка `hub-sync-871efdb`, коммит 3de9c4c — правки 871efdb перенесены
  в `modules/`, событие переименовано в `before-task-write`, шаги 5–6
  `hub-task-finish` восстановлены, 5 тестов обновлены. Все тесты зелёные.
- В коммит попал и незакоммиченный абзац про синхронизацию в `day-plan.md`
  (он же есть незакоммиченным в хабе).
- Остаток `--check`: незакоммиченная правка хаба «план дня из 5 разделов»
  (`ai/rules/planning.md`, `hub-project-router`) — ждёт решения пользователя;
  `hub-task-finish` — исправление, попадёт в хаб при следующем релизе.
- План дня из 5 разделов перенесён в исходники (a87dab9) по решению пользователя.
  Исправленный `hub-task-finish` скопирован в хаб. `--check`: хаб совпадает
  с исходниками. Осталось: PR ветки `hub-sync-871efdb` в main и коммит хаба.
- Чистка (ветка `cleanup-dead-code`): удалены `migrate-archiprojects-stage6.py`,
  `refresh-session-inventory.sh` с тестами, пустые `tmp/`, `projects/`;
  7 записей `promoted` из future-tasks; changelog до 2026-09-05 →
  `ai/archive/changelog-before-2026-09-06.md`; 93 плана/спеки →
  `docs/superpowers/archive/` (3 живые спеки оставлены). `obsidian-vault/`,
  `decisions.md`, `install.sh` не тронуты. Все тесты зелёные.
- Дальше по аудиту: самообучение L1–L5.
