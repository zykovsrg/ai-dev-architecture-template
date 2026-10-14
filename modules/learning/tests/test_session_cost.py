import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parents[0] / "scripts/session_cost.py"

U = {"input_tokens": 10, "cache_creation_input_tokens": 5,
     "cache_read_input_tokens": 100, "output_tokens": 2}


def load():
    spec = importlib.util.spec_from_file_location("session_cost", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["session_cost"] = mod
    spec.loader.exec_module(mod)
    return mod


# Claude Code record builders
def c_user(content, sid="c-1", cwd="HUB", ts="2026-10-12T08:00:00Z"):
    return {"type": "user", "sessionId": sid, "cwd": cwd, "timestamp": ts,
            "message": {"role": "user", "content": content}}


def c_result(tool_id, error=False, sid="c-1", cwd="HUB"):
    return c_user([{"type": "tool_result", "tool_use_id": tool_id, "is_error": error,
                    "content": "out"}], sid=sid, cwd=cwd)


def c_assistant(mid, items, usage=U, sid="c-1", cwd="HUB", ts="2026-10-12T08:00:01Z"):
    message = {"id": mid, "role": "assistant", "content": items}
    if usage is not None:
        message["usage"] = usage
    return {"type": "assistant", "sessionId": sid, "cwd": cwd, "timestamp": ts,
            "message": message}


def text(t):
    return {"type": "text", "text": t}


def tool(tid, name, value):
    return {"type": "tool_use", "id": tid, "name": name, "input": value}


# Codex record builders
def x_meta(sid="x-1", cwd="HUB", ts="2026-10-12T09:00:00Z"):
    return {"type": "session_meta", "payload": {"id": sid, "cwd": cwd, "timestamp": ts}}


def x_user(t):
    return {"type": "response_item", "payload": {"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": t}]}}


def x_say(t):
    return {"type": "response_item", "payload": {"type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": t}]}}


def x_call(cid, value, name="exec"):
    return {"type": "response_item", "payload": {"type": "custom_tool_call", "name": name,
            "call_id": cid, "input": value}}


def x_out(cid, output):
    return {"type": "response_item", "payload": {"type": "custom_tool_call_output",
            "call_id": cid, "output": output}}


def x_tokens(inp, cached, out, total):
    return {"type": "event_msg", "payload": {"type": "token_count", "info": {
        "total_token_usage": {"total_tokens": total},
        "last_token_usage": {"input_tokens": inp, "cached_input_tokens": cached,
                             "output_tokens": out, "reasoning_output_tokens": 1}}}}


def write(path, records, hub):
    body = "\n".join(r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)
                     for r in records)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.replace("HUB", str(hub)) + "\n", encoding="utf-8")


class Base(unittest.TestCase):
    def setUp(self):
        self.mod = load()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.hub = self.root / "hub"
        (self.hub / "ai").mkdir(parents=True)
        (self.hub / "projects/demo").mkdir(parents=True)
        (self.hub / "ai/project-registry.md").write_text(
            f"## demo\n\nStatus: active\nPath: {self.hub / 'projects/demo'}\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()


class ParseTests(Base):
    def test_claude_split_call_counted_once_with_largest_usage(self):
        path = self.root / "c.jsonl"
        partial = dict(U, output_tokens=1)
        write(path, [c_user("Привет"),
                     c_assistant("m1", [text("Смотрю")], usage=partial),
                     c_assistant("m1", [tool("t1", "Bash", {"command": "ls"})])], self.hub)
        s = self.mod.parse_claude(path, self.hub)
        self.assertEqual(len(s.steps), 1)
        step = s.steps[0]
        self.assertEqual((step.fresh, step.cached, step.output), (15, 100, 2))
        self.assertTrue(step.text)
        self.assertTrue(step.after_user)
        self.assertEqual([c.tool for c in step.calls], ["Bash"])
        self.assertTrue(s.usage_seen)
        self.assertEqual(s.first_user, "Привет")

    def test_claude_error_result_marks_call(self):
        path = self.root / "c.jsonl"
        write(path, [c_user("go"), c_assistant("m1", [tool("t1", "Bash", {"command": "ls"})]),
                     c_result("t1", error=True)], self.hub)
        s = self.mod.parse_claude(path, self.hub)
        self.assertTrue(s.steps[0].calls[0].error)

    def test_claude_without_usage_and_broken_lines(self):
        path = self.root / "c.jsonl"
        write(path, ["{not json", c_user("go"), c_assistant("m1", [text("ok")], usage=None),
                     {"type": "assistant", "sessionId": "c-1", "cwd": "HUB"}], self.hub)
        s = self.mod.parse_claude(path, self.hub)
        self.assertFalse(s.usage_seen)

    def test_claude_strips_reminders_from_first_user_text(self):
        path = self.root / "c.jsonl"
        write(path, [c_user("<system-reminder>x</system-reminder>[hub-session-scan] batch"),
                     c_assistant("m1", [text("ok")])], self.hub)
        s = self.mod.parse_claude(path, self.hub)
        self.assertTrue(s.first_user.startswith("[hub-session-scan]"))

    def test_codex_steps_tokens_errors_and_duplicate_events(self):
        path = self.root / "x.jsonl"
        write(path, [x_meta(), x_user("<environment_context>skip</environment_context>"),
                     x_user("Сделай"), x_call("k1", "text = await exec('ls')"),
                     x_tokens(100, 60, 5, 105), x_out("k1", "Exit code: 1\nboom"),
                     {"type": "event_msg", "payload": {"type": "token_count", "info": None}},
                     x_tokens(100, 60, 5, 105),
                     x_say("Готово"), x_tokens(200, 150, 7, 300)], self.hub)
        s = self.mod.parse_codex(path, self.hub)
        self.assertEqual(s.first_user, "Сделай")
        self.assertEqual(len(s.steps), 2)
        first, second = s.steps
        self.assertEqual((first.fresh, first.cached, first.output), (40, 60, 5))
        self.assertTrue(first.after_user)
        self.assertTrue(first.calls[0].error)
        self.assertTrue(second.text)
        self.assertFalse(second.after_user)

    def test_codex_zero_exit_code_is_not_error(self):
        path = self.root / "x.jsonl"
        write(path, [x_meta(), x_user("go"), x_call("k1", "exec('ls')"),
                     x_tokens(10, 0, 1, 11), x_out("k1", "Exit code: 0\nerror word")], self.hub)
        s = self.mod.parse_codex(path, self.hub)
        self.assertFalse(s.steps[0].calls[0].error)

    def test_labels_hide_arguments_and_outside_paths(self):
        hub = self.hub
        self.assertEqual(self.mod.label("Bash", "bash scripts/run.sh --token SECRET", hub),
                         "Bash bash scripts/run.sh")
        self.assertEqual(self.mod.label("Bash", f"python3 {hub}/scripts/x.py SECRET", hub),
                         "Bash python3 scripts/x.py")
        self.assertEqual(self.mod.label("Bash", "/usr/bin/env SECRET", hub), "Bash ?")
        self.assertEqual(self.mod.label("Bash", "bash /elsewhere/scripts/y.sh", hub), "Bash bash")
        self.assertEqual(self.mod.label("exec", "await exec('scripts/z.py SECRET')", hub),
                         "exec scripts/z.py")
        self.assertEqual(self.mod.label("Read", str(hub / "ai/rules/x.md"), hub),
                         "Read ai/rules/x.md")
        self.assertEqual(self.mod.label("Read", str(hub / "projects/demo/ai/current-task.md"), hub),
                         "Read projects/demo/ai/current-task.md")
        self.assertEqual(self.mod.label("Read", str(hub / "projects/demo/notes/SECRET.md"), hub),
                         "Read projects/demo/*")
        self.assertEqual(self.mod.label("Read", "/etc/SECRET", hub), "Read outside-hub")
        self.assertEqual(self.mod.label("Read", None, hub), "Read outside-hub")
        self.assertEqual(self.mod.label("Skill", {"skill": "SECRET"}, hub), "Skill")


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.mod = load()

    def step(self, *calls, text=False, after_user=False):
        return self.mod.Step(fresh=10, calls=list(calls), text=text, after_user=after_user)

    def bash(self, command, error=False):
        return self.mod.Call("Bash", f"Bash {command}", command=command, error=error)

    def read(self, path):
        return self.mod.Call("Read", f"Read {path}", path=path)

    def cats(self, steps):
        return [c for c, _ in self.mod.classify(steps)]

    def test_error_retry_until_same_tool_succeeds(self):
        steps = [self.step(self.bash("a", error=True)), self.step(self.read("/f")),
                 self.step(self.bash("b")), self.step(self.bash("c"))]
        result = self.mod.classify(steps)
        self.assertEqual([c for c, _ in result], [None, "error_retry", "error_retry", None])
        self.assertEqual(result[1][1], "Bash a")

    def test_user_message_ends_error_retry(self):
        steps = [self.step(self.bash("a", error=True)), self.step(self.read("/f"), after_user=True)]
        self.assertEqual(self.cats(steps), [None, None])

    def test_failed_retry_keeps_waiting(self):
        steps = [self.step(self.bash("a", error=True)), self.step(self.bash("b", error=True)),
                 self.step(self.read("/f"))]
        self.assertEqual(self.cats(steps), [None, "error_retry", "error_retry"])

    def test_repeat_command(self):
        steps = [self.step(self.bash("ls")), self.step(self.bash("ls"))]
        self.assertEqual(self.cats(steps), [None, "repeat_command"])

    def test_repeat_read_only_without_edit_between(self):
        edit = self.mod.Call("Edit", "Edit /f", path="/f")
        self.assertEqual(self.cats([self.step(self.read("/f")), self.step(self.read("/f"))]),
                         [None, "repeat_read"])
        self.assertEqual(self.cats([self.step(self.read("/f")), self.step(edit),
                                    self.step(self.read("/f"))]), [None, None, None])

    def test_error_retry_wins_over_repeat_command(self):
        steps = [self.step(self.bash("x", error=True)), self.step(self.bash("x"))]
        self.assertEqual(self.cats(steps), [None, "error_retry"])

    def test_startup_ends_at_first_text(self):
        steps = [self.step(), self.step(), self.step(text=True), self.step(text=True)]
        self.assertEqual(len(self.mod.startup(steps)), 3)
        self.assertEqual(len(self.mod.startup([self.step(), self.step()])), 2)
        self.assertEqual(self.mod.startup([]), [])


class WeekTests(Base):
    def setUp(self):
        super().setUp()
        self.claude = self.root / "claude"
        self.codex = self.root / "codex"
        slug = self.claude / "slug"
        hub_cwd = str(self.hub)
        write(slug / "c-1.jsonl", [
            c_user("PRIVATE-TEXT задача"),
            c_assistant("m1", [text("Проверяю"),
                               tool("t1", "Bash", {"command": "bash scripts/run.sh --token PRIVATE123"})]),
            c_result("t1", error=True),
            c_assistant("m2", [tool("t2", "Bash", {"command": "bash scripts/run.sh --token PRIVATE123"})]),
            c_result("t2"),
            c_assistant("m3", [tool("t3", "Read", {"file_path": "/etc/PRIVATE-PATH"})]),
            c_assistant("m4", [tool("t4", "Read", {"file_path": "/etc/PRIVATE-PATH"})]),
            c_assistant("m5", [text("Готово")]),
        ], self.hub)
        write(slug / "c-out.jsonl", [c_user("x", sid="c-out", cwd="/elsewhere"),
                                     c_assistant("m1", [text("y")], sid="c-out", cwd="/elsewhere")], self.hub)
        write(slug / "c-old.jsonl", [c_user("x", sid="c-old", ts="2026-10-07T23:00:00Z"),
                                     c_assistant("m1", [text("y")], sid="c-old")], self.hub)
        write(slug / "c-edge.jsonl", [c_user("x", sid="c-edge", ts="2026-10-08T00:10:00Z"),
                                      c_assistant("m1", [text("y")], sid="c-edge")], self.hub)
        write(slug / "c-scan.jsonl", [c_user("[hub-session-scan] batch", sid="c-scan"),
                                      c_assistant("m1", [text("y")], sid="c-scan")], self.hub)
        write(slug / "c-nousage.jsonl", [c_user("x", sid="c-nousage"),
                                         c_assistant("m1", [text("y")], usage=None, sid="c-nousage")],
              self.hub)
        write(slug / "c-nocwd.jsonl", [c_user("x", sid="c-nocwd", cwd=""),
                                       c_assistant("m1", [text("y")], sid="c-nocwd", cwd="")], self.hub)
        write(self.codex / "2026/10/12/rollout-x-1.jsonl", [
            x_meta(cwd=f"{hub_cwd}/projects/demo"), x_user("Сделай"), x_say("Ок"),
            x_tokens(100, 60, 5, 105)], self.hub)

    def run_week(self, until="2026-10-14", claude=None, codex=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.mod.main(["--hub", str(self.hub), "--claude-root", str(claude or self.claude),
                           "--codex-root", str(codex or self.codex), "week", "--until", until])
        return json.loads(out.getvalue()), out.getvalue()

    def test_week_report_counts_and_filters(self):
        data, _ = self.run_week()
        self.assertEqual(data["since"], "2026-10-08")
        self.assertEqual(data["sessions"], 3)  # c-1, c-edge, x-1
        self.assertEqual([s["session"] for s in data["skipped"]], ["c-nousage"])
        totals = data["totals"]
        self.assertEqual(totals["steps"], 7)
        self.assertEqual(totals["fresh"], 6 * 15 + 40)
        self.assertEqual(totals["cached"], 6 * 100 + 60)
        self.assertEqual(totals["loss_fresh"], 30)
        self.assertEqual(totals["loss_share"], round(30 / 130, 3))
        self.assertEqual(data["losses"]["error_retry"],
                         [{"label": "Bash bash scripts/run.sh", "steps": 1, "fresh": 15, "cached": 100}])
        self.assertEqual(data["losses"]["repeat_read"][0]["label"], "Read outside-hub")
        self.assertEqual(data["losses"]["repeat_command"], [])
        top = {s["session"]: s for s in data["startup"]["top"]}
        self.assertEqual(top["c-1"]["steps"], 1)
        self.assertEqual(top["x-1"]["project"], "demo")
        self.assertEqual(data["startup"]["median_fresh"], 15)

    def test_week_file_written_without_private_text(self):
        data, printed = self.run_week()
        year, week, _ = date(2026, 10, 14).isocalendar()
        path = self.hub / f"ai/learning/cost/{year}-W{week:02d}.json"
        self.assertEqual(data["week"], f"{year}-W{week:02d}")
        stored = path.read_text(encoding="utf-8")
        for blob in (stored, printed):
            self.assertNotIn("PRIVATE", blob)
            self.assertNotIn("задача", blob)

    def test_old_files_are_not_parsed(self):
        old = time.time() - 40 * 86400
        for path in self.claude.glob("*/*.jsonl"):
            os.utime(path, (old, old))
        data, _ = self.run_week()
        self.assertEqual(data["sessions"], 1)  # only x-1 keeps a fresh mtime

    def test_missing_transcript_folders(self):
        data, _ = self.run_week(claude=self.root / "none-c", codex=self.root / "none-x")
        self.assertEqual(data["sessions"], 0)
        self.assertEqual(data["note"], "no transcript folders")
        self.assertEqual(data["startup"]["median_fresh"], 0)

    def test_bad_until_date(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                self.run_week(until="14.10.2026")


if __name__ == "__main__":
    unittest.main()
