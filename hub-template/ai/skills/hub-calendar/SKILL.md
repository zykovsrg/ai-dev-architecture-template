---
name: hub-calendar
type: worker
description: Safely read selected Apple Calendar calendars and prepare one-time confirmed changes.
---

# Hub Calendar

Use only the guarded local Apple Calendar MCP. Never configure or call the raw
upstream MCP. The local source is pinned; automatic updates are forbidden.

Read only calendar IDs listed in the local allowlist. Never infer IDs from
names. Every read response must state `Apple Calendar / EventKit` and its IANA
timezone. Reads never change events.

For a calendar read, call `list_calendar_metadata` first. Its returned entries
are the authoritative list of available allowed calendars; use only their IDs
in `read_events`. A successful empty response means the allowlist has no
available calendar. Do not report an empty allowlist when this call was not
made or failed: state instead whether the calendar bridge is unavailable or
permission was denied.

Для создания и явного переименования используй название
`категория/проект/задача`. Каждая часть обязательна, набрана строчными
буквами, а `/` не окружён пробелами. Предпочитай категории `маша`,
`хадасса`, `дела`, `буся`, `веснушка`, `друзья`; новая категория допустима,
только если ни одна из них не подходит. Не переименовывай существующее
событие автоматически ради этого правила.

For create, update, or delete, first show a complete preview: action, calendar,
title, start/end with timezone, existing event ID, recurrence scope, and exact
effect. Apply only the matching one-time preview confirmation. A confirmation
never authorizes another change.

One exception keeps the preview but merges the gate: when a change is the
calendar side of an approved task write in `hub-task-intake`,
`hub-task-switch`, or `hub-task-finish`, that workflow shows the task diff and
this complete preview on one screen, and one confirmation approves exactly that
shown pair. Nothing else is merged: the preview stays complete, an unshown or
changed event still needs its own confirmation, and the confirmation dies with
the screen it belongs to. Do not create background checks, notifications,
task-to-calendar transfers, or files containing events, secrets, or tokens.

An authorized writable calendar may update or delete events whether they are
past or future. For a recurring event require exactly `this` or `future` scope and the
start of the occurrence being changed. Every occurrence of a series shares
one identifier, so without that date the change would hit the series.

macOS Calendar access is requested only after a separate user confirmation.
The allowlist starts empty and is changed only after the user selects exact IDs.

## Snapshot after a change

After a successful `apply_change`, re-read the affected day through
`read_events` and pass its events to
`bash scripts/snapshot-calendar.sh --hub <hub> --at <affected-date>-<HHMM>`.
Use one `HH:MM|HH:MM|<title>|<calendar>` line per event in start-time order.
This is a noncanonical cache, needs no additional confirmation, and a snapshot
failure must be reported without undoing the already applied calendar change.
