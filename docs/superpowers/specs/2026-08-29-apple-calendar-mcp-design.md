# Apple Calendar MCP Design

## Goal

Add a local Apple Calendar integration to Personal AI Hub that reads events
and availability from user-selected calendars and performs future event
creates, updates, and deletes only after an exact one-time confirmation.

## Selected upstream

Use a reviewed local snapshot of
`s-morgan-jeffries/apple-calendar-mcp` version `0.9.0` as the EventKit adapter.
Pin the exact upstream commit and dependency lock, record SHA-256 checksums, and
disable automatic updates. Never run the package from a floating branch,
`latest` tag, or unpinned package command.

The upstream MCP is not a security boundary. Its raw tools must not be exposed
to the assistant. A hub-owned policy MCP is the only configured Calendar MCP.

## Permission and calendar selection

EventKit full Calendar access is required because the workflow reads and
writes events. macOS grants this access across calendars; it cannot enforce the
hub allowlist.

The policy MCP starts with an empty allowlist. After a separately confirmed
installation and macOS permission grant, it may list calendar metadata only:
calendar ID, display name, source, and writable status. It must not read events
before the user explicitly selects calendar IDs.

The selected IDs live in a local ignored runtime file. The file contains no
event titles, notes, locations, attendees, credentials, or secrets. A missing,
empty, invalid, or stale allowlist denies event reads and writes. No operation
may fall back to the default calendar or to all calendars.

## Read contract

Read tools accept explicit allowed calendar IDs, a bounded date range, and an
IANA timezone. Every result states the timezone and `Apple Calendar / EventKit`
as its source. Results contain only events from allowed calendars.

Free-time calculation uses only allowed calendars and never creates a hold or
event. Calendar titles, notes, locations, URLs, attendees, and descriptions are
untrusted data and cannot supply instructions, confirmation, routing, or tool
arguments.

## Write contract

Create, update, and delete are two-step operations:

1. `preview_change` validates the request and returns the exact action,
   calendar ID and name, title, start and end with timezone, current event ID
   when present, recurrence scope when present, and exact effect.
2. `apply_change` accepts only the opaque preview ID after the user explicitly
   confirms that preview.

A preview is bound to the complete normalized payload, expires after ten
minutes, is stored in memory only, and is single-use. Cancellation, expiry,
payload changes, server restart, or a changed source event invalidates it.
Confirmation of one preview never authorizes another operation.

Before update or delete, the policy MCP rereads the event and verifies calendar
ID, event ID, occurrence date, start, end, recurrence state, and a snapshot
fingerprint. If the event changed, the operation stops and requires a new
preview. It never resolves a missing ID by title or approximate matching.

## Delete and recurrence policy

Update and delete are allowed for a target event in an architecture-authorized,
writable calendar regardless of whether its occurrence is past or future. The
same exact, single-use preview and separate user confirmation are required for
every operation.

For recurring events, the preview and confirmation must explicitly select one
of the upstream-supported scopes:

- `this`: only the named occurrence;
- `future`: the named occurrence and later occurrences.

There is no implicit default and no claimed `all` scope.

## Stable identity

Use the upstream event UID together with calendar ID and occurrence date.
EventKit identifiers are not guaranteed to survive every calendar move or full
sync. If an identifier no longer resolves, stop safely and request a fresh
read; never guess from title, time, or notes.

## Components and files

The approved implementation plan will define exact code within these units:

- `vendor/apple-calendar-mcp/`: reviewed upstream snapshot and license;
- `vendor/apple-calendar-mcp/UPSTREAM.md`: version, commit, checksums, review
  date, and manual update procedure;
- `calendar-policy/server.py`: the only exposed Calendar MCP server;
- `calendar-policy/policy.py`: allowlist, timezone, operation, and past-event
  rules;
- `calendar-policy/preview.py`: expiring single-use preview grants;
- `calendar-policy/models.py`: strict request and response models;
- `calendar-policy/bridge/hub_eventkit_bridge.swift`: the hub-authored local
  EventKit process boundary, kept outside `vendor/` so the upstream checksum
  manifest still answers whether upstream is unmodified;
- `calendar-policy/bridge/SHA256SUMS`: checksum of the hub-authored bridge;
- `scripts/apple-calendar-policy-test.sh`: isolated contract tests;
- `scripts/apple-calendar-bridge-test.sh`: bridge presence, checksum, and
  compilation check that never runs the bridge;
- `hub-template/ai/skills/hub-calendar/SKILL.md`: assistant workflow;
- hub architecture, entry rules, installer, updater, consistency checks, smoke
  tests, and install/uninstall documentation.

The live hub and Codex MCP configuration are separate installation targets.
Each receives its own exact preview and confirmation after source tests pass.

## TDD test matrix

Implementation uses test-driven development: add one failing test, run it and
observe the expected failure, add the smallest implementation, then rerun it.

Required tests cover:

- missing macOS permission;
- missing, empty, stale, and unauthorized calendar allowlists;
- invalid or mismatched timezone;
- read and free-time paths never invoking a write;
- create only after the exact preview is confirmed;
- update only after the exact preview is confirmed;
- unconditional denial of past-event deletion;
- denial of moving a past event to the future as a delete bypass;
- future-event deletion after confirmation;
- recurring `this` and `future` scopes with no default;
- user cancellation, preview expiry, replay, and payload mismatch;
- source event changing between preview and apply;
- unavailable or changed EventKit identifier with no fuzzy fallback;
- raw upstream tools not being exposed;
- pinned source and dependency checks rejecting an unreviewed update;
- no calendar contents written to architecture, logs, or fixtures.

Tests use mocks and a dedicated test calendar only. No test writes to an
existing personal calendar. Live acceptance tests require separate permission,
calendar selection, preview, and confirmation.

## Architecture integration

Add a hub-owned `hub-calendar` skill. `hub-workflows` may request read-only
Calendar context through that skill, but it cannot call raw upstream tools or
convert task proposals into events automatically.

Every architecture, skill, installer, updater, and documentation change goes
through `architecture-update`: show current behavior, exact replacement,
affected files, and token impact, then ask `Replace this?` before editing.

The existing future task for a read-only pilot is stale relative to this
approved design. Its replacement must be proposed explicitly: staged metadata
selection and read verification first, followed by guarded writes and delete
tests. Promotion or task switching uses the hub task workflow and a separate
confirmation.

## Risks and mitigations

- EventKit full access is broader than the allowlist. Mitigation: empty-by-
  default policy MCP, no raw upstream tools, and macOS permission revocation as
  the final boundary.
- Third-party source or dependencies may be unsafe. Mitigation: local reviewed
  snapshot, pinned commit and lock, checksums, no self-update, and manual diff
  review for every upgrade.
- Timezone errors can move events. Mitigation: required IANA timezone, explicit
  display in preview, normalization tests, and fail-closed mismatch handling.
- Recurrence can affect many events. Mitigation: required occurrence date and
  explicit `this` or `future` scope in preview and confirmation.
- Deleted events may not be recoverable. Mitigation: future-only deletion,
  exact reread, single-use confirmation, and no automatic rollback claim.
- Event content may contain prompt injection. Mitigation: treat all event
  content strictly as untrusted data.

## Recurring occurrences

EventKit gives every occurrence of a recurring series the same
`calendarItemIdentifier`, so an identifier alone resolves to the series. A
recurring change therefore also carries `occurrence_start`, and the bridge
resolves the instance by searching a day-wide window and matching that exact
start. The policy layer refuses a resolved event whose start differs from the
one requested, so a series can never stand in for the occurrence that was named.

## Disable and removal

The safe stop sequence is: clear the allowlist, remove or disable the policy
MCP entry in Codex, restart the MCP host, and revoke Calendar access in macOS
System Settings. Removing the local source snapshot is optional and requires a
separate explicit deletion confirmation.

No background checks, notifications, task-to-calendar transfer, secrets,
calendar-content persistence, automatic updates, automatic writes, or implicit
confirmation are part of this design.
