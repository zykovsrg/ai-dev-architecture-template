# Module: calendar

Id: calendar
Required: no
Switchable: yes
Depends: core
Uses if present: —
Rules: —
Keywords: —

## Purpose

Read selected Apple Calendar calendars safely and prepare one-time confirmed
changes.

## Installs

- modules/calendar/skills/hub-calendar/ -> ai/skills/hub-calendar/

## Repository only

- modules/calendar/policy/
- modules/calendar/scripts/sync-calendar-policy.sh
- modules/calendar/scripts/grant-calendar-access.sh
- modules/calendar/scripts/build-calendar-bridge.sh
- modules/calendar/tests/

## Reads

- selected Apple Calendar calendars

## Writes

- calendar events, only through a previewed and confirmed change

## Subscribes

- —
