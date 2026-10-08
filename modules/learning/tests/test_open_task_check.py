#!/usr/bin/env python3
"""Morning check of open current tasks: list, record evidence, decide, pause."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import shutil
import atexit

# open_task_check.py imports Hub neighbours (task_records, compact index, session_collect):
# stage them in one folder, as the installer lays them out in the Hub.
REPO = Path(__file__).resolve().parents[3]
STAGE = Path(tempfile.mkdtemp(prefix="open-task-check-stage-"))
atexit.register(shutil.rmtree, STAGE, ignore_errors=True)
for rel in ("modules/learning/scripts/open_task_check.py", "modules/learning/scripts/session_collect.py",
            "modules/tasks/scripts/task_records.py", "modules/tasks/scripts/read-compact-task-index.py",
            "modules/projects/scripts/archiprojects.py"):
    shutil.copy2(REPO / rel, STAGE / Path(rel).name)

sys.path.insert(0, str(STAGE))
spec = importlib.util.spec_from_file_location("open_task_check", STAGE / "open_task_check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
from task_records import read_records  # noqa: E402

TODAY = "2026-10-07"
CURRENT = """# Current Task

Status: active
Task ID: TASK-demo-20261001-001
Stage: execution

Due: 2026-10-06
Запланировано: 2026-10-06 13:00-14:00 (Europe/Kirov).
Событие: CAL/EV-1 · синхронизировано: 2026-10-06 13:00-14:00

## Goal

Обновить страницу.

## Done criteria

- Блок убран.
- Пробная версия отправлена
  врачу.
"""
PAUSED = """# Paused Tasks

## Template

### YYYY-MM-DD — Task title

Status: paused

## Paused tasks

### 2026-09-01 — Старая

Task ID: TASK-demo-20260901-001

Status: paused
"""


def make_hub(tmp: Path, current=CURRENT, yesterday=True) -> Path:
    project = tmp / "hub/projects/demo"
    (project / "ai").mkdir(parents=True)
    (tmp / "hub/ai").mkdir()
    (tmp / "hub/ai/project-registry.md").write_text(f"## demo\n\nStatus: active\nPath: {project}\n", encoding="utf-8")
    (project / "ai/current-task.md").write_text(current, encoding="utf-8")
    (project / "ai/paused-tasks.md").write_text(PAUSED, encoding="utf-8")
    (project / "ai/future-tasks.md").write_text("# Future Tasks\n", encoding="utf-8")
    if yesterday:
        old = time.time() - 2 * 86400
        os.utime(project / "ai/current-task.md", (old, old))
    return tmp / "hub"


def reply(*criteria, note=None):
    item = {"project": "demo", "task_id": "TASK-demo-20261001-001", "criteria": list(criteria)}
    if note:
        item["note"] = note
    return {"cases": [], "tasks": [item]}


BATCH = {"sessions": [{"id": "s1", "tool": "claude", "project": "demo"},
                      {"id": "s2", "tool": "claude", "project": "other"},
                      {"id": "s3", "tool": "codex", "project": "hub"}]}


class Reply(unittest.TestCase):
    def test_cases_accept_array_or_object(self):
        from session_rules import load_cases
        self.assertEqual(load_cases('[{"rule": "R-1"}]'), [{"rule": "R-1"}])
        self.assertEqual(load_cases(json.dumps(reply())), [])
        with self.assertRaises(ValueError):
            load_cases('{"tasks": []}')


class Criteria(unittest.TestCase):
    def test_bullets_and_continuations(self):
        self.assertEqual(check.done_criteria(CURRENT), ["Блок убран.", "Пробная версия отправлена врачу."])


class Flow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.folder = self.base / "batch"
        self.folder.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def listed(self, hub):
        rows, skipped = check.open_tasks(hub, TODAY)
        (self.folder / check.TASKS_FILE).write_text(json.dumps({"tasks": rows}), encoding="utf-8")
        return rows, skipped

    def test_list_skips_task_changed_today(self):
        rows, skipped = self.listed(make_hub(self.base, yesterday=False))
        self.assertEqual(rows, [])
        self.assertEqual(skipped[0]["task_id"], "TASK-demo-20261001-001")

    def test_list_ignores_empty_and_waiting(self):
        hub = make_hub(self.base, current=CURRENT.replace("Status: active", "Status: waiting"))
        self.assertEqual(self.listed(hub)[0], [])

    def test_close_needs_every_criterion_with_evidence(self):
        self.listed(make_hub(self.base))
        check.record(self.folder, BATCH, reply({"n": 1, "met": True, "session": "s1", "evidence": "Блок удалён в файле."}))
        self.assertEqual(check.decide(self.folder)[0]["action"], "pause")
        check.record(self.folder, BATCH, reply({"n": 2, "met": True, "session": "s1", "evidence": "Ссылка отправлена."}))
        [d] = check.decide(self.folder)
        self.assertEqual(d["action"], "close")
        self.assertEqual([m["n"] for m in d["met"]], [1, 2])

    def test_evidence_without_known_session_or_text_is_dropped(self):
        self.listed(make_hub(self.base))
        kept, dropped = check.record(self.folder, BATCH, reply(
            {"n": 1, "met": True, "session": "other", "evidence": "x"},
            {"n": 2, "met": True, "session": "s1", "evidence": ""},
            {"n": 3, "met": True, "session": "s1", "evidence": "x"}))
        self.assertEqual((kept, dropped), (0, 3))
        self.assertEqual(check.decide(self.folder)[0]["action"], "pause")

    def test_evidence_must_come_from_the_tasks_project_or_hub_root(self):
        self.listed(make_hub(self.base))
        kept, dropped = check.record(self.folder, BATCH, reply(
            {"n": 1, "met": True, "session": "s2", "evidence": "Блок удалён."},
            {"n": 2, "met": True, "session": "s3", "evidence": "Ссылка отправлена."}))
        self.assertEqual((kept, dropped), (1, 1))
        self.assertEqual(check.decide(self.folder)[0]["action"], "pause")

    def test_note_is_kept_and_plain_array_reply_adds_nothing(self):
        self.listed(make_hub(self.base))
        check.record(self.folder, BATCH, [])
        check.record(self.folder, BATCH, reply(note="Врач одобрил макет."))
        self.assertEqual(check.decide(self.folder)[0]["notes"], ["Врач одобрил макет."])

    def test_no_criteria_never_closes(self):
        hub = make_hub(self.base, current=CURRENT.split("## Done criteria")[0])
        self.listed(hub)
        self.assertEqual(check.decide(self.folder)[0]["action"], "pause")

    def test_pause_moves_task_and_keeps_schedule(self):
        hub = make_hub(self.base)
        check.pause(hub, "demo", "TASK-demo-20261001-001", TODAY)
        ai = hub / "projects/demo/ai"
        paused = read_records("demo", "paused", (ai / "paused-tasks.md").read_text(encoding="utf-8"))
        self.assertEqual([p["task_id"] for p in paused], ["TASK-demo-20261001-001", "TASK-demo-20260901-001"])
        self.assertEqual(paused[0]["due"], "2026-10-06")
        self.assertEqual(paused[0]["title"], "Обновить страницу.")
        self.assertEqual(paused[0]["event_link"]["event_id"], "EV-1")
        self.assertIn("#### Done criteria", (ai / "paused-tasks.md").read_text(encoding="utf-8"))
        self.assertEqual(read_records("demo", "current", (ai / "current-task.md").read_text(encoding="utf-8")), [])
        result = subprocess.run(["python3", str(STAGE / "task_records.py"), "read", "--file", str(ai / "paused-tasks.md"),
                                 "--project-id", "demo", "--kind", "paused", "--strict-headings"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pause_demotes_nested_subsections(self):
        hub = make_hub(self.base, current=CURRENT.replace("## Done criteria", "### Backend\n\nДетали.\n\n## Done criteria"))
        check.pause(hub, "demo", "TASK-demo-20261001-001", TODAY)
        ai = hub / "projects/demo/ai"
        self.assertIn("##### Backend", (ai / "paused-tasks.md").read_text(encoding="utf-8"))
        result = subprocess.run(["python3", str(STAGE / "task_records.py"), "read", "--file", str(ai / "paused-tasks.md"),
                                 "--project-id", "demo", "--kind", "paused", "--strict-headings"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pause_refuses_other_task(self):
        hub = make_hub(self.base)
        with self.assertRaises(ValueError):
            check.pause(hub, "demo", "TASK-demo-20261001-002", TODAY)

    def test_cli_refuses_folder_inside_hub(self):
        hub = make_hub(self.base)
        result = subprocess.run(["python3", str(STAGE / "open_task_check.py"), "--hub", str(hub),
                                 "--dir", str(hub / "ai/tmp"), "list"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
