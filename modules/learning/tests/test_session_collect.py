import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parents[0] / "scripts/session_collect.py"


def load():
    spec = importlib.util.spec_from_file_location("session_collect", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["session_collect"] = mod
    spec.loader.exec_module(mod)
    return mod


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.mod = load()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.hub = root / "hub"
        (self.hub / "ai").mkdir(parents=True)
        (self.hub / "projects/demo").mkdir(parents=True)
        (self.hub / "ai/project-registry.md").write_text(
            f"## demo\n\nStatus: active\nPath: {self.hub / 'projects/demo'}\n", encoding="utf-8")
        self.claude = root / "claude"
        self.codex = root / "codex/2026/10/04"
        (self.claude / "slug").mkdir(parents=True)
        self.codex.mkdir(parents=True)
        # Set file mtime to 2 hours before test's fixed 'now' time to ensure they're not considered active
        old_dt = datetime(2026, 10, 4, 10, 0, 0, tzinfo=timezone.utc)
        old_ts = old_dt.timestamp()
        for name, dest in (("claude-hub.jsonl", self.claude / "slug/c-1.jsonl"),
                           ("claude-other.jsonl", self.claude / "slug/c-2.jsonl"),
                           ("codex-hub.jsonl", self.codex / "rollout-x-1.jsonl")):
            text = (HERE / "fixtures" / name).read_text(encoding="utf-8").replace("HUB", str(self.hub))
            dest.write_text(text, encoding="utf-8")
            os.utime(dest, (old_ts, old_ts))
        # Fourth fixture for scanner session test
        scanner_fixture = self.claude / "slug/c-3.jsonl"
        scanner_text = f'{{"type":"user","sessionId":"c-3","cwd":"{self.hub}","timestamp":"2026-10-04T08:00:00Z","isSidechain":false,"message":{{"role":"user","content":"[hub-session-scan] batch"}}}}\n'
        scanner_fixture.write_text(scanner_text, encoding="utf-8")
        os.utime(scanner_fixture, (old_ts, old_ts))

    def tearDown(self):
        self.tmp.cleanup()

    def pending(self, ledger):
        now = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
        return self.mod.pending(self.hub, ledger, now, self.claude, self.codex.parents[2])

    def ledger(self, cutover="2026-10-04"):
        return {"format": 1, "cutover": cutover, "last_scan": None, "last_weekly_review": None,
                "processed": {"claude": [], "codex": []},
                "sources": {"observations_lines": 0, "session_reviews": []}}

    def test_claude_parse_strips_reminders_sidechain_and_keeps_errors(self):
        s = self.mod.parse_claude(self.claude / "slug/c-1.jsonl")
        self.assertEqual(s.id, "c-1")
        self.assertIn(("user", "Пиши по-русски"), s.turns)
        self.assertIn(("error", "Bash: permission denied"), s.turns)
        self.assertNotIn("sidechain", self.mod.normalize(s))
        self.assertNotIn("ignore me", self.mod.normalize(s))

    def test_codex_parse_skips_injected_context(self):
        s = self.mod.parse_codex(self.codex / "rollout-x-1.jsonl")
        self.assertEqual((s.id, s.tool), ("x-1", "codex"))
        self.assertEqual([t for t in s.turns if t[0] == "user"], [("user", "Не пиши GitHub латиницей")])
        self.assertIn(("error", "exec: error: rejected"), s.turns)

    def test_pending_filters_to_hub_and_cutover(self):
        ids = sorted(s.id for s in self.pending(self.ledger()))
        self.assertEqual(ids, ["c-1", "x-1"])
        self.assertEqual(self.pending(self.ledger(cutover="2026-10-05")), [])

    def test_processed_and_active_sessions_are_skipped(self):
        ledger = self.ledger()
        self.mod.mark_processed(ledger, "claude", ["c-1"], "2026-10-04T12:00:00Z")
        self.assertEqual([s.id for s in self.pending(ledger)], ["x-1"])
        os.utime(self.codex / "rollout-x-1.jsonl", None)
        now = datetime.now(timezone.utc)
        self.assertEqual(self.mod.pending(self.hub, ledger, now, self.claude, self.codex.parents[2]), [])

    def test_project_for_uses_registry(self):
        self.assertEqual(self.mod.project_for(str(self.hub / "projects/demo/sub"), self.hub), "demo")
        self.assertEqual(self.mod.project_for(str(self.hub), self.hub), "hub")

    def test_normalize_caps_length(self):
        s = self.mod.parse_claude(self.claude / "slug/c-1.jsonl")
        s.turns = [("user", "x" * 900)] * 200
        text = self.mod.normalize(s, limit=5000)
        self.assertLessEqual(len(text), 5100)
        self.assertIn("[cut]", text)

    def test_cli_status_and_batch(self):
        import subprocess, sys
        base = [sys.executable, str(SCRIPT), "--hub", str(self.hub),
                "--claude-root", str(self.claude), "--codex-root", str(self.codex.parents[2])]
        subprocess.run(base + ["init", "--cutover", "2026-10-04"], check=True)
        status = json.loads(subprocess.run(base + ["status"], check=True, capture_output=True, text=True).stdout)
        self.assertEqual(status["pending"], {"claude": 1, "codex": 1})
        out_dir = (Path(self.tmp.name) / "scan").resolve()
        result = json.loads(subprocess.run(base + ["batch", "--limit", "10", "--out-dir", str(out_dir)],
                                           check=True, capture_output=True, text=True).stdout)
        self.assertEqual(result["index"], str(out_dir / "index.json"))
        batch = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
        self.assertEqual({b["project"] for b in batch["sessions"]}, {"hub", "demo"})
        for entry in batch["sessions"]:
            self.assertNotIn("text", entry)
            self.assertTrue(Path(entry["file"]).is_file())
        # Nothing with transcript text is written inside the Hub
        self.assertFalse((self.hub / "ai/tmp").exists())
        # --session builds a single-session batch, --skip leaves a session out
        one = json.loads(subprocess.run(base + ["batch", "--out-dir", str(out_dir), "--session", "codex:x-1"],
                                        check=True, capture_output=True, text=True).stdout)
        self.assertEqual(one["written"], 1)
        index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
        self.assertEqual([s["id"] for s in index["sessions"]], ["x-1"])
        skip = json.loads(subprocess.run(base + ["batch", "--out-dir", str(out_dir), "--skip", "codex:x-1"],
                                         check=True, capture_output=True, text=True).stdout)
        index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
        self.assertEqual([s["id"] for s in index["sessions"]], ["c-1"])
        self.assertEqual(skip["remaining"], 0)

    def test_batch_default_dir_is_outside_hub(self):
        default = self.mod.default_batch_dir()
        self.assertEqual(default.name, "hub-session-scan")
        self.assertFalse(self.mod._inside(default, self.hub))

    def session(self, sid, size):
        return self.mod.Session("claude", sid, str(self.hub), "2026-10-04T08:00:00Z", Path("x"),
                                [("user", "я" * 400 + "\n" + "б" * 90)] * (size // 500))

    def test_write_batch_limits_total_size_and_writes_plain_text_files(self):
        out_dir = Path(self.tmp.name) / "scan"
        sessions = [self.session(f"s-{i}", 25000) for i in range(3)]
        index, remaining = self.mod.write_batch(self.hub, sessions, out_dir, limit=10, max_chars=60000)
        self.assertEqual([s["id"] for s in index["sessions"]], ["s-0", "s-1"])
        self.assertEqual(remaining, 1)
        total = 0
        for entry in index["sessions"]:
            text = Path(entry["file"]).read_text(encoding="utf-8")
            self.assertEqual(Path(entry["file"]).parent, out_dir)
            self.assertIn("\nUSER: ", text)
            self.assertGreater(text.count("\n"), 40)
            total += entry["chars"]
        self.assertLessEqual(total, 60000)
        self.assertEqual(json.loads((out_dir / "index.json").read_text(encoding="utf-8")), index)

    def test_write_batch_count_limit_and_oversize_first_session(self):
        out_dir = Path(self.tmp.name) / "scan"
        small = [self.session(f"s-{i}", 1000) for i in range(12)]
        index, remaining = self.mod.write_batch(self.hub, small, out_dir, limit=10, max_chars=60000)
        self.assertEqual((len(index["sessions"]), remaining), (10, 2))
        big = [self.session("big", 90000)]
        index, remaining = self.mod.write_batch(self.hub, big, out_dir, limit=10, max_chars=60000)
        self.assertEqual((len(index["sessions"]), remaining), (1, 0))
        self.assertLessEqual(index["sessions"][0]["chars"], 60000)

    def test_write_batch_blanks_stale_session_files(self):
        out_dir = Path(self.tmp.name) / "scan"
        out_dir.mkdir()
        stale = out_dir / "claude-old.txt"
        stale.write_text("old transcript", encoding="utf-8")
        self.mod.write_batch(self.hub, [self.session("s-1", 1000)], out_dir)
        self.assertTrue(stale.exists())
        self.assertEqual(stale.read_text(encoding="utf-8"), "")

    def test_archived_project_maps_to_hub(self):
        (self.hub / "projects/old").mkdir(parents=True)
        (self.hub / "ai/project-registry.md").write_text(
            f"## demo\n\nStatus: active\nPath: {self.hub / 'projects/demo'}\n\n"
            f"## old\n\nStatus: archived\nPath: {self.hub / 'projects/old'}\n", encoding="utf-8")
        self.assertEqual(self.mod.project_for(str(self.hub / "projects/old/x"), self.hub), "hub")
        self.assertEqual(self.mod.project_for(str(self.hub / "projects/demo"), self.hub), "demo")

    def test_scan_turns_are_dropped(self):
        long_cd = "cd " + "/very/long/path" * 20 + " && "
        lines = [
            {"type": "user", "message": {"role": "user", "content": "привет"}},
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": long_cd + "python3 scripts/session_collect.py --hub . batch"}}]}},
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "t2", "name": "Bash",
                 "input": {"command": "python3 scripts/session_rules.py --hub . apply --batch b --cases c"}}]}},
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "text", "text": "Скан готов: новое правило R-1"}]}},
            {"type": "user", "message": {"role": "user", "content": "ещё вопрос"}},
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ответ"}]}},
        ]
        path = self.claude / "slug/c-9.jsonl"
        with open(path, "w", encoding="utf-8") as handle:
            for rec in lines:
                rec.update({"sessionId": "c-9", "cwd": str(self.hub), "timestamp": "2026-10-04T08:00:00Z"})
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
        old_ts = datetime(2026, 10, 4, 10, tzinfo=timezone.utc).timestamp()
        os.utime(path, (old_ts, old_ts))
        session = next(s for s in self.pending(self.ledger()) if s.id == "c-9")
        text = self.mod.normalize(session)
        self.assertIn("привет", text)
        self.assertIn("ещё вопрос", text)
        self.assertIn("ответ", text)
        self.assertNotIn("Скан готов", text)
        self.assertNotIn("session_collect.py", text)
        self.assertNotIn("session_rules.py", text)

    def test_scanner_sessions_are_skipped(self):
        ids = sorted(s.id for s in self.pending(self.ledger()))
        self.assertNotIn("c-3", ids)

    def test_observations_and_reviews_become_sessions(self):
        (self.hub / "ai/workflow-observations.md").write_text(
            "# Журнал\n\n## Записи\n- 2026-10-03 | day-plan | friction | старое\n"
            "- 2026-10-04 | day-plan | friction | а\n- 2026-10-04 | day-plan | friction | б\n",
            encoding="utf-8")
        reviews = self.hub / "projects/demo/ai/session-reviews"
        reviews.mkdir(parents=True)
        (reviews / "2026-10-04-x.md").write_text("# Session review\n\n## Findings\n\nF1: агент забыл тест\n\n## Follow-up\n\nnone\n",
                                                 encoding="utf-8")
        (reviews / "2026-10-03-old.md").write_text("# Session review\n\n## Findings\n\nF1: старое\n\n## Follow-up\n\nnone\n",
                                                   encoding="utf-8")
        ledger = self.ledger()
        ids = sorted(s.id for s in self.mod.extra_sources(self.hub, ledger))
        self.assertEqual(ids, ["obs-2", "obs-3", "review-demo-2026-10-04-x"])
        self.mod.mark_processed(ledger, "claude", ids, "2026-10-04T12:00:00Z")
        self.assertEqual(self.mod.extra_sources(self.hub, ledger), [])
        self.assertEqual(self.mod.extra_sources(self.hub, self.ledger(cutover=None)), [])


if __name__ == "__main__":
    unittest.main()
