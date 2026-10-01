# Non-recurring Calendar Event Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let ordinary Apple Calendar events apply through their verified ID lookup without an unnecessary occurrence-time lookup.

**Architecture:** `EventKitBackend` will include `occurrence_start` only for a recurring request. The guarded bridge keeps its exact occurrence lookup for recurring series, while ordinary events use the successful preview identity path. The tested source policy is then synchronised into the local hub.

**Tech Stack:** Python 3.14, pytest, pytest-asyncio, Swift/EventKit bridge, Bash installer.

## Global Constraints

- Preserve the calendar allowlist, single-use preview, and separate confirmation.
- Do not read or change calendar contents during installation.
- Do not send `occurrence_start` for non-recurring updates or deletes.
- Preserve `occurrence_start` for recurring updates or deletes.

---

### Task 1: Build correct bridge payloads

**Files:**

- Modify: `calendar-policy/src/hub_calendar_policy/eventkit_backend.py:82-97`
- Modify: `calendar-policy/tests/test_eventkit_backend.py:142-182`
- Test: `calendar-policy/tests/test_eventkit_backend.py`

**Interfaces:**

- Consumes: `EventRef`, `ChangeRequest.recurring`, `ChangeRequest.recurrence_scope`.
- Produces: update and delete bridge payloads that include `occurrence_start` only for recurring events.

- [ ] **Step 1: Write failing tests**

Replace the ordinary-delete expectation and add an ordinary-update expectation:

```python
assert "occurrence_start" not in payload
```

Keep the recurring payload test with:

```python
assert payload["occurrence_start"] == original.start.isoformat()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=calendar-policy/src calendar-policy/.venv/bin/python -m pytest calendar-policy/tests/test_eventkit_backend.py -q
```

Expected: ordinary-event payload assertions fail because the backend currently always adds `occurrence_start`.

- [ ] **Step 3: Write minimal implementation**

Build update and delete payloads, then add this field only when `request.recurring` is true:

```python
if request.recurring:
    payload["occurrence_start"] = event.start.isoformat()
```

For delete, use the same condition and add no other fallback matching.

- [ ] **Step 4: Run tests to verify they pass**

Run the Step 2 command.

Expected: all EventKit backend tests pass.

- [ ] **Step 5: Run full policy verification**

Run:

```bash
bash scripts/apple-calendar-policy-test.sh
bash scripts/check-consistency.sh
git diff --check
```

Expected: all calendar-policy tests pass; consistency and diff checks pass.

- [ ] **Step 6: Synchronise the tested policy into the hub and restart MCP**

Run:

```bash
bash scripts/sync-calendar-policy.sh --source /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture --hub /Users/zykovsrg/Documents/vibecode/_ai-hub
```

Then restart only the active `python -m hub_calendar_policy` processes. Confirm that the installed policy source equals the project source before reporting completion.
