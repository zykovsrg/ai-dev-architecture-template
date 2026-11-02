#!/usr/bin/env python3
"""The evening-review helper must run the month-window sync check itself."""
import atexit
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = Path(tempfile.mkdtemp(prefix="evening-review-stage-"))
atexit.register(shutil.rmtree, STAGE, ignore_errors=True)
subprocess.run(["bash", str(HERE / "stage-scripts.sh"), str(STAGE)], check=True)
SCRIPT = STAGE / "evening_review.py"
SOURCE = "Apple Calendar / EventKit"
TZ = "Europe/Kirov"
CAL = "CAL-1"
LINK = f"Событие: {CAL}/EV-1 · синхронизировано: 2026-10-03 12:00-12:30"


def make_hub(tmp: Path) -> Path:
    project = tmp / "projects" / "demo"
    (project / "ai").mkdir(parents=True)
    (tmp / "ai").mkdir()
    (tmp / "ai/project-registry.md").write_text(f"## demo\n\nStatus: active\nPath: {project}\n", encoding="utf-8")
    (project / "ai/current-task.md").write_text("# Current Task\n\nStatus: empty\n\n## Goal\n\nNo active task.\n", encoding="utf-8")
    (project / "ai/paused-tasks.md").write_text("# Paused Tasks\n", encoding="utf-8")
    (project / "ai/future-tasks.md").write_text(
        "# Future Tasks\n\n### TASK-demo-20261001-001 — задача\n\nStatus: ready\nCreated: 2026-10-01\n"
        "Запланировано: 2026-10-03 12:00-12:30 (Europe/Kirov).\n" + LINK + "\n", encoding="utf-8")
    return tmp


def event(start, end, eid="EV-1", title="дела/demo/задача"):
    return {"id": eid, "calendar_id": CAL, "title": title, "start": start, "end": end,
            "timezone": TZ, "all_day": False, "recurring": False}


def response(events, complete=True):
    return {"source": SOURCE, "timezone": TZ, "events": events,
            "unavailable_calendar_ids": [] if complete else [CAL], "availability_complete": complete}


MOVED = event("2026-10-03T13:00:00+03:00", "2026-10-03T13:30:00+03:00")


def payload(window=None, **extra):
    data = {"metadata": {"source": SOURCE, "calendars": [{"id": CAL, "name": "Важно, но несрочно", "timezone": TZ}]},
            "today": response([MOVED]), "tomorrow": response([])}
    if window is not None:
        data["sync_window"] = window
    data.update(extra)
    return data


def window(start="2026-09-03T00:00:00+03:00", end="2026-11-03T00:00:00+03:00", complete=True):
    return {"start": start, "end": end, "response": response([MOVED], complete)}


def run(hub, data):
    return subprocess.run([sys.executable, str(SCRIPT), "--hub", str(hub), "--day", "2026-10-03",
                           "--now", "2026-10-03 21:30"],
                          input=json.dumps(data, ensure_ascii=False), capture_output=True, text=True)


class EveningReviewSync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hub = make_hub(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_run_without_window_fails(self):
        result = run(self.hub, payload())
        self.assertEqual(result.returncode, 2)
        self.assertIn("sync_window", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_short_window_fails(self):
        result = run(self.hub, payload(window(start="2026-09-20T00:00:00+03:00")))
        self.assertEqual(result.returncode, 2)
        self.assertIn("D-30", result.stderr)

    def test_complete_window_reports_discrepancy(self):
        result = run(self.hub, payload(window()))
        self.assertEqual(result.returncode, 0, result.stderr)
        sync = json.loads(result.stdout)["sync"]
        self.assertEqual(sync["status"], "complete")
        self.assertEqual([i["kind"] for i in sync["items"]], ["calendar_moved"])

    def test_partial_window_reports_incomplete_without_items(self):
        result = run(self.hub, payload(window(complete=False)))
        self.assertEqual(result.returncode, 0, result.stderr)
        sync = json.loads(result.stdout)["sync"]
        self.assertEqual(sync, {"status": "incomplete", "items": [], "unavailable_calendar_ids": [CAL]})

    def test_followup_turn_with_consumed_keys_needs_no_window(self):
        result = run(self.hub, payload(consumed=['["demo", "x"]']))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["sync"], {"status": "done-earlier-this-review"})


if __name__ == "__main__":
    unittest.main()
