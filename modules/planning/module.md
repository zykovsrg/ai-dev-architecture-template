# Module: planning

Id: planning
Required: no
Switchable: yes
Depends: core, projects, tasks, calendar
Uses if present: goals, learning
Rules: ai/rules/planning.md
Keywords: —

## Purpose

Day-plan, evening-review and weekly-review workflows, combining tasks with
the calendar snapshot.

## Installs

- modules/planning/skills/hub-workflows/ -> ai/skills/hub-workflows/
- modules/planning/data/ai/workflow-context.md -> ai/workflow-context.md
- modules/planning/scripts/snapshot-calendar.sh -> scripts/snapshot-calendar.sh
- modules/planning/scripts/calendar-context.py -> scripts/calendar-context.py
- modules/planning/scripts/calendar_task_sync.py -> scripts/calendar_task_sync.py
- modules/planning/scripts/calendar_drift.py -> scripts/calendar_drift.py
- modules/planning/scripts/validate-day-plan-output.py -> scripts/validate-day-plan-output.py
- modules/planning/rules.md -> ai/rules/planning.md

## Repository only

- modules/planning/tests/

## Reads

- task files

## Writes

- workflow context and day-plan proposals
- calendar snapshots `ai/tmp/calendar-snapshots`
- calendar drift observations in `ai/workflow-observations.md` when learning is installed

## Subscribes

- before-task-write: follow ai/rules/planning.md § before-task-write
- after-calendar-change: follow ai/rules/planning.md § after-calendar-change
