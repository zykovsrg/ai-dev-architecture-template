# Low-cost Session Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use deterministic gates first, Luna by default, and Terra only for ambiguity or material risk.

**Architecture:** Workflow text defines the order and escalation gate; one Python test protects those rules. Existing validators remain responsible for syntax and evidence.

**Tech Stack:** Markdown workflows, Python unittest.

## Global Constraints

- Do not send whole histories automatically.
- Do not apply an improvement without user approval.
- Luna is default; Terra is escalation-only.

---

### Task 1: Encode and test the review contract

**Files:**
- Modify: `hub-template/ai/skills/hub-session-review/SKILL.md`
- Modify: `hub-template/ai/skills/hub-task-finish/SKILL.md`
- Create: `tests/test_low_cost_session_review.py`

**Interfaces:**
- Consumes: task-close or user-request review.
- Produces: deterministic failure before model use, or a narrow Luna review.

- [ ] **Step 1: Write the failing test**

Assert the session workflow contains `Luna` and `Terra`, and task finish says `before any model call`.

- [ ] **Step 2: Run the test to verify it fails**

Run `python3 -m unittest tests/test_low_cost_session_review.py`; expect failure.

- [ ] **Step 3: Add minimal workflow rules**

Add deterministic-first, narrow-evidence, Luna-default, Terra-escalation, and no-broad-history wording.

- [ ] **Step 4: Run the focused test and commit**

Run `python3 -m unittest tests/test_low_cost_session_review.py`; expect PASS. Commit the workflow and test.

### Task 2: Ship the changed workflow

**Files:**
- Modify: `release/hub-files.json`

- [ ] **Step 1: Rebuild and verify**

Run `python3 scripts/hub_release.py build --source . > release/hub-files.json`, then `python3 scripts/hub_release.py check --source . --manifest release/hub-files.json && bash scripts/architecture-test.sh --unit`; expect success.

- [ ] **Step 2: Commit**

Commit the refreshed manifest.
