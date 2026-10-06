---
name: hub-calendar
type: worker
description: Safely read selected Apple Calendar calendars and apply changes; only deletions wait for confirmation.
---

# Hub Calendar

Use only the guarded local Apple Calendar MCP. Never configure or call the raw
upstream MCP. The local source is pinned; automatic updates are forbidden.

Module rules: `ai/rules/calendar.md`.

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

Для создания и явного переименования события проекта бери название из
`python3 scripts/archiprojects.py calendar-title --hub <hub> --project <id> --task "<задача>"`.
Оно показывает всю доступную цепочку вложенности кириллицей: русские имена
групп архипроекта от корня, затем русское имя проекта, затем задачу, например
`хадасса/промостраницы/варикоцеле/доработать текст по комментариям врача`.
Проект без архипроекта даёт `<проект>/<задача>`. Общий проект группы
отмечен в карточке `Calendar name: —` и не добавляет своего уровня:
`хадасса/промостраницы/<задача>`. Имена берутся из
`calendar_name:` группы в `ai/archiprojects.md` и `Calendar name:` карточки
проекта. Событие без проекта называй `категория/задача` строчными буквами;
`/` не окружён пробелами. Не переименовывай существующее событие
автоматически ради этого правила. Старые названия вида
`категория/<project-id>/задача` продолжают распознаваться.

For create or update, call `preview_change`, check that the preview matches the
request (action, calendar, title, start/end with timezone, event ID, recurrence
scope), then call `apply_change` in the same turn without asking the user.
Afterwards report briefly what was created or changed. For delete, show the
complete preview and apply it only after the user's explicit yes; that yes
never authorizes another deletion. Do not create background checks,
notifications, task-to-calendar transfers, or files containing events,
secrets, or tokens.
Caches defined by an installed subscriber are cache exceptions. They authorize
neither publishing event data nor changing events.

An authorized writable calendar may update or delete events whether they are
past or future. For a recurring event require exactly `this` or `future` scope and the
start of the occurrence being changed. Every occurrence of a series shares
one identifier, so without that date the change would hit the series.

A delete always removes one single event, never a series: for an occurrence
send `recurring: true`, `recurrence_scope: this` and its `occurrence_start`;
`future` is refused for delete (`SERIES_DELETE_FORBIDDEN`). The tool checks
that the event is gone. If EventKit left the last occurrence as a standalone
event, the tool removes that same event once more. If the event still remains,
it reports `DELETE_NOT_APPLIED`: tell the user and do not report a deletion.
For an update, omit `title` unless the user asks to rename the event, and omit
`all_day` unless the change turns the event into or out of an all-day event:
an omitted `all_day` keeps the event's own flag.

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
