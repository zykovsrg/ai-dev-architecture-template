# Модуль: calendar

Id: calendar
Required: no
Switchable: yes
Depends: core
Uses if present: —
Rules: ai/rules/calendar.md
Keywords: —

## Purpose

Безопасно читать выбранные календари Apple Calendar и применять изменения
через одноразовый просмотр; только удаления ждут согласия пользователя.

## Installs

- modules/calendar/rules.md -> ai/rules/calendar.md
- modules/calendar/skills/hub-calendar/ -> ai/skills/hub-calendar/

## Repository only

- modules/calendar/policy/
- modules/calendar/scripts/sync-calendar-policy.sh
- modules/calendar/scripts/grant-calendar-access.sh
- modules/calendar/scripts/build-calendar-bridge.sh
- modules/calendar/tests/

## Reads

- выбранные календари Apple Calendar

## Writes

- события календаря, только через одноразовый просмотр; удаление — после согласия пользователя

## Subscribes

- —
