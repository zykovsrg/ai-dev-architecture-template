import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
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

    def load_index_module(self):
        scripts = str(ROOT / "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        spec = importlib.util.spec_from_file_location(
            "compact_task_index_under_test", ROOT / "scripts/read-compact-task-index.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_only_active_registered_projects_and_compact_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_index(self.make_hub(Path(tmp)))
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = json.loads(result.stdout)
            self.assertEqual({row["project_id"] for row in rows}, {"alpha", "beta"})
            self.assertEqual(set(rows[0]), {"project_id", "task_id", "title", "status", "due", "source_kind", "source_path"})
            self.assertEqual({row["source_kind"] for row in rows}, {"current", "future", "paused"})
            for row in rows:
                self.assertEqual(Path(row["source_path"]).name, {
                    "current": "current-task.md",
                    "future": "future-tasks.md",
                    "paused": "paused-tasks.md",
                }[row["source_kind"]])
            self.assertNotIn("MUST_NOT_APPEAR", result.stdout)
            self.assertNotIn("## Goal", result.stdout)

    def test_primary_discovery_does_not_full_read_task_bodies(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = self.make_hub(Path(tmp))
            marker = "BODY_MARKER_MUST_NOT_BE_FULL_READ_" + ("x" * 200000)
            for path in (hub / "projects").glob("*/ai/*.md"):
                path.write_text(path.read_text(encoding="utf-8") + "\n## Notes\n" + marker + "\n", encoding="utf-8")
            module = self.load_index_module()
            original = Path.read_text

            def guarded_read_text(path, *args, **kwargs):
                if path.name in {"current-task.md", "future-tasks.md", "paused-tasks.md"}:
                    raise AssertionError("compact discovery must not full-read canonical task bodies")
                return original(path, *args, **kwargs)

            with mock.patch.object(Path, "read_text", new=guarded_read_text):
                rows = module.build_index(hub)
            output = json.dumps(rows, ensure_ascii=False)
            self.assertNotIn("BODY_MARKER_MUST_NOT_BE_FULL_READ", output)
            self.assertEqual({row["project_id"] for row in rows}, {"alpha", "beta"})

    def test_current_record_parses_scheduled_and_link_after_goal_in_compact_mode(self):
        module = self.load_index_module()
        text = (
            "Status: active\n"
            "Task ID: TASK-demo-20260911-001\n"
            "Due: 2026-09-12\n"
            "\n"
            "## Goal\n"
            "\n"
            "Compact title\n"
            "\n"
            "Запланировано: 2026-09-27 10:00-11:00\n"
            "Событие: cal/evt · синхронизировано: 2026-09-27 10:00-11:00\n"
        )
        records = module.read_records_lines("demo", "current", iter(text.splitlines(keepends=True)))
        self.assertEqual(records, [{
            "task_id": "TASK-demo-20260911-001",
            "title": "Compact title",
            "status": "active",
            "due": "2026-09-12",
            "scheduled": ("2026-09-27 10:00", "2026-09-27 11:00"),
            "event_link": {
                "calendar_id": "cal",
                "event_id": "evt",
                "synced_start": "2026-09-27 10:00",
                "synced_end": "2026-09-27 11:00",
            },
        }])

    def test_compact_parser_preserves_strict_validation(self):
        module = self.load_index_module()
        cases = [
            ("current", "Status: active\nTask ID: invalid\n\n## Goal\n\nTitle\n", "invalid_current_task_id"),
            ("current", "Status: active\nTask ID: TASK-other-20260911-001\n\n## Goal\n\nTitle\n", "invalid_current_task_id"),
            ("current", "Status: nonsense\nTask ID: TASK-demo-20260911-001\n\n## Goal\n\nTitle\n", "invalid_status"),
            ("current", "Status: active\nTask ID: TASK-demo-20260911-001\nDue: 2026-02-30\n\n## Goal\n\nTitle\n", "invalid_due"),
            ("paused", "### 2026-09-11 — Paused\n\nStatus: paused\n", "invalid_paused_record"),
            ("future", "### TASK-demo-20260911-002 — Future\n\nStatus: nonsense\n", "invalid_status"),
        ]
        for kind, text, expected in cases:
            with self.subTest(kind=kind, expected=expected):
                with self.assertRaisesRegex(ValueError, expected):
                    module.read_records_lines("demo", kind, iter(text.splitlines(keepends=True)))

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


class CompactTaskIndexGroupFilterTests(unittest.TestCase):
    """--group ID: read task files only for archiprojects.members(...)."""

    def write_project(self, path: Path, project: str):
        (path / "ai").mkdir(parents=True)
        (path / "ai/current-task.md").write_text(CURRENT.format(project=project), encoding="utf-8")
        (path / "ai/future-tasks.md").write_text(FUTURE.format(project=project), encoding="utf-8")
        (path / "ai/paused-tasks.md").write_text(PAUSED.format(project=project), encoding="utf-8")

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

    def write_card(self, hub: Path, project: str, primary: str):
        (hub / "ai/project-cards").mkdir(parents=True, exist_ok=True)
        (hub / f"ai/project-cards/{project}.md").write_text(
            f"# Project Card\nProject ID: {project}\nName: {project.title()}\n"
            f"primary_archiproject: {primary}\nPurpose: fixture.\n",
            encoding="utf-8",
        )

    def make_hub(self, root: Path):
        hub = root / "hub"
        (hub / "ai").mkdir(parents=True)
        (hub / "ai/archiprojects.md").write_text(
            "# Archiprojects\n\n## Schema\n\n"
            "## top\n```yaml\nid: top\nname: Top\nstatus: active\nkind: group\n```\n",
            encoding="utf-8",
        )
        projects = hub / "projects"
        entries = []
        for project, primary in (("alpha", "top"), ("beta", "none")):
            path = projects / project
            self.write_project(path, project)
            self.write_card(hub, project, primary)
            entries.append((project, "active", path))
        self.write_registry(hub, entries)
        return hub, projects

    def run_index(self, hub: Path, extra_args=()):
        return subprocess.run(
            [sys.executable, "scripts/read-compact-task-index.py", "--hub", str(hub), *extra_args],
            text=True, capture_output=True,
        )

    def test_group_filter_limits_to_member_projects_and_never_opens_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub, projects = self.make_hub(Path(tmp))
            # Make the non-member project's task files unreadable; the group
            # filter must never open them.
            for name in ("current-task.md", "future-tasks.md", "paused-tasks.md"):
                (projects / "beta" / "ai" / name).chmod(0o000)
            try:
                result = self.run_index(hub, ["--group", "top"])
            finally:
                for name in ("current-task.md", "future-tasks.md", "paused-tasks.md"):
                    (projects / "beta" / "ai" / name).chmod(0o644)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = json.loads(result.stdout)
            self.assertEqual({row["project_id"] for row in rows}, {"alpha"})

    def test_unknown_group_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub, _projects = self.make_hub(Path(tmp))
            result = self.run_index(hub, ["--group", "ghost"])
            self.assertEqual(result.returncode, 2)
            self.assertIn("unknown archiprojects group: ghost", result.stderr)


if __name__ == "__main__":
    unittest.main()
