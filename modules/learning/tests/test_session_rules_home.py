#!/usr/bin/env python3
"""Regression checks: new rules that repeat CLAUDE.md / AGENTS.md are skipped."""

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from session_rules import (GLOBAL_LIMIT, apply_batch, check_home, check_limits, duplicates_standing,  # noqa: E402
                           retire, standing_instructions)


STANDING = "# Hub\n\n- Use the active voice: say who did what.\n- One sentence carries one idea; keep sentences to about 20 words.\n"


def case(text):
    return {"rule": "new", "text": text, "kind": "preference", "effect": "explicit", "scope": "global",
            "session": "s1", "tool": "claude", "note": "The user stated a preference."}


class StandingDuplicateTests(unittest.TestCase):
    def test_detects_paraphrase_and_keeps_new_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            (hub / "CLAUDE.md").write_text(STANDING)
            standing = standing_instructions(hub)
            self.assertTrue(duplicates_standing("One sentence carries one idea; keep sentences to about twenty words.", standing))
            self.assertFalse(duplicates_standing("Treat paused tasks as active work in plans.", standing))
            self.assertFalse(duplicates_standing("Do not use the active voice.", standing))
            self.assertFalse(duplicates_standing("Treat paused tasks as active work.", ["Never treat paused tasks as active work."]))
            self.assertTrue(duplicates_standing("Never delete a whole series.", ["Never delete the whole series of events."]))

    def test_apply_skips_duplicate(self):
        catalog = {"next_id": 1, "rules": []}
        ledger = {"processed": {"claude": [], "codex": []}}
        batch = {"sessions": [{"tool": "claude", "id": "s1", "date": "2026-10-08", "project": "hub"}]}
        skipped = []
        new = apply_batch(catalog, ledger, batch,
                          [case("Use the active voice: say who did what."), case("Treat paused tasks as active work.")],
                          set(), date(2026, 10, 8), "now", ["Use the active voice: say who did what."], skipped)
        self.assertEqual(new, ["R-1"])
        self.assertEqual(skipped, ["Use the active voice: say who did what."])
        self.assertEqual(ledger["processed"]["claude"], ["s1"])


class LeakTests(unittest.TestCase):
    def _catalog(self, note):
        rule = {"id": "R-1", "text": "Treat paused tasks as active work in plans.", "kind": "preference",
                "status": "retired", "merged_into": None, "explicit_scope": "global", "created": "2026-10-01",
                "cases": [], "history": [{"date": "2026-10-08", "event": "retired", "detail": note}]}
        return {"next_id": 2, "rules": [rule]}

    def _run(self, catalog):
        ledger = {"processed": {"claude": [], "codex": []}}
        batch = {"sessions": [{"tool": "claude", "id": "s1", "date": "2026-10-09", "project": "hub"}]}
        leaks = []
        new = apply_batch(catalog, ledger, batch, [case("Treat paused tasks as active work in plans.")],
                          set(), date(2026, 10, 9), "now", [], [], leaks)
        return new, leaks, ledger

    def test_similar_to_moved_rule_is_leak(self):
        catalog = self._catalog("moved to ai/rules/planning.md")
        new, leaks, ledger = self._run(catalog)
        self.assertEqual(new, [])
        self.assertEqual(leaks, [{"rule": "R-1", "session": "s1"}])
        rule = catalog["rules"][0]
        self.assertEqual(rule["status"], "retired")
        self.assertEqual(rule["cases"][-1]["effect"], "leak")
        self.assertEqual(rule["history"][-1]["event"], "leak")
        self.assertEqual(ledger["processed"]["claude"], ["s1"])

    def test_retired_without_move_note_is_not_leak(self):
        catalog = self._catalog("")
        new, leaks, _ = self._run(catalog)
        self.assertEqual(new, ["R-2"])
        self.assertEqual(leaks, [])


class HomeAndLimitTests(unittest.TestCase):
    def test_check_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            (hub / "ai/rules").mkdir(parents=True)
            (hub / "ai/rules/calendar.md").write_text("Work meetings go into\nthe urgent calendar.\n")
            (hub / "projects/p").mkdir(parents=True)
            (hub / "projects/p/x.md").write_text("Work meetings go into the urgent calendar.\n")
            (hub / "ai/rules/link.md").symlink_to(hub / "ai/rules/calendar.md")
            self.assertTrue(check_home(hub, "ai/rules/calendar.md", "meetings go into the urgent")[0])
            self.assertFalse(check_home(hub, "ai/rules/calendar.md", "never written")[0])
            self.assertFalse(check_home(hub, "../x.md", "a")[0])
            self.assertFalse(check_home(hub, str(hub / "ai/rules/calendar.md"), "Work")[0])
            self.assertFalse(check_home(hub, "ai/rules/link.md", "Work")[0])
            self.assertFalse(check_home(hub, "projects/p/x.md", "Work")[0])

    def test_check_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            (hub / "ai/skills/a").mkdir(parents=True)
            (hub / "ai/skills/a/SKILL.md").write_text("x\n" * 301)
            (hub / "ai/skills/a/ok.md").write_text("x\n" * 300)
            self.assertEqual(check_limits(hub), [{"file": "ai/skills/a/SKILL.md", "lines": 301}])


class RetireNoteTests(unittest.TestCase):
    def test_retire_keeps_note_and_limit_is_30(self):
        catalog = {"rules": [{"id": "R-1", "status": "active", "history": []}]}
        retire(catalog, "R-1", date(2026, 10, 8), "moved to ai/rules/planning.md")
        self.assertEqual(catalog["rules"][0]["status"], "retired")
        self.assertEqual(catalog["rules"][0]["history"][-1]["detail"], "moved to ai/rules/planning.md")
        self.assertEqual(GLOBAL_LIMIT, 30)


if __name__ == "__main__":
    unittest.main()
