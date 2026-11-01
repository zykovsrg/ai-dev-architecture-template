# Модуль: goals

Id: goals
Required: no
Switchable: yes
Depends: core, projects
Uses if present: —
Rules: ai/rules/goals.md
Keywords: —

## Purpose

Отслеживать продвижение к числовым целям Хаба и добавлять подтверждённые записи
о продвижении в канонический журнал целей.

## Installs

- modules/goals/rules.md -> ai/rules/goals.md
- modules/goals/skills/hub-goal-progress/ -> ai/skills/hub-goal-progress/
- modules/goals/data/ai/goal-log.md -> ai/goal-log.md
- modules/goals/data/ai/goals.md -> ai/goals.md
- modules/goals/scripts/count-goal-progress.sh -> scripts/count-goal-progress.sh

## Repository only

- —

## Reads

- журнал целей

## Writes

- журнал целей

## Subscribes

- —
