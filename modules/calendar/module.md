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

- hub-template/ai/skills/hub-calendar/ -> ai/skills/hub-calendar/

## Repository only

- calendar-policy/
- scripts/sync-calendar-policy.sh
- scripts/grant-calendar-access.sh
- scripts/build-calendar-bridge.sh

## Reads

- selected Apple Calendar calendars

## Writes

- calendar events, only through a previewed and confirmed change

## Subscribes

- —
