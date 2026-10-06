#!/usr/bin/env python3
import atexit
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = Path(tempfile.mkdtemp(prefix="calendar-task-sync-stage-"))
atexit.register(shutil.rmtree, STAGE, ignore_errors=True)
subprocess.run(["bash", str(HERE / "stage-scripts.sh"), str(STAGE)], check=True)
ROOT = STAGE
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("calendar_task_sync", ROOT / "calendar_task_sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

LINK = "Событие: CAL/EV-1 · синхронизировано: 2026-09-22 15:00-17:00"


def make_hub(tmp: Path, future_body: str) -> Path:
    project = tmp / "projects" / "demo"
    (project / "ai").mkdir(parents=True)
    (tmp / "ai").mkdir()
    (tmp / "ai/project-registry.md").write_text(f"## demo\n\nStatus: active\nPath: {project}\n", encoding="utf-8")
    (project / "ai/current-task.md").write_text("# Current Task\n\nStatus: empty\n\n## Goal\n\nNo active task.\n", encoding="utf-8")
    (project / "ai/paused-tasks.md").write_text("# Paused Tasks\n", encoding="utf-8")
    (project / "ai/future-tasks.md").write_text("# Future Tasks\n\n" + future_body, encoding="utf-8")
    return tmp


class Collect(unittest.TestCase):
    def test_collects_linked_and_scheduled_only(self):
        body = ("### FT-20260915-001 — Связанная\n\nStatus: ready\nDue: 2026-09-23\nCreated: 2026-09-15\n"
                "Запланировано: 2026-09-22 15:00-17:00 (Europe/Kirov).\n" + LINK + "\n\n"
                "### FT-20260915-002 — Без времени\n\nStatus: ready\nCreated: 2026-09-15\n")
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(Path(tmp), body)
            rows = sync.collect_tasks(hub)
        self.assertEqual([r["task_id"] for r in rows], ["FT-20260915-001"])
        self.assertEqual(rows[0]["project_id"], "demo")
        self.assertEqual(rows[0]["event_link"]["event_id"], "EV-1")
        self.assertEqual(rows[0]["due"], "2026-09-23")


def task(sched=("2026-09-22 15:00", "2026-09-22 17:00"), synced=("2026-09-22 15:00", "2026-09-22 17:00"),
         status="ready", link=True, due=None):
    return {"project_id": "demo", "task_id": "FT-1", "title": "T", "status": status, "source_path": "p",
            "scheduled": sched, "due": due,
            "event_link": {"calendar_id": "CAL", "event_id": "EV-1",
                           "synced_start": synced[0], "synced_end": synced[1]} if link else None}


def event(start="2026-09-22T15:00:00+03:00", end="2026-09-22T17:00:00+03:00", eid="EV-1", title="хадасса/demo/T"):
    return {"id": eid, "calendar_id": "CAL", "title": title, "start": start, "end": end, "all_day": False}


NOW = "2026-09-21 09:00"


class Discrepancies(unittest.TestCase):
    def kinds(self, tasks, events, now=NOW):
        return [d["kind"] for d in sync.find_discrepancies(tasks, events, now)]

    def test_in_sync(self):
        self.assertEqual(self.kinds([task()], [event()]), [])

    def test_due_carried_into_item(self):
        [d] = sync.find_discrepancies([task(due="2026-09-23", sched=("2026-09-23 10:00", "2026-09-23 12:00"))],
                                       [event()], NOW)
        self.assertEqual(d["due"], "2026-09-23")

    def test_tz_conversion_avoids_false_calendar_moved(self):
        t = task(sched=("2026-09-22 15:00", "2026-09-22 17:00"), synced=("2026-09-22 15:00", "2026-09-22 17:00"))
        evs = [event("2026-09-22T12:00:00+00:00", "2026-09-22T14:00:00+00:00")]
        self.assertEqual(sync.find_discrepancies([t], evs, NOW, tz="Europe/Kirov"), [])

    def test_without_tz_conversion_would_be_calendar_moved(self):
        t = task(sched=("2026-09-22 15:00", "2026-09-22 17:00"), synced=("2026-09-22 15:00", "2026-09-22 17:00"))
        evs = [event("2026-09-22T12:00:00+00:00", "2026-09-22T14:00:00+00:00")]
        self.assertEqual(self.kinds([t], evs), ["calendar_moved"])

    def test_calendar_moved(self):
        self.assertEqual(self.kinds([task()], [event("2026-09-23T10:00:00+03:00", "2026-09-23T12:00:00+03:00")]), ["calendar_moved"])

    def test_task_moved(self):
        self.assertEqual(self.kinds([task(sched=("2026-09-23 10:00", "2026-09-23 12:00"))], [event()]), ["task_moved"])

    def test_both_moved(self):
        t = task(sched=("2026-09-24 10:00", "2026-09-24 11:00"))
        self.assertEqual(self.kinds([t], [event("2026-09-23T10:00:00+03:00", "2026-09-23T12:00:00+03:00")]), ["both_moved"])

    def test_stale_sync(self):
        t = task(sched=("2026-09-23 10:00", "2026-09-23 12:00"))
        self.assertEqual(self.kinds([t], [event("2026-09-23T10:00:00+03:00", "2026-09-23T12:00:00+03:00")]), ["stale_sync"])

    def test_event_missing(self):
        self.assertEqual(self.kinds([task()], []), ["event_missing"])

    def test_closed_with_future_event(self):
        self.assertEqual(self.kinds([task(status="done")], [event()]), ["closed_with_future_event"])
        self.assertEqual(self.kinds([task(status="dropped")], [event()]), ["closed_with_future_event"])

    def test_closed_with_past_event_is_quiet(self):
        self.assertEqual(self.kinds([task(status="done")], [event()], now="2026-09-23 09:00"), [])

    def test_closed_with_missing_event_is_quiet(self):
        self.assertEqual(self.kinds([task(status="done")], []), [])

    def test_unlinked_match(self):
        t = task(link=False)
        [d] = sync.find_discrepancies([t], [event()], NOW)
        self.assertEqual((d["kind"], d["event_id"]), ("unlinked", "EV-1"))

    def test_unlinked_rejects_other_title(self):
        self.assertEqual(self.kinds([task(link=False)], [event(title="work/demo/Other")]), [])

    def test_unlinked_rejects_competing_tasks(self):
        other = {**task(link=False), "task_id": "FT-2"}
        self.assertEqual(self.kinds([task(link=False), other], [event()]), [])

    def test_linked_checks_calendar(self):
        other = {**event(), "calendar_id": "OTHER"}
        self.assertEqual(self.kinds([task()], [other]), ["event_missing"])

    def test_linked_recurring_uses_exact_span(self):
        previous = event("2026-09-21T15:00:00+03:00", "2026-09-21T17:00:00+03:00")
        self.assertEqual(self.kinds([task()], [previous, event()]), [])

    def test_linked_recurring_missing_occurrence_is_ambiguous(self):
        events = [event("2026-09-20T15:00:00+03:00", "2026-09-20T17:00:00+03:00"),
                  event("2026-09-21T15:00:00+03:00", "2026-09-21T17:00:00+03:00")]
        self.assertEqual(self.kinds([task()], events), ["event_ambiguous"])

    def test_unlinked_does_not_steal_linked_event(self):
        linked = {**task(), "title": "Renamed", "task_id": "FT-2"}
        self.assertEqual(self.kinds([task(link=False), linked], [event()]), [])

    def test_single_recurring_event_is_not_unlinked(self):
        self.assertEqual(self.kinds([task(link=False)], [{**event(), "recurring": True}]), [])

    def test_single_moved_recurring_event_is_ambiguous(self):
        moved = {**event("2026-09-23T15:00:00+03:00", "2026-09-23T17:00:00+03:00"), "recurring": True}
        self.assertEqual(self.kinds([task()], [moved]), ["event_ambiguous"])

    def test_unlinked_task_title_can_contain_slash(self):
        t = {**task(link=False), "title": "A/B"}
        self.assertEqual(self.kinds([t], [event(title="work/demo/A/B")]), ["unlinked"])

    def test_unlinked_needs_project_in_title(self):
        self.assertEqual(self.kinds([task(link=False)], [event(title="дела/другое/задача")]), [])

    def test_unlinked_ambiguous_is_quiet(self):
        evs = [event(), event(eid="EV-2")]
        self.assertEqual(self.kinds([task(link=False)], evs), [])

    def test_unlinked_match_through_nested_title_resolver(self):
        resolve = lambda title: ("demo", "t") if title == "хадасса/промостраницы/демо/t" else None
        [d] = sync.find_discrepancies([task(link=False)], [event(title="хадасса/промостраницы/демо/t")], NOW,
                                      resolve=resolve)
        self.assertEqual(d["kind"], "unlinked")

    def test_recurring_never_unlinked_match(self):
        evs = [event(), event("2026-09-23T15:00:00+03:00", "2026-09-23T17:00:00+03:00")]
        self.assertEqual(self.kinds([task(link=False)], evs), [])


class DueAndPassed(unittest.TestCase):
    def kinds(self, tasks, events, now=NOW):
        return [d["kind"] for d in sync.find_discrepancies(tasks, events, now)]

    def test_block_after_due_is_reported(self):
        [d] = sync.find_discrepancies([task(due="2026-09-21")], [event()], NOW)
        self.assertEqual((d["kind"], d["due"], d["event"]),
                         ("scheduled_after_due", "2026-09-21", ["2026-09-22 15:00", "2026-09-22 17:00"]))

    def test_block_on_due_date_is_quiet(self):
        self.assertEqual(self.kinds([task(due="2026-09-22")], [event()]), [])

    def test_after_due_uses_moved_calendar_time(self):
        moved = event("2026-09-24T10:00:00+03:00", "2026-09-24T12:00:00+03:00")
        self.assertEqual(self.kinds([task(due="2026-09-23")], [moved]), ["calendar_moved", "scheduled_after_due"])

    def test_after_due_without_link_uses_task_schedule(self):
        self.assertEqual(self.kinds([task(link=False, due="2026-09-21")], []), ["scheduled_after_due"])

    def test_after_due_skips_closed_and_waiting(self):
        self.assertEqual(self.kinds([task(status="done", due="2026-09-21")], [event()], now="2026-09-23 09:00"), [])
        self.assertEqual(self.kinds([task(status="waiting", due="2026-09-21")], [event()]), [])

    def test_passed_block_of_open_task_is_reported(self):
        [d] = sync.find_discrepancies([task()], [event()], "2026-09-23 09:00")
        self.assertEqual((d["kind"], d["event"]), ("schedule_passed", ["2026-09-22 15:00", "2026-09-22 17:00"]))

    def test_block_earlier_today_is_left_to_evening_review(self):
        self.assertEqual(self.kinds([task()], [event()], now="2026-09-22 20:00"), [])

    def test_passed_wins_over_after_due(self):
        self.assertEqual(self.kinds([task(due="2026-09-21")], [event()], now="2026-09-23 09:00"), ["schedule_passed"])

    def test_passed_without_link(self):
        self.assertEqual(self.kinds([task(link=False)], [], now="2026-09-23 09:00"), ["schedule_passed"])

    def test_passed_skips_closed_and_waiting(self):
        self.assertEqual(self.kinds([task(status="waiting")], [event()], now="2026-09-23 09:00"), [])
        self.assertEqual(self.kinds([task(status="paused")], [event()], now="2026-09-23 09:00"), [])

    def test_missing_event_does_not_add_schedule_items(self):
        self.assertEqual(self.kinds([task(due="2026-09-21")], [], now="2026-09-23 09:00"), ["event_missing"])

    def test_ambiguous_event_does_not_add_schedule_items(self):
        events = [event("2026-09-20T15:00:00+03:00", "2026-09-20T17:00:00+03:00"),
                  event("2026-09-21T15:00:00+03:00", "2026-09-21T17:00:00+03:00")]
        self.assertEqual(self.kinds([task(due="2026-09-19")], events), ["event_ambiguous"])


class Cli(unittest.TestCase):
    def test_cli_prints_json(self):
        body = ("### FT-20260915-001 — Связанная\n\nStatus: ready\nCreated: 2026-09-15\n"
                "Запланировано: 2026-09-22 15:00-17:00 (Europe/Kirov).\n" + LINK + "\n")
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(Path(tmp), body)
            payload = json.dumps({"events": [event("2026-09-23T10:00:00+03:00", "2026-09-23T12:00:00+03:00")]})
            res = subprocess.run([sys.executable, str(ROOT / "calendar_task_sync.py"), "--hub", str(hub),
                                  "--now", NOW], input=payload, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual([d["kind"] for d in json.loads(res.stdout)], ["calendar_moved"])

    def test_cli_rejects_bad_json(self):
        res = subprocess.run([sys.executable, str(ROOT / "calendar_task_sync.py"), "--hub", "/nonexistent",
                              "--now", NOW], input="nope", capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)

    def test_cli_rejects_bad_now(self):
        res = subprocess.run([sys.executable, str(ROOT / "calendar_task_sync.py"), "--hub", "/nonexistent",
                              "--now", "not-a-date"], input="{}", capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)
        self.assertTrue(res.stderr.strip())


if __name__ == "__main__":
    unittest.main()
