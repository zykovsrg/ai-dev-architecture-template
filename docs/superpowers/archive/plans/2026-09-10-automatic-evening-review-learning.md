# Automatic Evening Review Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one guarded MCP call prepare all calendar and learning inputs for an evening review.

**Architecture:** A lifecycle module inside the guarded Calendar service reads only allowed calendars, writes a noncanonical snapshot, and returns prior snapshots and pending friction. The MCP tool cannot change tasks, events, observations, or rules; the workflow then requires that tool before rendering the review.

**Tech Stack:** Python 3.11+, FastMCP, Pydantic, pytest, pytest-asyncio.

## Global Constraints

- The only new write is under `ai/tmp/calendar-snapshots/`.
- Calendar permission, allowlist, timezone, and date checks fail closed.
- Learning proposals remain confirmation-gated.

---

### Task 1: Implement a safe lifecycle reader

**Files:**
- Create: `calendar-policy/src/hub_calendar_policy/evening_review.py`
- Modify: `calendar-policy/src/hub_calendar_policy/server.py`
- Test: `calendar-policy/tests/test_evening_review.py`

**Interfaces:** `GuardedCalendarServer.prepare_evening_review(day: str, timezone: str) -> dict[str, object]` returns `events`, `snapshot`, `prior_snapshots`, and `pending_friction`.

- [ ] **Step 1: Write failing tests.**

```python
@pytest.mark.asyncio
async def test_prepare_evening_review_returns_snapshot_and_pending_friction(tmp_path, server):
    source = tmp_path / "ai/tmp/workflow-friction/2026-09-10.txt"
    source.parent.mkdir(parents=True)
    source.write_text("calendar overlap\n", encoding="utf-8")
    result = await server.prepare_evening_review("2026-09-10", "Europe/Kirov")
    assert [event["title"] for event in result["events"]] == ["Planning"]
    assert Path(result["snapshot"]).is_file()
    assert result["pending_friction"][0]["text"] == "calendar overlap"
    assert server._backend.writes == []
```

- [ ] **Step 2: Verify RED.** Run `python3 -m pytest calendar-policy/tests/test_evening_review.py -v`; expect `AttributeError` for `prepare_evening_review`.

- [ ] **Step 3: Implement the minimal service.** Add `day_bounds(day, timezone)`, `snapshot_lines(events)`, and a read-only pending-friction parser using the existing SHA-256 identifier format. The server must call `_require_permission`, authorize only `self._policy.allowed_calendar_ids`, read events once, and create a snapshot only after that read succeeds.

- [ ] **Step 4: Verify GREEN.** Run `python3 -m pytest calendar-policy/tests/test_evening_review.py -v`; expect PASS.

- [ ] **Step 5: Commit.** Run `git add calendar-policy/src/hub_calendar_policy/evening_review.py calendar-policy/src/hub_calendar_policy/server.py calendar-policy/tests/test_evening_review.py` then `git commit -m "feat: prepare evening review learning inputs"`.

### Task 2: Add the guarded MCP surface

**Files:**
- Modify: `calendar-policy/src/hub_calendar_policy/mcp_server.py`
- Modify: `calendar-policy/src/hub_calendar_policy/__main__.py`
- Test: `calendar-policy/tests/test_mcp_surface.py`
- Test: `calendar-policy/tests/test_entrypoint_config.py`

**Interfaces:** MCP tool `prepare_evening_review(date: str, timezone: str) -> dict[str, object]`; `HUB_ROOT` is an absolute non-symlink directory selected by server configuration.

- [ ] **Step 1: Write failing tests.** Assert `prepare_evening_review` is in `await mcp.list_tools()`. Assert relative or missing `HUB_ROOT` raises `ConfigError` before Calendar access.

- [ ] **Step 2: Verify RED.** Run `python3 -m pytest calendar-policy/tests/test_mcp_surface.py calendar-policy/tests/test_entrypoint_config.py -v`; expect missing-tool and missing-loader failures.

- [ ] **Step 3: Implement transport.** Add the tool to `build_mcp`; load and validate `HUB_ROOT` in `__main__.py`; pass it to `GuardedCalendarServer`. Do not accept a hub path from the MCP client.

- [ ] **Step 4: Verify GREEN.** Run `python3 -m pytest calendar-policy/tests/test_mcp_surface.py calendar-policy/tests/test_entrypoint_config.py calendar-policy/tests/test_evening_review.py -v`; expect PASS.

- [ ] **Step 5: Commit.** Run `git add calendar-policy/src/hub_calendar_policy/mcp_server.py calendar-policy/src/hub_calendar_policy/__main__.py calendar-policy/tests/test_mcp_surface.py calendar-policy/tests/test_entrypoint_config.py` then `git commit -m "feat: expose evening review lifecycle tool"`.

### Task 3: Require the lifecycle in the workflow

**Files:**
- Modify: `hub-template/ai/skills/hub-workflows/SKILL.md`
- Modify: `scripts/check-consistency.sh`
- Modify: `scripts/hub-smoke-test.sh`

**Interfaces:** A calendar-only evening review first calls `prepare_evening_review`; its response supplies calendar events, history, and pending friction.

- [ ] **Step 1: Write a failing contract check.** Add `grep -Fq 'prepare_evening_review' hub-template/ai/skills/hub-workflows/SKILL.md || { echo 'MISSING [evening review lifecycle] — required MCP tool'; exit 1; }` to the consistency check.

- [ ] **Step 2: Verify RED.** Run `bash scripts/check-consistency.sh`; expect the new missing-lifecycle error.

- [ ] **Step 3: Implement the workflow change.** Require the tool before every calendar-only evening review; retain separate confirmation for any observation or rule.

- [ ] **Step 4: Verify GREEN.** Run `python3 -m pytest calendar-policy/tests -v && bash scripts/assistant-workflows-test.sh && bash scripts/check-consistency.sh && bash scripts/smoke-test.sh`; expect PASS.

- [ ] **Step 5: Commit.** Run `git add hub-template/ai/skills/hub-workflows/SKILL.md scripts/check-consistency.sh scripts/hub-smoke-test.sh` then `git commit -m "fix: require automatic evening review learning"`.

## Self-Review

- Tasks 1–2 make lifecycle collection automatic at the guarded tool boundary.
- Task 3 prevents the workflow from omitting that boundary.
- No durable learning write bypasses confirmation.

## Execution Handoff

Execute inline with `superpowers:executing-plans`; this is one tightly coupled feature.
