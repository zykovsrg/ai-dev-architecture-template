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

Every successful `read_events` and `find_free_slots` response includes
`availability_complete` and `unavailable_calendar_ids`. If that list is
non-empty, say the result is partial and name the affected IDs. Never describe
partial event data as a free day, use partial free-slot output to recommend
availability, ingest partial events into rolling context, or write a snapshot
from them. Partial `find_free_slots` responses contain no slots.

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

One exception keeps the preview but merges the gate: another installed module
may show this complete preview together with its own diff on one screen, and
one confirmation approves exactly that shown pair. Nothing else is merged: the
preview stays complete, an unshown or changed event still needs its own
confirmation, and the confirmation dies with the screen it belongs to. Do not
create background checks, notifications, task-to-calendar transfers, or files
containing events, secrets, or tokens.
Caches defined by an installed subscriber are cache exceptions. They authorize
neither publishing event data nor changing events.

An authorized writable calendar may update or delete events whether they are
past or future. For a recurring event require exactly `this` or `future` scope and the
start of the occurrence being changed. Every occurrence of a series shares
one identifier, so without that date the change would hit the series.

A `preview_change` response for a recurring event echoes the start of the
series, not the occurrence being changed. A preview whose `start` precedes the
requested date therefore identifies a series; this is expected and is not a
mismatch, so never treat it as an unsafe or wrong target. Send `recurring:
true`, `recurrence_scope: this`, and `occurrence_start` set to the start of the
occurrence being changed. A delete preview is the cheap way to learn whether an
event is a series before proposing any change to it.

macOS Calendar access is requested only after a separate user confirmation.
The allowlist starts empty and is changed only after the user selects exact IDs.

## after-calendar-change

After a successful `apply_change`, run the `after-calendar-change` event: read
`<hub>/ai/modules.md` and follow each subscriber's rules with the affected
calendar ID and date. A subscriber failure is reported and never undoes the
applied change.
