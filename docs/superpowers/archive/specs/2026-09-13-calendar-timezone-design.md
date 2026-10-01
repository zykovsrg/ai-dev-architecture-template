# Calendar event timezone serialization

## Goal

Calendar events read through the local EventKit bridge must preserve the
event's calendar timezone in their ISO 8601 timestamps. A day plan in
`Europe/Kirov` must therefore show the same wall-clock time as Apple Calendar.

## Evidence

The bridge currently serializes `Date` through an `ISO8601DateFormatter` with
its default UTC timezone, producing timestamps ending in `Z`. It separately
labels those events `Europe/Kirov`. Consumers that correctly parse the
timestamp receive an absolute UTC instant, while consumers that render it as
local time can show a three-hour shift.

## Chosen design

Change only the bridge serializer. For each event, format `start` and `end`
using that event's timezone; when EventKit does not provide one, use the local
timezone already reported by the bridge. The timestamp's offset must match the
reported timezone.

Keep the existing all-day inclusive-to-exclusive conversion unchanged. Add a
regression test that uses a Kirov event and checks that the serialized value
has `+03:00` and the expected local clock time.

## Alternatives rejected

1. Convert time in every workflow renderer. This duplicates logic and leaves
   other clients exposed to the same mismatch.
2. Document that clients must reinterpret UTC as local time. This contradicts
   ISO 8601 semantics and remains error-prone.

## Acceptance criteria

- Timed events serialize with the event or local fallback timezone offset.
- A Kirov test proves no three-hour shift.
- Existing all-day and calendar-policy tests remain green.
