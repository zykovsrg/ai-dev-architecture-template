# Rolling calendar context

Maintain one local noncanonical file `<hub>/ai/tmp/calendar-context.json`.
Never commit or publish event data. This cache is separate from snapshots and
their 14-day retention. Maintain it only when day planning is invoked.

## Window and data

Let D be today's local calendar date. Store 30 complete past days [D-30,D),
today [D,D+1), and 30 future days [D+1,D+31). Ends are exclusive local
midnights; use calendar dates, not fixed 24-hour offsets across DST.
Analyze the past window and next 14 days [D+1,D+15), anchored on today's plan.

JSON fields: schema_version=1, anchor_date, timezone (IANA), calendar_ids,
and days keyed by YYYY-MM-DD. Each day contains fetched_at and events.
Store only IDs, exact titles, start/end, all-day flags, timezone and source
from guarded MCP responses. Omit descriptions and attendees. Successfully
read empty days have events=[]; missing coverage is never an empty day.

## Update procedure

- Before ingesting each response, require `availability_complete: true` and an empty `unavailable_calendar_ids`. If coverage is partial, skip ingest for that range, preserve prior cache contents, and report the coverage as missing or stale. A partial response with `events: []` is never evidence of an empty calendar.
- Run `scripts/calendar-context.py plan --hub <hub> --anchor <D>
  --timezone <IANA> --calendar-id <allowed-id>` (repeat `--calendar-id` for
  each allowed calendar). For every returned half-open range, call guarded
  `read_events`, then run `calendar-context.py ingest` with the same hub,
  anchor, timezone and IDs plus that `--start` and `--end`. Send the complete
  MCP JSON response to the process on stdin and then close stdin. Do not
  hand-edit the cache.
- First run: resolve allowed calendar IDs through hub-calendar; fetch the
  past and future windows once using guarded read_events, plus today's normal
  calendar read. Split requests to respect tool range limits and pagination.
- Next day: discard the oldest past date and fetch the new far-future date.
  Moving D to D+1 discards D-30 and adds D+31. Retain the overlap; yesterday's
  today becomes history. Replace today's bucket using the normal fresh read.
- Same-day reruns add no extra day. After missed days, prune outside the new
  window and fetch all missing dates. Rebuild on nonoverlapping windows,
  malformed data, changed timezone or changed allowed-calendar selection;
  revoked calendars must not be used.
- Include events overlapping a date, including multi-day/all-day events.
  Deduplicate analysis by calendar ID, event ID and occurrence start so
  recurring instances remain distinct and multi-day events count once.
- Validate and atomically replace the file through a staged write; reject
  symlink targets. Failed fetches preserve valid prior data. Report missing
  or stale coverage and do not mark an unsuccessful read as current.
  No MCP access means unavailable context, not an empty history.

The first real day-plan run initializes this buffer. Do not fabricate an
initial buffer during architecture installation and do not schedule a job.

## Freshness and recommendations

Rolling extension cannot discover edits to retained dates. After a
calendar edit, refresh affected buffered dates. Before using a retained future
event for a recommendation, re-read its date and replace that bucket so moved
or deleted events cannot support advice. Label historical data as a snapshot:
a past scheduled event does not prove completion or actual time spent.

Read permitted canonical project tasks for deadlines, remaining actions and
reported completion. An ordinary event date is not necessarily a deadline.
Unknown effort or capacity stays unknown; do not infer publication output from
SEO calendar blocks alone.

For joint planning, use the past 30 days and next 14 days to assess today's
work against verified deadlines and remaining canonical actions. Keep this
analysis internal until a user planning decision needs it; there is no separate
recommendation section. State uncertainty and cite supporting task/event dates
when discussing a decision. Missing context is a limitation under
`## Синхронизация`, never evidence of free time or completed work.
Accepted user decisions follow the normal task/calendar write flow; analysis
alone changes neither project records nor calendar events.
