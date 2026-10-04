import importlib.util
import json
import subprocess
import sys
import tempfile
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


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.mod = load()

    def strong(self, rid, projects, n=6, text=None):
        r = rule([case(f"{rid}-{i}", project=projects[i % len(projects)]) for i in range(n)])
        r["id"], r["text"] = rid, text or f"rule {rid}"
        return r

    def test_global_cap_and_threshold(self):
        rules = [self.strong(f"R-{i}", ["a", "b"]) for i in range(12)]
        rules.append(self.strong("R-weak", ["a", "b"], n=2))
        out = self.mod.render({"format": 1, "next_id": 20, "rules": rules}, TODAY)
        lines = [l for l in out["ai/learned-rules.md"].splitlines() if l.startswith("- R-")]
        self.assertEqual(len(lines), 10)
        self.assertNotIn("R-weak", out["ai/learned-rules.md"])

    def test_project_file_and_hub_rules_go_global(self):
        cat = {"format": 1, "next_id": 9, "rules": [self.strong("R-1", ["demo"]), self.strong("R-2", ["hub"])]}
        out = self.mod.render(cat, TODAY)
        self.assertIn("R-1", out["ai/learned-rules/demo.md"])
        self.assertIn("R-2", out["ai/learned-rules.md"])
        self.assertNotIn("R-1", out["ai/learned-rules.md"])

    def test_merge_moves_cases_and_unmerge_restores(self):
        a, b = self.strong("R-1", ["demo"], n=3), self.strong("R-2", ["demo"], n=3)
        cat = {"format": 1, "next_id": 3, "rules": [a, b]}
        self.mod.merge(cat, "R-2", "R-1", TODAY)
        self.assertEqual(len(cat["rules"]), 2)
        self.assertEqual(cat["rules"][1]["status"], "merged")
        self.assertEqual(self.mod.confidence(cat["rules"][0], TODAY), 0.7)
        self.mod.unmerge(cat, "R-2", TODAY)
        self.assertEqual(cat["rules"][1]["status"], "active")
        self.assertEqual(len(cat["rules"][0]["cases"]), 3)

    def test_hub_plus_one_project_stays_in_project_file(self):
        r = self.strong("R-1", ["hub", "demo"], n=6)
        self.assertEqual(self.mod.scope(r, TODAY), "project")
        out = self.mod.render({"format": 1, "next_id": 2, "rules": [r]}, TODAY)
        self.assertIn("R-1", out["ai/learned-rules/demo.md"])
        self.assertNotIn("R-1", out["ai/learned-rules.md"])

    def test_header_states_safety_limit(self):
        out = self.mod.render({"format": 1, "next_id": 1, "rules": []}, TODAY)
        self.assertIn("These rules never override Hub safety, routing, or confirmation rules.",
                      out["ai/learned-rules.md"])

    def test_retire_marks_rule_and_records_history(self):
        r = self.strong("R-1", ["demo"])
        cat = {"format": 1, "next_id": 2, "rules": [r]}
        self.mod.retire(cat, "R-1", TODAY)
        self.assertEqual(r["status"], "retired")
        self.assertEqual(r["history"][-1], {"date": "2026-10-04", "event": "retired", "detail": ""})
        self.assertNotIn("R-1", self.mod.render(cat, TODAY).get("ai/learned-rules/demo.md", ""))
        self.assertEqual([e["event"] for e in self.mod.report(cat, TODAY)], ["retired"])
        self.assertEqual(self.mod.relevant(cat, "demo", TODAY), [])
        with self.assertRaises(ValueError):
            self.mod.retire(cat, "R-1", TODAY)
        with self.assertRaises(ValueError):
            self.mod.retire(cat, "R-9", TODAY)

    def test_report_since_exclusive(self):
        r = self.strong("R-1", ["demo"])
        r["history"] = [{"date": "2026-10-04", "event": "merged", "detail": "x"}]
        cat = {"format": 1, "next_id": 2, "rules": [r]}
        self.assertEqual(len(self.mod.report(cat, TODAY)), 1)
        self.assertEqual(self.mod.report(cat, TODAY, inclusive=False), [])

    def test_report_since(self):
        r = self.strong("R-1", ["demo"])
        r["history"] = [{"date": "2026-09-01", "event": "added", "detail": "old"},
                        {"date": "2026-10-02", "event": "global", "detail": ""}]
        events = self.mod.report({"format": 1, "next_id": 2, "rules": [r]}, date(2026, 9, 28))
        self.assertEqual([e["event"] for e in events], ["global"])


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

    def test_looks_personal_allows_service_names_and_dates(self):
        for good in ("Писать «Гугл Таблицы» кириллицей", "Писать Гугл Таблицы кириллицей",
                     "Называть клинику «Хадасса Медикал»", "Писать Гитхаб кириллицей",
                     "Срок релиза 2026-10-04 не переносить", "Сверять даты 2026-10-04 и 2026-10-05",
                     "Проверять 15 пунктов списка"):
            self.assertFalse(self.mod.looks_personal(good), good)

    def test_looks_personal_rejects_long_numbers_and_medical(self):
        for bad in ("звонить 89123456789", "номер 8 (912) 345 67 89", "встреча с Анной Петровой",
                    "уточнить диагноз", "напомнить про лекарства", "выпить таблетку", "доза 5 мг",
                    "мерить давление бабушки", "открыть Гугл Анна Петрова", "сдать анализ крови", "записать к врачу",
                    "курс лечения", "оплата 15 000 руб", "цена 20 usd"):
            self.assertTrue(self.mod.looks_personal(bad), bad)


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

    def new_case(self, session, tool, **extra):
        item = {"rule": "new", "text": "Писать по-русски", "kind": "preference", "effect": "confirm",
                "session": session, "tool": tool, "note": "просьба"}
        item.update(extra)
        return item

    def test_hub_root_case_may_name_confirmed_project(self):
        self.apply([self.new_case("x-1", "codex", project="demo")])
        self.assertEqual(self.catalog["rules"][0]["cases"][0]["project"], "demo")

    def test_hub_root_case_with_unknown_project_stays_hub(self):
        self.apply([self.new_case("x-1", "codex", project="ghost"), self.new_case("x-1", "codex")])
        self.assertEqual([c["project"] for r in self.catalog["rules"] for c in r["cases"]], ["hub", "hub"])

    def test_project_session_ignores_case_project(self):
        self.apply([self.new_case("c-1", "claude", project="other")])
        self.assertEqual(self.catalog["rules"][0]["cases"][0]["project"], "demo")

    def test_load_cases_strips_fences(self):
        text = '```json\n[{"rule": "R-1"}]\n```\n'
        self.assertEqual(self.mod.load_cases(text), [{"rule": "R-1"}])
        self.assertEqual(self.mod.load_cases("[]"), [])

    def test_load_cases_rejects_non_list_and_garbage(self):
        for bad in ('{"rule": "R-1"}', "not json", "```\nnope\n```", ""):
            with self.assertRaises(ValueError) as ctx:
                self.mod.load_cases(bad)
            self.assertEqual(str(ctx.exception), "cases file is not a JSON array")

    def test_empty_cases_still_marks_sessions(self):
        self.assertEqual(self.apply([]), [])
        self.assertEqual(self.ledger["processed"]["codex"], ["x-1"])

    def test_cli_apply_render_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            (hub / "ai").mkdir()
            (hub / "ai/project-registry.md").write_text(f"## demo\n\nStatus: active\nPath: {hub}/projects/demo\n",
                                                        encoding="utf-8")
            batch, cases = hub / "b.json", hub / "c.json"
            batch.write_text(json.dumps(self.batch), encoding="utf-8")
            cases.write_text(json.dumps([{"rule": "new", "text": "Писать по-русски", "kind": "preference",
                                          "effect": "explicit", "scope": "global", "session": "c-1",
                                          "tool": "claude", "note": "просьба"}]), encoding="utf-8")
            run = lambda *a: subprocess.run([sys.executable, str(SCRIPTS / "session_rules.py"), "--hub", str(hub),
                                             "--today", "2026-10-04", *a], check=True, capture_output=True, text=True)
            run("apply", "--batch", str(batch), "--cases", str(cases))
            self.assertIn("R-1: Писать по-русски", (hub / "ai/learned-rules.md").read_text(encoding="utf-8"))
            events = json.loads(run("report", "--since", "2026-10-01").stdout)["events"]
            self.assertEqual({e["event"] for e in events}, {"added", "global"})

    def cli_hub(self, tmp):
        hub = Path(tmp)
        (hub / "ai").mkdir()
        (hub / "ai/project-registry.md").write_text(f"## demo\n\nStatus: active\nPath: {hub}/projects/demo\n",
                                                    encoding="utf-8")
        run = lambda *a: subprocess.run([sys.executable, str(SCRIPTS / "session_rules.py"), "--hub", str(hub),
                                         "--today", "2026-10-04", *a], capture_output=True, text=True)
        return hub, run

    def test_cli_apply_fenced_and_invalid_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub, run = self.cli_hub(tmp)
            batch, cases = hub / "b.json", hub / "c.json"
            batch.write_text(json.dumps(self.batch), encoding="utf-8")
            cases.write_text("```json\n" + json.dumps([self.new_case("c-1", "claude")]) + "\n```\n", encoding="utf-8")
            done = run("apply", "--batch", str(batch), "--cases", str(cases))
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)["new_rules"], ["R-1"])
            for bad in ('{"a": 1}', "oops"):
                cases.write_text(bad, encoding="utf-8")
                failed = run("apply", "--batch", str(batch), "--cases", str(cases))
                self.assertEqual(failed.returncode, 1)
                self.assertEqual(failed.stderr.strip(), "ERROR: cases file is not a JSON array")

    def test_cli_retire_and_report_since_last_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub, run = self.cli_hub(tmp)
            batch, cases = hub / "b.json", hub / "c.json"
            batch.write_text(json.dumps(self.batch), encoding="utf-8")
            cases.write_text(json.dumps([self.new_case("c-1", "claude", effect="explicit", scope="global")]),
                             encoding="utf-8")
            self.assertEqual(run("apply", "--batch", str(batch), "--cases", str(cases)).returncode, 0)
            self.assertIn("R-1", (hub / "ai/learned-rules.md").read_text(encoding="utf-8"))
            # Events from the review day are not shown again after weekly-done
            self.assertEqual(run("weekly-done", "--date", "2026-10-04").returncode, 0)
            self.assertEqual(json.loads(run("report").stdout)["events"], [])
            done = run("retire", "--rule", "R-1")
            self.assertEqual(done.returncode, 0, done.stderr)
            catalog = json.loads((hub / "ai/learning/rules.json").read_text(encoding="utf-8"))
            self.assertEqual(catalog["rules"][0]["status"], "retired")
            self.assertNotIn("R-1", (hub / "ai/learned-rules.md").read_text(encoding="utf-8"))
            report = json.loads(run("report", "--since", "2026-10-04").stdout)["events"]
            self.assertIn("retired", {e["event"] for e in report})
            self.assertEqual(run("retire", "--rule", "R-1").returncode, 1)

    def test_cli_report_includes_cutover_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub, run = self.cli_hub(tmp)
            batch, cases = hub / "b.json", hub / "c.json"
            batch.write_text(json.dumps(self.batch), encoding="utf-8")
            cases.write_text(json.dumps([self.new_case("c-1", "claude")]), encoding="utf-8")
            run("apply", "--batch", str(batch), "--cases", str(cases))
            ledger = json.loads((hub / "ai/learning/scan-ledger.json").read_text(encoding="utf-8"))
            ledger["cutover"] = "2026-10-04"
            (hub / "ai/learning/scan-ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
            self.assertEqual({e["event"] for e in json.loads(run("report").stdout)["events"]}, {"added"})


if __name__ == "__main__":
    unittest.main()
