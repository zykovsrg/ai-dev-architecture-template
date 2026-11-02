# Модуль: planning

Id: planning
Required: no
Switchable: yes
Depends: core, projects, tasks, calendar
Uses if present: goals, learning
Rules: ai/rules/planning.md
Keywords: —

## Purpose

Процессы планирования дня, вечернего и недельного разбора, объединяющие задачи
со снимком календаря.

## Installs

- modules/planning/skills/hub-workflows/ -> ai/skills/hub-workflows/
- modules/planning/data/ai/workflow-context.md -> ai/workflow-context.md
- modules/planning/scripts/snapshot-calendar.sh -> scripts/snapshot-calendar.sh
- modules/planning/scripts/calendar-context.py -> scripts/calendar-context.py
- modules/planning/scripts/calendar_task_sync.py -> scripts/calendar_task_sync.py
- modules/planning/scripts/calendar_drift.py -> scripts/calendar_drift.py
- modules/planning/scripts/reminders_sync.py -> scripts/reminders_sync.py
- modules/planning/scripts/reminders_engine.py -> scripts/reminders_engine.py
- modules/planning/scripts/reminders_authority.py -> scripts/reminders_authority.py
- modules/planning/scripts/reminders_authority_archive.py -> scripts/reminders_authority_archive.py
- modules/planning/scripts/reminders_task_gateway.py -> scripts/reminders_task_gateway.py
- modules/planning/scripts/reminders_reads.py -> scripts/reminders_reads.py
- modules/planning/scripts/reminders_recurrence.py -> scripts/reminders_recurrence.py
- modules/planning/scripts/reminders_archive.py -> scripts/reminders_archive.py
- modules/planning/scripts/reminders_project_lists.py -> scripts/reminders_project_lists.py
- modules/planning/scripts/reminders_project_initial_binding.py -> scripts/reminders_project_initial_binding.py
- modules/planning/scripts/reminders_cancel.py -> scripts/reminders_cancel.py
- modules/planning/scripts/reminders_external_retirement.py -> scripts/reminders_external_retirement.py
- modules/planning/scripts/reminders_task_reassignment.py -> scripts/reminders_task_reassignment.py
- modules/planning/scripts/reminders_project_list_verification.py -> scripts/reminders_project_list_verification.py
- modules/planning/scripts/reminders_historical.py -> scripts/reminders_historical.py
- modules/planning/scripts/reminders_structure.py -> scripts/reminders_structure.py
- modules/planning/scripts/reminders_old_list_cleanup.py -> scripts/reminders_old_list_cleanup.py
- modules/planning/scripts/reminders_bidirectional.py -> scripts/reminders_bidirectional.py
- modules/planning/scripts/reminders_structure_restart.py -> scripts/reminders_structure_restart.py
- modules/planning/scripts/reminders_structure_prefix.py -> scripts/reminders_structure_prefix.py
- modules/planning/scripts/evening_review.py -> scripts/evening_review.py
- modules/planning/scripts/review_reminders.py -> scripts/review_reminders.py
- modules/planning/scripts/validate-day-plan-output.py -> scripts/validate-day-plan-output.py
- modules/planning/rules.md -> ai/rules/planning.md

После подтверждённой очистки пять выбранных пользователем прежних отмен имеют логический терминал `restoration_forfeited`. Он подтверждает исходные доказательства, точное согласие и отсутствие UUID в полном активном наборе; он не подменяет состояние SDK. Остальные отмены продолжают проверяться обычным Native-статусом.

## Repository only

- modules/planning/tests/

## Reads

- файлы задач

## Writes

- контекст рабочего процесса и предложения плана дня
- снимки календаря `ai/tmp/calendar-snapshots`
- наблюдения о расхождениях календаря в `ai/workflow-observations.md`, когда установлен learning

## Subscribes

- before-task-write: следовать ai/rules/planning.md § before-task-write
- after-calendar-change: следовать ai/rules/planning.md § after-calendar-change
