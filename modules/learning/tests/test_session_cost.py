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
        (self.hub / "scripts").mkdir()
        for name in ("run.sh", "x.py", "z.py"):
            (self.hub / "scripts" / name).write_text("", encoding="utf-8")
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
        self.assertEqual(self.mod.label("Bash", "ghp_SECRETTOKEN run", hub), "Bash ?")
        self.assertEqual(self.mod.label("Bash", "sk-live-abc123", hub), "Bash ?")
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

    def test_script_tail_only_when_script_exists_in_hub(self):
        self.assertEqual(self.mod.label("Bash", "python3 scripts/missing.py SECRET", self.hub),
                         "Bash python3")
        self.assertEqual(self.mod.label("exec", "await exec('scripts/missing.py')", self.hub),
                         "exec")

    def test_claude_null_tokens_do_not_crash(self):
        path = self.root / "c.jsonl"
        write(path, [c_user("go"),
                     c_assistant("m1", [text("ok")], usage=dict(U, output_tokens=None,
                                                                 input_tokens=None))], self.hub)
        s = self.mod.parse_claude(path, self.hub)
        self.assertEqual((s.steps[0].fresh, s.steps[0].output), (5, 0))

    def test_codex_null_fields_do_not_crash(self):
        path = self.root / "x.jsonl"
        record = x_tokens(None, None, None, 5)
        record["payload"]["info"]["last_token_usage"]["input_tokens"] = None
        part = {"type": "response_item", "payload": {"type": "message", "role": "user",
                "content": [{"type": "input_text", "text": None}, {"type": "input_text", "text": "go"}]}}
        write(path, [x_meta(), part, record], self.hub)
        s = self.mod.parse_codex(path, self.hub)
        self.assertEqual((s.steps[0].fresh, s.steps[0].output), (0, 0))
        self.assertEqual(s.first_user, "go")

    def test_claude_cwd_taken_from_later_record(self):
        path = self.root / "c.jsonl"
        write(path, [c_user("go", cwd=""), c_assistant("m1", [text("ok")], cwd=""),
                     c_assistant("m2", [text("ok")], cwd="HUB/projects/demo")], self.hub)
        s = self.mod.parse_claude(path, self.hub)
        self.assertEqual(s.cwd, f"{self.hub}/projects/demo")

    def test_claude_message_id_shared_between_files_counted_once(self):
        seen = set()
        a, b = self.root / "a.jsonl", self.root / "b.jsonl"
        write(a, [c_user("go", sid="s-a"), c_assistant("d1", [text("ok")], sid="s-a")], self.hub)
        write(b, [c_user("go", sid="s-b"), c_assistant("d1", [text("ok")], sid="s-b"),
                  c_assistant("d1", [text("more")], sid="s-b"),
                  c_assistant("d2", [text("ok")], sid="s-b")], self.hub)
        first = self.mod.parse_claude(a, self.hub, seen)
        second = self.mod.parse_claude(b, self.hub, seen)
        self.assertEqual(len(first.steps), 1)
        self.assertEqual(len(second.steps), 1)


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.mod = load()

    def step(self, *calls, text=False, after_user=False):
        return self.mod.Step(fresh=10, calls=list(calls), text=text, after_user=after_user)

    def bash(self, command, error=False):
        return self.mod.Call("Bash", f"Bash {command}", command=command, error=error)

    def read(self, path, offset=None, limit=None):
        return self.mod.Call("Read", f"Read {path}", path=path, read_key=(path, offset, limit))

    def call(self, tool, label_):
        return self.mod.Call(tool, label_)

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

    def test_repeat_read_depends_on_paging(self):
        paged = [self.step(self.read("/f", 0, 100)), self.step(self.read("/f", 100, 100))]
        self.assertEqual(self.cats(paged), [None, None])
        same = [self.step(self.read("/f", 0, 100)), self.step(self.read("/f", 0, 100))]
        self.assertEqual(self.cats(same), [None, "repeat_read"])

    def test_startup_stops_after_first_reply(self):
        skill = self.call("Skill", "Skill")
        read = self.call("Read", "Read ai/x")
        steps = [self.step(skill), self.step(read), self.step(text=True), self.step(text=True)]
        self.assertEqual(len(self.mod.startup(steps)), 3)

    def test_startup_stops_before_non_loading_call(self):
        steps = [self.step(self.call("Skill", "Skill")), self.step(self.bash("ls")),
                 self.step(text=True)]
        self.assertEqual(len(self.mod.startup(steps)), 1)

    def test_startup_first_reply_only(self):
        self.assertEqual(len(self.mod.startup([self.step(text=True), self.step(text=True)])), 1)

    def test_startup_text_with_loading_call_continues(self):
        steps = [self.step(self.call("Skill", "Skill"), text=True), self.step(text=True),
                 self.step(text=True)]
        self.assertEqual(len(self.mod.startup(steps)), 2)

    def test_startup_loading_kinds(self):
        script = self.mod.Call("Bash", f"Bash bash {self.mod.STARTUP_SCRIPT}", command="x")
        steps = [self.step(self.call("ToolSearch", "ToolSearch")),
                 self.step(self.call("Read", "Read CLAUDE.md")),
                 self.step(self.call("Read", "Read .claude/x.md")), self.step(script),
                 self.step(self.call("Read", "Read projects/demo/ai/x.md"))]
        self.assertEqual(len(self.mod.startup(steps)), 4)

    def test_startup_empty(self):
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
                                     c_assistant("o1", [text("y")], sid="c-out", cwd="/elsewhere")], self.hub)
        write(slug / "c-old.jsonl", [c_user("x", sid="c-old", ts="2026-10-07T23:00:00Z"),
                                     c_assistant("old1", [text("y")], sid="c-old")], self.hub)
        write(slug / "c-edge.jsonl", [c_user("x", sid="c-edge", ts="2026-10-08T00:10:00Z"),
                                      c_assistant("e1", [text("y")], sid="c-edge")], self.hub)
        write(slug / "c-scan.jsonl", [c_user("[hub-session-scan] batch", sid="c-scan"),
                                      c_assistant("s1", [text("y")], sid="c-scan")], self.hub)
        write(slug / "c-nousage.jsonl", [c_user("x", sid="c-nousage"),
                                         c_assistant("n1", [text("y")], usage=None, sid="c-nousage")],
              self.hub)
        write(slug / "c-nocwd.jsonl", [c_user("x", sid="c-nocwd", cwd=""),
                                       c_assistant("w1", [text("y")], sid="c-nocwd", cwd="")], self.hub)
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
        self.assertEqual((top["c-1"]["steps"], top["c-1"]["fresh"]), (0, 0))
        self.assertEqual((top["x-1"]["steps"], top["x-1"]["fresh"]), (1, 40))
        self.assertEqual((top["c-edge"]["steps"], top["c-edge"]["fresh"]), (1, 15))
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
