# Calendar Partial Reads Implementation Plan

> **For agentic workers:** Implement this plan task by task. Keep each change
> focused and run the named regression checks.

**Goal:** Keep calendar reads useful when one allowlisted calendar disappears
  during an EventKit read, while clearly marking incomplete results.

**Architecture:** The guarded server will read each requested calendar
  independently and return unavailable calendar IDs alongside readable
  events. A partial free-slot result will contain no claimed free slots, and an
  evening review will not replace its snapshot with incomplete data.

**Tech Stack:** Python 3.11+, Pydantic, pytest, local Swift/EventKit bridge.

## Global Constraints

- Read only calendar IDs explicitly configured in the existing allowlist.
- Continue to fail on permission denial, invalid timezone/range, and unrelated
  bridge errors.
- Never report partial free-slot results as available time.
- Do not write calendar snapshots from partial event data.

---

### Task 1: Isolate unavailable calendars during event reads

**Files:**
- Modify: `calendar-policy/src/hub_calendar_policy/server.py`
- Test: `calendar-policy/tests/test_server.py`
- Test support: `calendar-policy/tests/fake_backend.py`

**Interfaces:**
- Add one internal helper returning `(events, unavailable_calendar_ids)`.
- `read_events` returns `events` and `unavailable_calendar_ids`.

- [ ] Add a fake-backend scenario where one allowlisted calendar disappears
  between metadata validation and event retrieval.
- [ ] Run the focused test and confirm the current implementation fails by
  raising `CALENDAR_UNAVAILABLE` or `CALENDAR_NOT_FOUND`.
- [ ] Implement per-calendar reads, skipping only those two missing-calendar
  errors; re-raise permission and all unrelated failures.
- [ ] Return a stable sorted list of unavailable calendar IDs with the events.
- [ ] Run the focused test and the complete calendar-policy test suite.

### Task 2: Prevent unsafe derived availability and snapshots

**Files:**
- Modify: `calendar-policy/src/hub_calendar_policy/server.py`
- Test: `calendar-policy/tests/test_server.py`

**Interfaces:**
- `find_free_slots` returns no slots and the unavailable IDs when any requested
  calendar could not be read.
- `prepare_evening_review` returns partial events and unavailable IDs, with no
  new snapshot written when the event set is incomplete.

- [ ] Add failing tests for no free-slot claims and unchanged snapshot state on
  a partial read.
- [ ] Run the focused tests to verify those failures occur for the intended
  reason.
- [ ] Implement safe behavior using the Task 1 helper.
- [ ] Run the focused tests and complete calendar-policy suite.

### Task 3: Document partial responses

**Files:**
- Modify: `hub-template/ai/skills/hub-calendar/SKILL.md`
- Test: `calendar-policy/tests/test_mcp_surface.py` (only if response shape is
  asserted there)

- [ ] Document that consumers must surface `unavailable_calendar_ids` and
  treat event data as incomplete; free-slot results with unavailable IDs are
  unusable.
- [ ] Run documentation checks and the focused API-surface tests.
- [ ] Review the final diff and report that deployment of the changed local
  connector is a separate operational step if the running MCP is packaged from
  another location.
