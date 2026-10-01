# Dated Task and Calendar Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a day-plan statement with any resolved date create one confirmed project-task update and timed calendar-block proposal.

**Architecture:** The day-plan resource resolves relative and explicit dates in the calendar timezone. It preserves explicit intervals, otherwise finds a 30-minute free interval, records it in `Запланировано:`, and pairs the task diff with the guarded calendar preview. The template is the release source; the active Hub receives it only through its preview-and-confirm release path.

**Tech Stack:** Markdown skill contracts, Bash smoke checks, Python unittest, guarded Apple Calendar MCP.

## Global Constraints

- Never apply a task or calendar change without a fresh exact confirmation.
- Do not move existing events to find an interval.
- Date-only requests use 30 minutes; explicit intervals are unchanged.
- Past dates do not imply completion.
- Event titles follow `категория/проект/задача` in lowercase.

---

### Task 1: Specify and test the day-plan pairing contract

**Files:**
- Modify: `tests/test_hub_workflows_progressive.py`
- Modify: `hub-template/ai/skills/hub-workflows/resources/day-plan.md`
- Modify: `hub-template/ai/architecture.md`

**Interfaces:**
- Consumes: a user statement with a resolvable date, canonical project-task record, and the allowlisted calendar read.
- Produces: a task diff containing `Запланировано: YYYY-MM-DD HH:MM-HH:MM` and one matching `hub-calendar` preview.

- [ ] **Step 1: Write the failing contract test**

Add this method to `tests/test_hub_workflows_progressive.py`:

```python
    def test_dated_day_plan_actions_pair_task_and_timed_event(self):
        day_plan = (RESOURCE_DIR / "day-plan.md").read_text(encoding="utf-8")
        for phrase in (
            "relative and explicit dates",
            "30-minute free interval",
            "Запланировано: YYYY-MM-DD HH:MM-HH:MM",
            "explicit interval unchanged",
            "past date does not infer completion",
            "one confirmation may approve only that exact pair",
        ):
            self.assertIn(phrase, day_plan)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_hub_workflows_progressive.HubWorkflowProgressiveDisclosureTests.test_dated_day_plan_actions_pair_task_and_timed_event -v`

Expected: FAIL because the day-plan resource lacks the dated-action contract.

- [ ] **Step 3: Add the minimal workflow and architecture wording**

Add this paragraph to `## Editing the plan` in `hub-template/ai/skills/hub-workflows/resources/day-plan.md`:

```markdown
For a new or changed action with relative and explicit dates, resolve the date
in the calendar timezone. Preserve an explicit interval unchanged. A date-only
statement uses the first 30-minute free interval on that date; never move an
existing event. Put the result in `Запланировано: YYYY-MM-DD HH:MM-HH:MM` in
the exact task diff and show its complete calendar preview beside it. One
confirmation may approve only that exact pair. A past date does not infer
completion.
```

Replace the day-plan paragraph in `hub-template/ai/architecture.md` so every
dated explicit action produces this paired timed proposal.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `python3 -m unittest tests.test_hub_workflows_progressive.HubWorkflowProgressiveDisclosureTests.test_dated_day_plan_actions_pair_task_and_timed_event -v`

Expected: PASS.

- [ ] **Step 5: Run contract checks**

Run: `python3 -m unittest discover -s tests -p 'test_hub_workflows_progressive.py' -v && bash scripts/check-consistency.sh && bash scripts/hub-smoke-test.sh`

Expected: all checks pass.

- [ ] **Step 6: Commit**

Run: `git add tests/test_hub_workflows_progressive.py hub-template/ai/skills/hub-workflows/resources/day-plan.md hub-template/ai/architecture.md && git commit -m "feat: pair dated day-plan tasks with calendar blocks"`

### Task 2: Release the confirmed contract into the active Hub

**Files:**
- Modify through release tool: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/architecture.md`
- Modify through release tool: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/skills/hub-workflows/resources/day-plan.md`

**Interfaces:**
- Consumes: the committed source release and the active Hub directory.
- Produces: the same contract in the active Hub; no calendar event is created during release.

- [ ] **Step 1: Produce a release preview**

Run: `bash scripts/update-installed-hub.sh --dry-run --source /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture --hub /Users/zykovsrg/Documents/vibecode/_ai-hub`

Expected: a finite list of managed-file changes and a plan SHA256.

- [ ] **Step 2: Show the exact preview and request confirmation**

Show only the release-listed files and plan SHA256. Do not apply yet.

- [ ] **Step 3: Apply the confirmed preview**

Repeat the Step 1 command with `--apply` and pass the exact `Plan SHA256` printed
by that reviewed preview to `--confirm-plan`.

Expected: the active Hub receives the reviewed managed-file changes.

- [ ] **Step 4: Verify the active Hub matches the source**

Run: `bash scripts/update-installed-hub.sh --check --source /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture --hub /Users/zykovsrg/Documents/vibecode/_ai-hub`

Expected: `Hub managed files match the selected release.`
