# Module: tasks

Id: tasks
Required: yes
Switchable: no
Depends: core, projects
Uses if present: —
Rules: —
Keywords: —

## Purpose

Task record lifecycle for a registered project: intake, switch, finish and
environment checks, backed by the compact task index.

## Installs

- hub-template/ai/skills/hub-task-intake/ -> ai/skills/hub-task-intake/
- hub-template/ai/skills/hub-task-switch/ -> ai/skills/hub-task-switch/
- hub-template/ai/skills/hub-task-finish/ -> ai/skills/hub-task-finish/
- hub-template/ai/skills/hub-environment-check/ -> ai/skills/hub-environment-check/
- scripts/read-compact-task-index.py -> scripts/read-compact-task-index.py
- scripts/task_records.py -> scripts/task_records.py
- scripts/check-all-task-records.sh -> scripts/check-all-task-records.sh
- scripts/lib/calendar-date.sh -> scripts/lib/calendar-date.sh

## Repository only

- —

## Reads

- project task files

## Writes

- project task files

## Subscribes

- —
