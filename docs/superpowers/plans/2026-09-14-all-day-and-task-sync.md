# All-day events and task-state synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make day planning and evening review render all-day events verbatim and turn confirmed user task decisions into synchronized canonical-record and calendar changes.

**Architecture:** The workflow templates remain the source of conversational behavior. A focused regression suite asserts the mandatory wording, one-event-per-line rule, exact proposal/diff requirement, and paired calendar confirmation; the Hub architecture document states the invariant shared by both workflows.

**Tech Stack:** Markdown workflow templates, Python `unittest`, Bash architecture test runner.

## Global Constraints

- All-day titles are copied verbatim, one event per output line, with `весь день`.
- Calendar events alone never prove completion.
- A user decision applies only after an exact canonical diff and, when needed, a complete guarded calendar preview are shown and confirmed.
- Ambiguous task references create no mutation proposal.
- No new dependencies, background jobs, or direct unconfirmed writes.

---

## File structure

| File | Responsibility |
| --- | --- |
| `hub-template/ai/skills/hub-workflows/resources/day-plan.md` | Day-plan rendering and decision-sync contract. |
| `hub-template/ai/skills/hub-workflows/resources/evening-review.md` | Evening-review rendering and decision-sync contract. |
| `hub-template/ai/skills/hub-workflows/SKILL.md` | Shared confirmation/application boundary for the two workflows. |
| `hub-template/ai/architecture.md` | Durable Hub-wide invariant. |
| `tests/test_hub_workflows_progressive.py` | Regression tests for template wording and scope boundaries. |
| `scripts/architecture-test.sh` | Runs the new/extended workflow regression suite through the normal unit command. |

### Task 1: Define and test verbatim all-day rendering

**Files:**
- Modify: `tests/test_hub_workflows_progressive.py`
- Modify: `hub-template/ai/skills/hub-workflows/resources/day-plan.md`
- Modify: `hub-template/ai/skills/hub-workflows/resources/evening-review.md`

**Interfaces:**
- Consumes: guarded `read_events` records with `all_day`, `title`, `start`, and `end`.
- Produces: an output bullet for every source event, using `весь день — <exact title>` for all-day events.

- [ ] **Step 1: Add failing contract tests**

Add a test method that requires both scenario resources to contain the exact constraints below:

```python
def test_day_plan_and_evening_review_preserve_all_day_events(self):
    required = (
        "each all-day event separately",
        "весь день",
        "Keep event titles verbatim",
        "do not shorten, translate, group, or paraphrase",
    )
    for filename in ("day-plan.md", "evening-review.md"):
        text = (RESOURCE_DIR / filename).read_text(encoding="utf-8")
        for phrase in required:
            self.assertIn(phrase, text, f"{filename}: {phrase}")
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `python3 -m unittest tests.test_hub_workflows_progressive.HubWorkflowProgressiveDisclosureTests.test_day_plan_and_evening_review_preserve_all_day_events -v`

Expected: FAIL because both resources lack the explicit all-day rendering contract.

- [ ] **Step 3: Add the minimal template rules**

In both resources, add this semantic rule next to their calendar-rendering instructions:

```text
Render each all-day event separately as `- весь день — <title>`.
Keep `<title>` verbatim; never shorten, translate, group, or paraphrase it.
```

In `day-plan.md`, repeat the same rule for retained all-day entries in `## Предлагаемый календарь`.

- [ ] **Step 4: Run focused and normal unit checks**

Run: `python3 -m unittest tests.test_hub_workflows_progressive -v && bash tests/test-day-plan-output.sh`

Expected: PASS.

- [ ] **Step 5: Commit the completed task**

```bash
git add hub-template/ai/skills/hub-workflows/resources/day-plan.md \
  hub-template/ai/skills/hub-workflows/resources/evening-review.md \
  tests/test_hub_workflows_progressive.py
git commit -m "fix: preserve all-day workflow events"
```

### Task 2: Require synchronized task-state proposals in both workflows

**Files:**
- Modify: `tests/test_hub_workflows_progressive.py`
- Modify: `hub-template/ai/skills/hub-workflows/SKILL.md`
- Modify: `hub-template/ai/skills/hub-workflows/resources/day-plan.md`
- Modify: `hub-template/ai/skills/hub-workflows/resources/evening-review.md`
- Modify: `hub-template/ai/architecture.md`

**Interfaces:**
- Consumes: an unambiguous user statement and the matching canonical task record.
- Produces: one of `update_task`, `update_due`, or `update_waiting`, with project ID, exact target path, exact diff, and a paired guarded calendar preview only when the task has a calendar change.

- [ ] **Step 1: Add failing shared-contract tests**

Add a test requiring both resources to name all three actions and the ambiguity safeguard:

```python
def test_day_plan_and_evening_review_require_exact_task_sync(self):
    required = ("update_task", "update_due", "update_waiting",
                "exact target path", "exact diff", "ambiguous")
    for filename in ("day-plan.md", "evening-review.md"):
        text = (RESOURCE_DIR / filename).read_text(encoding="utf-8")
        for phrase in required:
            self.assertIn(phrase, text, f"{filename}: {phrase}")
```

Add a second test that requires `hub-template/ai/architecture.md` to state
`calendar events never prove completion` and `exact canonical task-record diff`.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python3 -m unittest tests.test_hub_workflows_progressive.HubWorkflowProgressiveDisclosureTests.test_day_plan_and_evening_review_require_exact_task_sync -v`

Expected: FAIL because evening review does not yet define direct user decision handling and the templates do not both name every safeguard.

- [ ] **Step 3: Add the shared contract**

Add the following rule to both scenario resources:

```text
For a direct, unambiguous user statement about one canonical task, emit exactly
one `update_task`, `update_due`, or `update_waiting` proposal with the project
ID, exact target path, and exact canonical task-record diff. A calendar change
is paired only when the task schedule changes. If the task reference is
ambiguous, emit no proposal and ask which task is meant.
```

Keep the existing prohibition against treating a calendar event as completion.
In the core skill and `architecture.md`, state that a confirmed displayed
package applies the exact task diff and its paired calendar preview together,
while an unpaired calendar edit remains calendar-only.

- [ ] **Step 4: Run focused and complete architecture tests**

Run: `python3 -m unittest tests.test_hub_workflows_progressive -v && bash scripts/architecture-test.sh --unit`

Expected: PASS.

- [ ] **Step 5: Commit the completed task**

```bash
git add hub-template/ai/skills/hub-workflows/SKILL.md \
  hub-template/ai/skills/hub-workflows/resources/day-plan.md \
  hub-template/ai/skills/hub-workflows/resources/evening-review.md \
  hub-template/ai/architecture.md tests/test_hub_workflows_progressive.py
git commit -m "feat: synchronize workflow task decisions"
```

### Task 3: Verify distribution into the active Hub

**Files:**
- Modify: none unless the normal update preview identifies these managed files.
- Test: `tests/test_hub_update_check.sh`
- Test: `scripts/architecture-test.sh`

**Interfaces:**
- Consumes: the committed template changes and the existing Hub update mechanism.
- Produces: a reviewable update preview; no active-Hub write occurs without the user confirming that preview.

- [ ] **Step 1: Run distribution regression checks**

Run: `bash tests/test_hub_update_check.sh && bash scripts/architecture-test.sh --unit`

Expected: PASS.

- [ ] **Step 2: Produce the standard managed-file update preview**

Run:

```bash
bash scripts/update-installed-hub.sh --dry-run \
  --hub /Users/zykovsrg/Documents/vibecode/_ai-hub \
  --source /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture
```

Inspect that it includes only:

```text
ai/skills/hub-workflows/SKILL.md
ai/skills/hub-workflows/resources/day-plan.md
ai/skills/hub-workflows/resources/evening-review.md
ai/architecture.md
```

Expected: a preview with exact diffs and no write.

- [ ] **Step 3: Request the separate active-Hub update confirmation**

Report the preview and request confirmation before applying it. Do not apply the managed-file update in this task.

## Plan self-review

- Spec coverage: Task 1 covers verbatim all-day output; Task 2 covers decision-to-record synchronization, ambiguity, and confirmation; Task 3 covers safe distribution.
- Placeholder scan: no unfinished markers or undefined interfaces.
- Type consistency: all workflow action names match the existing proposal envelope: `update_task`, `update_due`, and `update_waiting`.
