# Task ID validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every consumer reject project-scoped task IDs whose date is not an eight-digit `YYYYMMDD` value.

**Architecture:** `scripts/task_records.py` becomes the shared strict validator for project-scoped IDs. A focused Python regression test locks the accepted and rejected forms; the board generator keeps its existing compatible validation.

**Tech Stack:** Python 3 standard library; Bash validation scripts.

## Global Constraints

- Project-scoped IDs use exactly `TASK-<project-id>-YYYYMMDD-NNN`.
- Do not rewrite malformed canonical records automatically.
- Keep legacy global `TASK-YYYYMMDD-NNN` and future `FT-YYYYMMDD-N` IDs valid.

---

### Task 1: Make task-record validation consistent

**Files:**
- Modify: `scripts/task_records.py:42-46`
- Create: `tests/test-task-records.py`

**Interfaces:**
- Consumes: `_valid_task_id(project_id: str, task_id: str) -> bool`.
- Produces: strict validation used by current, future, and paused task readers.

- [ ] **Step 1: Write the failing regression test**

```python
import unittest

from scripts.task_records import _valid_task_id


class TaskIdValidationTests(unittest.TestCase):
    def test_project_scoped_id_requires_compact_date(self):
        self.assertTrue(
            _valid_task_id(
                "zdorove-babushki", "TASK-zdorove-babushki-20260914-001"
            )
        )
        self.assertFalse(
            _valid_task_id(
                "zdorove-babushki", "TASK-zdorove-babushki-2026-09-14-001"
            )
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests/test-task-records.py -v`

Expected: the hyphenated project-scoped ID is incorrectly accepted.

- [ ] **Step 3: Implement the minimal validation rule**

Replace `_valid_task_id` with:

```python
def _valid_task_id(project_id, task_id):
    return bool(
        task_id
        and re.fullmatch(
            rf"(?:TASK-{re.escape(project_id)}-\d{{8}}-\d{{3}}|TASK-\d{{8}}-\d{{3}}|FT-\d{{8}}-\d+)",
            task_id,
        )
    )
```

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `python3 -m unittest tests/test-task-records.py -v`

Expected: `OK`.

- [ ] **Step 5: Run the existing task-record and board validations**

Run:

```bash
bash scripts/check-all-task-records.sh
bash scripts/generate-obsidian-projects-kanban.sh --hub /Users/zykovsrg/Documents/vibecode/_ai-hub --scope /Users/zykovsrg/Documents/vibecode/_ai-hub/ai/tmp/obsidian-scope-refresh-20260914.txt --vault /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/obsidian-vault --preview
```

Expected: both commands finish successfully.

- [ ] **Step 6: Commit the implementation**

```bash
git add scripts/task_records.py tests/test-task-records.py
git commit -m "fix: validate project task IDs consistently"
```

## Self-review

- The plan covers the strict format, rejection of the bad format, and regression checks.
- No automatic repair path is introduced.
- Names and regex usage are consistent with the existing board validator.
