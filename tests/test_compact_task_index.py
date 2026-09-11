import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CURRENT = """Status: active
Task ID: TASK-{project}-20260911-001
Due: 2026-09-12

## Goal

Current {project}
"""
FUTURE = """### TASK-{project}-20260911-002 — Future {project}

Status: ready
due: 2026-09-13
"""
PAUSED = """### 2026-09-11 — Paused {project}

Task ID: TASK-{project}-20260911-003
Status: paused
"""


class CompactTaskIndexTests(unittest.TestCase):
    def write_project(self, path: Path, project: str, invalid=False):
        (path / "ai").mkdir(parents=True)
        current = CURRENT.format(project=project)
        if invalid:
            current = current.replace("Status: active", "Status: nonsense")
        (path / "ai/current-task.md").write_text(current, encoding="utf-8")
        (path / "ai/future-tasks.md").write_text(FUTURE.format(project=project), encoding="utf-8")
        (path / "ai/paused-tasks.md").write_text(PAUSED.format(project=project), encoding="utf-8")
        (path / "secret.txt").write_text("MUST_NOT_APPEAR", encoding="utf-8")

    def write_registry(self, hub: Path, entries):
        rows = []
        for project, status, path in entries:
            rows.append(
                f"## {project}\nName: {project.title()}\nType: work\nStatus: {status}\n"
                f"Path: {path}\nTags: fixture\nCard: ai/project-cards/{project}.md\n"
            )
        (hub / "ai/project-registry.md").write_text(
            "# Project Registry\n\n" + "\n".join(rows), encoding="utf-8"
        )

    def make_hub(self, root: Path, invalid=False):
        hub = root / "hub"
        (hub / "ai").mkdir(parents=True)
        projects = hub / "projects"
        entries = []
        for project, status in (("alpha", "active"), ("beta", "active"), ("old", "archived")):
            path = projects / project
            self.write_project(path, project, invalid=invalid and project == "beta")
            entries.append((project, status, path))
        self.write_registry(hub, entries)
        return hub

    def run_index(self, hub: Path):
        return subprocess.run(
            [sys.executable, "scripts/read-compact-task-index.py", "--hub", str(hub)],
            text=True, capture_output=True,
        )

    def test_only_active_registered_projects_and_compact_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_index(self.make_hub(Path(tmp)))
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = json.loads(result.stdout)
            self.assertEqual({row["project_id"] for row in rows}, {"alpha", "beta"})
            self.assertEqual(set(rows[0]), {"project_id", "task_id", "title", "status", "due", "source_kind", "source_path"})
            self.assertNotIn("MUST_NOT_APPEAR", result.stdout)
            self.assertNotIn("## Goal", result.stdout)

    def test_invalid_active_record_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_index(self.make_hub(Path(tmp), invalid=True))
            self.assertNotEqual(result.returncode, 0)

    def test_output_order_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = self.make_hub(Path(tmp))
            first = self.run_index(hub)
            second = self.run_index(hub)
            self.assertEqual(first.stdout, second.stdout)
            rows = json.loads(first.stdout)
            keys = [(r["project_id"], {"current": 0, "future": 1, "paused": 2}[r["source_kind"]], r["task_id"]) for r in rows]
            self.assertEqual(keys, sorted(keys))

    def test_rejects_project_outside_hub_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hub = self.make_hub(root)
            outside = root / "outside" / "alpha"
            self.write_project(outside, "alpha")
            self.write_registry(hub, [("alpha", "active", outside)])
            result = self.run_index(hub)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid registered project path", result.stderr)

    def test_rejects_nested_project_below_direct_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hub = self.make_hub(root)
            nested = hub / "projects" / "group" / "alpha"
            self.write_project(nested, "alpha")
            self.write_registry(hub, [("alpha", "active", nested)])
            result = self.run_index(hub)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid registered project path", result.stderr)

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hub = self.make_hub(root)
            outside = root / "outside" / "alpha"
            self.write_project(outside, "alpha")
            link = hub / "projects" / "escape"
            link.symlink_to(outside, target_is_directory=True)
            self.write_registry(hub, [("escape", "active", link)])
            result = self.run_index(hub)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid registered project path", result.stderr)

    def test_rejects_path_traversal_registry_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hub = self.make_hub(root)
            outside = hub / "outside"
            self.write_project(outside, "alpha")
            traversal = hub / "projects" / ".." / "outside"
            self.write_registry(hub, [("alpha", "active", traversal)])
            result = self.run_index(hub)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid registered project path", result.stderr)


if __name__ == "__main__":
    unittest.main()
