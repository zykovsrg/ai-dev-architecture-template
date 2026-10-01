import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "modules/planning/scripts/calendar_drift.py"
JOURNAL = (REPO_ROOT / "modules/learning/data/ai/workflow-observations.md").read_text(encoding="utf-8")
CAL = "CAL-1"


def write_snapshot(hub, at, captured, lines):
    directory = hub / "ai/tmp/calendar-snapshots"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{at}--captured-{captured}--1-1.txt"
    path.write_text("".join(f"{line}|{CAL}\n" for line in lines), encoding="utf-8")


def run(hub, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--hub", str(hub), *args],
        capture_output=True, text=True, check=False,
    )


class CalendarDriftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hub = Path(self.tmp.name)
        (self.hub / "ai").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def journal(self):
        return (self.hub / "ai/workflow-observations.md").read_text(encoding="utf-8")

    def enable_learning(self):
        (self.hub / "ai/workflow-observations.md").write_text(JOURNAL, encoding="utf-8")

    def test_single_snapshot_reports_insufficient_data(self):
        write_snapshot(self.hub, "2026-10-01-0900", 100, ["10:00|11:00|работа/a/задача"])
        result = run(self.hub, "diff", "--day", "2026-10-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("недостаточно снимков", result.stdout)

    def test_detects_moved_resized_removed_added(self):
        write_snapshot(self.hub, "2026-10-01-0900", 100, [
            "00:00|00:00|дела/весь день",
            "00:00|23:59|дела/таблетки",
            "10:00|11:00|работа/a/перенос",
            "12:00|13:00|работа/a/дольше",
            "14:00|15:00|работа/a/отмена",
        ])
        write_snapshot(self.hub, "2026-10-01-2100", 200, [
            "00:00|00:00|дела/весь день",
            "16:00|17:00|работа/a/перенос",
            "12:00|14:00|работа/a/дольше",
            "18:00|18:30|дела/новое",
        ])
        out = run(self.hub, "diff", "--day", "2026-10-01").stdout
        self.assertIn("- 2026-10-01 | evening-review | calendar | сдвиг: работа/a/перенос 10:00-11:00 → 16:00-17:00", out)
        self.assertIn("- 2026-10-01 | evening-review | calendar | длительность: работа/a/дольше 60 → 120 мин", out)
        self.assertIn("- 2026-10-01 | evening-review | calendar | отмена: работа/a/отмена 14:00-15:00", out)
        self.assertIn("- 2026-10-01 | evening-review | calendar | добавлено: дела/новое 18:00-18:30", out)
        self.assertNotIn("весь день", out)
        self.assertNotIn("таблетки", out)

    def test_uses_earliest_and_latest_snapshot_of_the_day(self):
        write_snapshot(self.hub, "2026-10-01-0900", 100, ["10:00|11:00|работа/a/x"])
        write_snapshot(self.hub, "2026-10-01-1200", 150, ["11:00|12:00|работа/a/x"])
        write_snapshot(self.hub, "2026-10-01-2100", 200, ["10:00|11:00|работа/a/x"])
        write_snapshot(self.hub, "2026-10-02-0900", 300, [])
        out = run(self.hub, "diff", "--day", "2026-10-01").stdout
        self.assertIn("расхождений нет", out)

    def test_write_appends_once_and_only_with_learning(self):
        write_snapshot(self.hub, "2026-10-01-0900", 100, ["14:00|15:00|работа/a/отмена"])
        write_snapshot(self.hub, "2026-10-01-2100", 200, [])
        result = run(self.hub, "diff", "--day", "2026-10-01", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("модуль learning выключен", result.stdout)
        self.assertFalse((self.hub / "ai/workflow-observations.md").exists())

        self.enable_learning()
        run(self.hub, "diff", "--day", "2026-10-01", "--write")
        run(self.hub, "diff", "--day", "2026-10-01", "--write")
        line = "- 2026-10-01 | evening-review | calendar | отмена: работа/a/отмена 14:00-15:00"
        self.assertEqual(self.journal().count(line), 1)
        self.assertTrue(self.journal().startswith(JOURNAL.rstrip("\n")))

    def test_summary_groups_repeats_by_project(self):
        self.enable_learning()
        entries = [
            "- 2026-09-05 | evening-review | calendar | сдвиг: работа/a/x 10:00-11:00 → 12:00-13:00",
            "- 2026-09-15 | evening-review | calendar | сдвиг: работа/a/долгое название 09:00-10:00 → 15:00-16:00",
            "- 2026-09-29 | evening-review | calendar | сдвиг: работа/a/z 09:00-10:00 → 15:00-16:00",
            "- 2026-09-29 | evening-review | calendar | отмена: дела/b 09:00-10:00",
            "- 2026-09-30 | evening-review | calendar | отмена: дела/c 09:00-10:00",
            "- 2026-09-10 | evening-review | calendar | длительность: дела/d 30 → 60 мин",
        ]
        with (self.hub / "ai/workflow-observations.md").open("a", encoding="utf-8") as journal:
            journal.write("\n".join(entries) + "\n")
        out = run(self.hub, "summary", "--until", "2026-10-01").stdout
        self.assertIn("сдвиг | работа/a | 3", out)
        self.assertIn("отмена | дела | 2", out)
        self.assertNotIn("длительность", out)

    def test_same_title_events_are_kept_separately(self):
        write_snapshot(self.hub, "2026-10-01-0900", 100, ["09:00|10:00|работа/a/фокус", "15:00|16:00|работа/a/фокус"])
        write_snapshot(self.hub, "2026-10-01-2100", 200, ["09:00|10:00|работа/a/фокус"])
        out = run(self.hub, "diff", "--day", "2026-10-01").stdout
        self.assertIn("отмена: работа/a/фокус 15:00-16:00", out)
        self.assertNotIn("сдвиг", out)

    def test_move_and_resize_records_both(self):
        write_snapshot(self.hub, "2026-10-01-0900", 100, ["10:00|11:00|работа/a/x"])
        write_snapshot(self.hub, "2026-10-01-2100", 200, ["15:00|17:00|работа/a/x"])
        out = run(self.hub, "diff", "--day", "2026-10-01").stdout
        self.assertIn("сдвиг: работа/a/x 10:00-11:00 → 15:00-17:00", out)
        self.assertIn("длительность: работа/a/x 60 → 120 мин", out)

    def test_rejects_bad_day(self):
        result = run(self.hub, "diff", "--day", "2026-13-01")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
