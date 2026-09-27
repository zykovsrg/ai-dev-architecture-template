# Calendar Module Rules

## Guarded Apple Calendar

Apple Calendar uses only `hub-calendar` and the pinned local guarded MCP.
Raw upstream tools are forbidden. The allowlist is empty by default and may
contain only user-selected stable calendar IDs. Reads require explicit IDs and
IANA timezone and return their EventKit source. Every write requires a fresh,
single-use preview confirmation. An authorized writable calendar may update or
delete events regardless of whether they are past or future; recurring writes
require `this` or `future`. No background checks, notifications, secrets, or
calendar content are stored in architecture files. Updates are manual, audited,
and separately confirmed.

Before a workflow reads a day, it calls `list_calendar_metadata`; the returned
allowed entries are the only source for the IDs sent to `read_events`. A missing
or failed metadata response must be reported as bridge unavailability or denied
permission, never as an empty allowlist.
