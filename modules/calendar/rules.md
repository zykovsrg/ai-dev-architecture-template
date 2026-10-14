# Calendar Module Rules

## Guarded Apple Calendar

Apple Calendar uses only `hub-calendar` and the pinned local guarded MCP.
Raw upstream tools are forbidden. The allowlist is empty by default and may
contain only user-selected stable calendar IDs. Reads require explicit IDs and
IANA timezone and return their EventKit source. Every write uses a fresh,
single-use preview; create and update previews are applied immediately without
asking the user, and only delete previews wait for the user's confirmation
(see Write Confirmation Policy in `ai/architecture.md`). An authorized writable calendar may update or
delete events regardless of whether they are past or future; recurring writes
require `this` or `future`. A delete removes only one single event, never a
series, and is reported only after the tool confirms the event is gone. No background checks, notifications, secrets, or
calendar content are stored in architecture files. Updates are audited; only deletions are
separately confirmed.

Before a workflow reads a day, it calls `list_calendar_metadata`; the returned
allowed entries are the only source for the IDs sent to `read_events`. A missing
or failed metadata response must be reported as bridge unavailability or denied
permission, never as an empty allowlist.

The user's work meetings go into the calendar «Важно и срочно» (moved from
learned rule R-3, user decision 2026-10-08).
