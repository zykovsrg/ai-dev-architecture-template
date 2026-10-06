# Module: tasks

Id: tasks
Required: yes
Switchable: no
Depends: core, projects
Uses if present: —
Rules: ai/rules/tasks.md
Keywords: —

## Purpose

Task record lifecycle for a registered project: intake, switch, finish and
environment checks, backed by the compact task index.

## Installs

- modules/tasks/rules.md -> ai/rules/tasks.md
- modules/tasks/skills/hub-task-intake/ -> ai/skills/hub-task-intake/
- modules/tasks/skills/hub-task-switch/ -> ai/skills/hub-task-switch/
- modules/tasks/skills/hub-task-finish/ -> ai/skills/hub-task-finish/
- modules/tasks/skills/hub-environment-check/ -> ai/skills/hub-environment-check/
- modules/tasks/skills/hub-task-overview/ -> ai/skills/hub-task-overview/
- modules/tasks/scripts/read-compact-task-index.py -> scripts/read-compact-task-index.py
- modules/tasks/scripts/task_records.py -> scripts/task_records.py
- modules/tasks/scripts/seed_stage_template.py -> scripts/seed_stage_template.py
- modules/tasks/scripts/check-all-task-records.sh -> scripts/check-all-task-records.sh
- modules/tasks/scripts/lib/calendar-date.sh -> scripts/lib/calendar-date.sh

## Repository only

- —

## Reads

- project task files

## Writes

- project task files

## Subscribes

- —
