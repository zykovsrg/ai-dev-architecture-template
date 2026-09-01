# Non-recurring Calendar Event Resolution

## Problem

The EventKit bridge can find a non-recurring event during preview but fail with
`EVENT_NOT_FOUND` during apply. The backend always adds `occurrence_start` to
an update or delete payload. That forces the bridge to use occurrence matching,
which is only required for recurring events.

## Decision

Send `occurrence_start` only when the request is recurring. A non-recurring
event is applied by its EventKit calendar-item identifier, the same identity
path that succeeded during preview.

## Scope

- Change the EventKit backend payload construction only.
- Preserve calendar allowlists, exact previews, explicit confirmation, and
  recurring-event scopes.
- Add regression tests for ordinary and recurring update/delete payloads.
- Install the tested policy into the confirmed hub and restart its MCP process.

## Success criteria

- A non-recurring event payload contains no `occurrence_start`.
- A recurring event payload still contains the selected occurrence start.
- The calendar-policy test suite passes.
