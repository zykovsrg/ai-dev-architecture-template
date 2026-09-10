# Live Hub Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the refactored hub to the working installation without removing its goal, calendar, or workflow-learning behavior.

**Architecture:** Make the template the combined source of truth: retain the installed hub's detailed learning instructions and layer the new low-cost session review and safe record checks on top. Verify the template contract, then update the installation through the existing guarded updater.

**Tech Stack:** Markdown skill contracts, Bash checks, Python unit tests, Git.

## Global Constraints

- Existing goal progress, calendar snapshots, friction records, and weekly rule promotion stay enabled.
- Session reviews create proposals only and use deterministic checks before Luna or Terra.
- No managed working file is replaced by an unreviewed older template.
- New and changed behavior must have a repeatable check.

---

### Task 1: Make preservation explicit in the source template

**Files:**
- Modify: `hub-template/ai/architecture.md`
- Modify: `hub-template/AGENTS.md`
- Modify: `hub-template/CLAUDE.md`
- Test: `tests/test_live_hub_merge.py`

**Interfaces:**
- Consumes: the installed hub's documented goal, calendar, and workflow-learning lifecycle.
- Produces: one combined architecture contract used by future installations.

- [ ] **Step 1: Write the failing contract test**

```python
def test_template_keeps_existing_learning_and_adds_session_review(self):
    text = template("ai/architecture.md")
    self.assertIn("## Goal Progress", text)
    self.assertIn("## Self-Learning Workflows", text)
    self.assertIn("hub-session-review", text)
    self.assertIn("snapshot-calendar.sh", text)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_live_hub_merge -v`

Expected: FAIL because the template has condensed rather than preserved the full learning contract.

- [ ] **Step 3: Merge the text by responsibility**

Keep the installed hub's `Goal Progress` and `Self-Learning Workflows` sections, then add the session-review closure rule and its on-demand route. Keep the combined task-and-calendar confirmation language unchanged.

- [ ] **Step 4: Run the contract test**

Run: `python3 -m unittest tests.test_live_hub_merge -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add hub-template/AGENTS.md hub-template/CLAUDE.md hub-template/ai/architecture.md tests/test_live_hub_merge.py
git commit -m "fix: preserve learning in hub template"
```

### Task 2: Combine the workflow skills

**Files:**
- Modify: `hub-template/ai/skills/hub-workflows/SKILL.md`
- Modify: `hub-template/ai/skills/hub-calendar/SKILL.md`
- Modify: `hub-template/ai/skills/hub-goal-progress/SKILL.md`
- Test: `tests/test_live_hub_merge.py`

**Interfaces:**
- Consumes: `ai/workflow-observations.md`, `ai/workflow-context.md`, and calendar snapshots.
- Produces: a workflow contract that preserves established learning and feeds no automatic rule changes.

- [ ] **Step 1: Extend the failing contract test**

```python
def test_template_workflows_keep_calendar_and_rule_lifecycle(self):
    workflows = template("ai/skills/hub-workflows/SKILL.md")
    calendar = template("ai/skills/hub-calendar/SKILL.md")
    self.assertIn("promote_rule", workflows)
    self.assertIn("retire_rule", workflows)
    self.assertIn("snapshot-calendar.sh", workflows)
    self.assertIn("snapshot-calendar.sh", calendar)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_live_hub_merge.LiveHubMergeTests.test_template_workflows_keep_calendar_and_rule_lifecycle -v`

Expected: FAIL because condensed template rules omit the complete existing lifecycle.

- [ ] **Step 3: Merge the lifecycle into the template**

Restore the existing goal blocks, snapshot history, friction capture, weekly observation promotion, and rule retirement wording. Retain the new pending-observation rule: rendering a proposal does not consume it.

- [ ] **Step 4: Run the focused and full unit suites**

Run: `python3 -m unittest tests.test_live_hub_merge -v && bash scripts/architecture-test.sh --unit`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add hub-template/ai/skills/hub-workflows/SKILL.md hub-template/ai/skills/hub-calendar/SKILL.md hub-template/ai/skills/hub-goal-progress/SKILL.md tests/test_live_hub_merge.py
git commit -m "fix: retain task and calendar learning workflows"
```

### Task 3: Add the closure review without weakening existing closure rules

**Files:**
- Modify: `hub-template/ai/skills/hub-task-finish/SKILL.md`
- Modify: `hub-template/ai/skills/hub-session-review/SKILL.md`
- Test: `tests/test_live_hub_merge.py`

**Interfaces:**
- Consumes: a confirmed task's current session and deterministic validation output.
- Produces: an evidence-backed review path before task memory is cleared.

- [ ] **Step 1: Add the failing closure-order assertion**

```python
def test_task_close_reviews_before_memory_clear(self):
    finish = template("ai/skills/hub-task-finish/SKILL.md")
    self.assertLess(finish.index("hub-session-review"), finish.index("clear task memory"))
    self.assertIn("deterministic", finish)
```

- [ ] **Step 2: Run it to verify it fails if the order is absent**

Run: `python3 -m unittest tests.test_live_hub_merge.LiveHubMergeTests.test_task_close_reviews_before_memory_clear -v`

Expected: PASS only after the ordered combined contract is present.

- [ ] **Step 3: Keep the low-cost review contract**

Ensure the task-close skill validates deterministic checks before a model call, stores the review before clearing context, and leaves the task open on review failure. Ensure the session-review skill keeps focused Luna review and Terra escalation only for ambiguity or material risk.

- [ ] **Step 4: Run review checks**

Run: `python3 -m unittest tests/test_low_cost_session_review.py tests/test_live_hub_merge.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add hub-template/ai/skills/hub-task-finish/SKILL.md hub-template/ai/skills/hub-session-review/SKILL.md tests/test_live_hub_merge.py
git commit -m "feat: merge session review into task closure"
```

### Task 4: Rebuild and deploy the combined release

**Files:**
- Modify: `release/hub-files.json`
- Update: installed hub files under `/Users/zykovsrg/Documents/vibecode/_ai-hub`

**Interfaces:**
- Consumes: the combined template and updater preview.
- Produces: working rules and scripts matching the combined source.

- [ ] **Step 1: Rebuild the manifest**

Run: `python3 scripts/hub_release.py build --source . > release/hub-files.json`

- [ ] **Step 2: Verify source consistency**

Run: `python3 scripts/hub_release.py check --source . --manifest release/hub-files.json`

Expected: exit 0.

- [ ] **Step 3: Preview the installation update**

Run: `bash scripts/update-installed-hub.sh --hub /Users/zykovsrg/Documents/vibecode/_ai-hub --source . --dry-run`

Expected: the preview includes the session review and new validation files, with no removal of goal, calendar, or learning rules.

- [ ] **Step 4: Apply the reviewed update**

Run: `bash scripts/update-installed-hub.sh --hub /Users/zykovsrg/Documents/vibecode/_ai-hub --source . --apply --allow-dirty`

Expected: protected files update; project data and `.local` state remain untouched.

- [ ] **Step 5: Verify the working installation**

Run: `bash scripts/check-all-task-records.sh --hub /Users/zykovsrg/Documents/vibecode/_ai-hub && bash scripts/architecture-test.sh --unit`

Expected: canonical task records and all unit tests pass.

- [ ] **Step 6: Commit**

```bash
git add release/hub-files.json tests/test_live_hub_merge.py
git commit -m "build: release combined hub architecture"
```
