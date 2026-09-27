# Module: planning

Id: planning
Required: no
Switchable: no
Depends: core, projects, tasks, calendar
Uses if present: goals, learning
Rules: —
Keywords: —

## Purpose

Day-plan, evening-review and weekly-review workflows, combining tasks with
the calendar snapshot.

## Installs

- hub-template/ai/skills/hub-workflows/ -> ai/skills/hub-workflows/
- hub-template/ai/workflow-context.md -> ai/workflow-context.md
- scripts/snapshot-calendar.sh -> scripts/snapshot-calendar.sh
- scripts/calendar-context.py -> scripts/calendar-context.py
- scripts/calendar_task_sync.py -> scripts/calendar_task_sync.py
- scripts/validate-day-plan-output.py -> scripts/validate-day-plan-output.py

## Repository only

- —

## Reads

- task files

## Writes

- workflow context and day-plan proposals
- calendar snapshots `ai/tmp/calendar-snapshots`

## Subscribes

- —
