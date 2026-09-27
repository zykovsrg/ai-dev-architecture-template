# Module: goals

Id: goals
Required: no
Switchable: no
Depends: core, projects
Uses if present: —
Rules: ai/rules/goals.md
Keywords: —

## Purpose

Track progress toward numeric hub goals and append confirmed progress
entries to the canonical goal log.

## Installs

- modules/goals/rules.md -> ai/rules/goals.md
- hub-template/ai/skills/hub-goal-progress/ -> ai/skills/hub-goal-progress/
- hub-template/ai/goal-log.md -> ai/goal-log.md
- hub-template/ai/goals.md -> ai/goals.md
- scripts/count-goal-progress.sh -> scripts/count-goal-progress.sh

## Repository only

- —

## Reads

- the goal log

## Writes

- the goal log

## Subscribes

- —
