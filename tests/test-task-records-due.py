#!/usr/bin/env python3
"""Compact discovery must report the same due date as the canonical read."""

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("task_records", ROOT / "modules/tasks/scripts/task_records.py")
task_records = importlib.util.module_from_spec(spec)
spec.loader.exec_module(task_records)


CURRENT_DUE_BELOW_BODY = """# Current Task

Task ID: TASK-zdorove-babushki-20260914-001
Status: active
Stage: intake

## Goal

Организовать обследование сердца бабушки за 1–2 визита в клинику.

## Done criteria

- Есть подтверждённые записи.

Due: 2026-09-19
"""

FUTURE_DUE_BELOW_BODY = """# Future Tasks

### FT-20260901-001 — Ручной тест границ all-day

Status: ready
Created: 2026-09-01

Подробности задачи в свободной форме.

Due: 2026-09-19
"""

PAUSED_DUE_BELOW_BODY = """# Paused Tasks

### 2026-09-17 — Отображение семантики в CLI

Task ID: TASK-seo-content-creator-20260917-001
Status: paused
Paused: 2026-09-17

Подробности задачи в свободной форме.

Due: 2026-09-19
"""


class CompactDueParityTests(unittest.TestCase):
    def assert_due_parity(self, project_id, kind, text, expected):
        compact = task_records.read_records_lines(project_id, kind, text.splitlines())
        full = task_records.read_records(project_id, kind, text)
        self.assertEqual([record["due"] for record in full], [expected])
        self.assertEqual(
            [record["due"] for record in compact],
            [record["due"] for record in full],
            f"compact discovery lost the due date for kind={kind}",
        )

    def test_current_due_below_body_is_discovered(self):
        self.assert_due_parity(
            "zdorove-babushki", "current", CURRENT_DUE_BELOW_BODY, "2026-09-19"
        )

    def test_future_due_below_body_is_discovered(self):
        self.assert_due_parity(
            "ai-dev-architecture", "future", FUTURE_DUE_BELOW_BODY, "2026-09-19"
        )

    def test_paused_due_below_body_is_discovered(self):
        self.assert_due_parity(
            "seo-content-creator", "paused", PAUSED_DUE_BELOW_BODY, "2026-09-19"
        )

    def test_conflicting_due_still_raises_in_compact_mode(self):
        text = CURRENT_DUE_BELOW_BODY + "\nDue: 2026-09-20\n"
        with self.assertRaises(ValueError):
            task_records.read_records_lines(
                "zdorove-babushki", "current", text.splitlines()
            )


if __name__ == "__main__":
    unittest.main()
