#!/usr/bin/env python3
"""Seeding a project's future tasks from its archiproject group's stage template."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "seed_stage_template.py"
spec = importlib.util.spec_from_file_location("task_records", ROOT / "scripts" / "task_records.py")
task_records = importlib.util.module_from_spec(spec)
spec.loader.exec_module(task_records)

ARCHIPROJECTS = """# Archiprojects

## work

```yaml
id: work
name: Работа
status: active
kind: group
```

## work-promo

```yaml
id: work-promo
name: Промо
status: active
kind: group
parent: work
stage_template: projects/promo/knowledge/stages.md
```

## other

```yaml
id: other
name: Другое
status: active
kind: group
```
"""

TEMPLATE = """# Этапы страницы

## Stages

1. Назначить встречу с врачом
2. Написать текст
3. Передать страницу на публикацию
"""

FUTURE = """# Future Tasks

Use this file for confirmed future ideas that are outside the current task.

## Future tasks

### TASK-page-a-20261005-001 — Уже есть

Status: ready
Created: 2026-10-05
"""


def make_hub(tmp: Path, group: str = "work-promo") -> Path:
    hub = tmp / "hub"
    (hub / "ai/project-cards").mkdir(parents=True)
    (hub / "projects/promo/knowledge").mkdir(parents=True)
    (hub / "projects/page-a/ai").mkdir(parents=True)
    (hub / "ai/archiprojects.md").write_text(ARCHIPROJECTS)
    (hub / "projects/promo/knowledge/stages.md").write_text(TEMPLATE)
    path = hub / "projects/page-a"
    (hub / "ai/project-registry.md").write_text(
        f"# Registry\n\n## page-a\nName: Page A\nStatus: active\nPath: {path}\n"
    )
    (hub / "ai/project-cards/page-a.md").write_text(
        f"# Page A\n\nProject ID: page-a\nprimary_archiproject: {group}\n"
    )
    (path / "ai/future-tasks.md").write_text(FUTURE)
    return hub


def run(hub: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(SCRIPT), "--hub", str(hub), "--project", "page-a", "--today", "2026-10-05", *extra],
        capture_output=True, text=True,
    )


class SeedStageTemplateTests(unittest.TestCase):
    def test_seeds_all_stages_in_order_with_next_free_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(Path(tmp))
            result = run(hub)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = json.loads(result.stdout)
            self.assertEqual(out["created"], [
                "TASK-page-a-20261005-002", "TASK-page-a-20261005-003", "TASK-page-a-20261005-004",
            ])
            text = (hub / "projects/page-a/ai/future-tasks.md").read_text()
            order = [text.index(t) for t in ("Назначить встречу с врачом", "Написать текст", "Передать страницу на публикацию", "Уже есть")]
            self.assertEqual(order, sorted(order))
            records = task_records.read_records_lines("page-a", "future", text.splitlines())
            titles = {r["title"]: r["status"] for r in records}
            self.assertEqual(titles["Написать текст"], "ready")

    def test_marks_leading_stages_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(Path(tmp))
            result = run(hub, "--done", "2")
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (hub / "projects/page-a/ai/future-tasks.md").read_text()
            records = {r["title"]: r["status"] for r in task_records.read_records_lines("page-a", "future", text.splitlines())}
            self.assertEqual(records["Назначить встречу с врачом"], "done")
            self.assertEqual(records["Написать текст"], "done")
            self.assertEqual(records["Передать страницу на публикацию"], "ready")

    def test_second_run_adds_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(Path(tmp))
            run(hub)
            before = (hub / "projects/page-a/ai/future-tasks.md").read_text()
            result = run(hub)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["created"], [])
            self.assertEqual((hub / "projects/page-a/ai/future-tasks.md").read_text(), before)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(Path(tmp))
            result = run(hub, "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)["created"]), 3)
            self.assertEqual((hub / "projects/page-a/ai/future-tasks.md").read_text(), FUTURE)

    def test_group_without_template_is_reported_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(Path(tmp), group="other")
            result = run(hub)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = json.loads(result.stdout)
            self.assertEqual(out["created"], [])
            self.assertIsNone(out["template"])
            self.assertEqual((hub / "projects/page-a/ai/future-tasks.md").read_text(), FUTURE)

    def test_unknown_project_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(Path(tmp))
            result = subprocess.run(
                ["python3", str(SCRIPT), "--hub", str(hub), "--project", "nope", "--today", "2026-10-05"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
