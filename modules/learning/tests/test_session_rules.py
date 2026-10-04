import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load():
    spec = importlib.util.spec_from_file_location("session_rules", SCRIPTS / "session_rules.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rule(cases, explicit_scope=None):
    return {"id": "R-1", "text": "t", "kind": "preference", "status": "active", "merged_into": None,
            "explicit_scope": explicit_scope, "created": "2026-10-01", "cases": cases, "history": []}


def case(session, effect="confirm", project="p", day="2026-10-01"):
    return {"effect": effect, "project": project, "tool": "claude", "session": session, "date": day, "note": "n"}


TODAY = date(2026, 10, 4)


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.mod = load()

    def test_table(self):
        for n, expected in ((1, 0.3), (2, 0.3), (3, 0.5), (5, 0.5), (6, 0.7), (10, 0.7), (11, 0.85)):
            r = rule([case(f"s{i}") for i in range(n)])
            self.assertEqual(self.mod.confidence(r, TODAY), expected, n)

    def test_repeats_in_one_session_count_once(self):
        self.assertEqual(self.mod.confidence(rule([case("s")] * 5), TODAY), 0.3)

    def test_explicit_and_contradict(self):
        self.assertEqual(self.mod.confidence(rule([case("s", "explicit")]), TODAY), 0.7)
        r = rule([case(f"s{i}") for i in range(6)] + [case("x", "contradict"), case("y", "contradict")])
        self.assertEqual(self.mod.confidence(r, TODAY), 0.5)

    def test_decay_after_four_weeks(self):
        r = rule([case(f"s{i}", day="2026-08-01") for i in range(6)])
        # 2026-08-01 -> 2026-10-04 is 64 days = 9 full weeks; 5 weeks past grace
        self.assertEqual(self.mod.confidence(r, TODAY), 0.6)

    def test_clamp(self):
        r = rule([case("s", "contradict")])
        self.assertEqual(self.mod.confidence(r, TODAY), 0.0)

    def test_scope(self):
        one = rule([case(f"s{i}") for i in range(6)])
        self.assertEqual(self.mod.scope(one, TODAY), "project")
        two = rule([case(f"s{i}", project="a" if i % 2 else "b") for i in range(6)])
        self.assertEqual(self.mod.scope(two, TODAY), "global")
        weak = rule([case("s1", project="a"), case("s2", project="b")])
        self.assertEqual(self.mod.scope(weak, TODAY), "project")
        self.assertEqual(self.mod.scope(rule([case("s", "explicit")], "global"), TODAY), "global")

    def test_looks_personal(self):
        for bad in ("позвонить +7 912 345-67-89", "mail a@b.ru", "оплата 15 000 ₽",
                    "встреча с Анной Петровой"):
            self.assertTrue(self.mod.looks_personal(bad), bad)
        self.assertFalse(self.mod.looks_personal("Писать названия сервисов кириллицей"))
        self.assertFalse(self.mod.looks_personal("Писать «Гитхаб» кириллицей"))


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.mod = load()
        self.catalog = {"format": 1, "next_id": 1, "rules": []}
        self.ledger = {"format": 1, "cutover": "2026-10-04", "last_scan": None, "last_weekly_review": None,
                       "processed": {"claude": [], "codex": []},
                       "sources": {"observations_lines": 0, "session_reviews": []}}
        self.batch = {"sessions": [{"tool": "claude", "id": "c-1", "date": "2026-10-04", "project": "demo", "text": ""},
                                   {"tool": "codex", "id": "x-1", "date": "2026-10-04", "project": "hub", "text": ""}]}

    def apply(self, cases):
        return self.mod.apply_batch(self.catalog, self.ledger, self.batch, cases, {"demo"}, TODAY,
                                    "2026-10-04T12:00:00Z")

    def test_new_rule_then_existing_id(self):
        ids = self.apply([{"rule": "new", "text": "Писать по-русски", "kind": "preference",
                           "effect": "explicit", "scope": "global", "session": "c-1", "tool": "claude", "note": "просьба"}])
        self.assertEqual(ids, ["R-1"])
        self.assertEqual(self.catalog["rules"][0]["explicit_scope"], "global")
        self.assertEqual(self.catalog["rules"][0]["cases"][0]["project"], "demo")
        self.assertEqual(self.ledger["processed"], {"claude": ["c-1"], "codex": ["x-1"]})

    def test_invalid_case_changes_nothing(self):
        bad = [{"rule": "R-9", "effect": "confirm", "session": "c-1", "tool": "claude", "note": "n"}]
        with self.assertRaises(ValueError):
            self.apply(bad)
        self.assertEqual(self.catalog["rules"], [])
        self.assertEqual(self.ledger["processed"], {"claude": [], "codex": []})

    def test_rejects_unknown_session_and_personal_note(self):
        for bad in ({"rule": "new", "text": "t", "kind": "preference", "effect": "confirm",
                     "session": "zzz", "tool": "claude", "note": "n"},
                    {"rule": "new", "text": "звонить +7 912 345-67-89", "kind": "preference", "effect": "confirm",
                     "session": "c-1", "tool": "claude", "note": "n"}):
            with self.assertRaises(ValueError):
                self.apply([bad])

    def test_empty_cases_still_marks_sessions(self):
        self.assertEqual(self.apply([]), [])
        self.assertEqual(self.ledger["processed"]["codex"], ["x-1"])


if __name__ == "__main__":
    unittest.main()
