# Calendar Partial Read Design

## Problem

An allowlisted calendar may appear in EventKit metadata and then disappear
between metadata lookup and event retrieval. The guarded server currently
aborts the whole request with `CALENDAR_UNAVAILABLE`, hiding events from the
other calendars that remain readable.

## Decision

Keep the explicit allowlist and process each requested calendar independently.
Return events from calendars that can be read, plus a structured
`unavailable_calendar_ids` field naming any calendars skipped because EventKit no
longer resolves them. Permission failures, malformed requests, and unrelated
bridge errors still fail the complete operation.

Apply this behavior to event reads and free-slot reads. For evening review,
keep its event result and snapshot consistent: if any configured calendar is
unavailable, do not create a snapshot from incomplete data; report the
unavailable IDs with the events and leave the snapshot unchanged.

Consumers must treat a non-empty `unavailable_calendar_ids` list as partial data
and must not claim the day is free. The calendar workflow documentation will
state this rule. No allowlist change or calendar write is included.

## Scope

- Guarded server response and per-calendar read handling.
- Focused regression coverage for mixed available/unavailable calendars and
  unchanged fail-closed behavior for permission and malformed-request errors.
- Calendar workflow guidance for partial responses.

## Alternatives considered

1. Remove Birthdays from the allowlist. This is a quick workaround but hides
   birthday events and does not make reads resilient to other transiently
   unavailable calendars.
2. Retry the entire read. This may repeat the same failure and still prevents
   usable calendars from being read.

## Success criteria

- If one requested calendar disappears while other requested calendars are
  readable, the response contains the readable events and identifies the
  unavailable calendar explicitly.
- Consumers surface partial-data status and do not present the response as a
  fully verified schedule.
- Permission denial and non-calendar bridge failures remain errors.
- Existing all-readable behavior is unchanged.
