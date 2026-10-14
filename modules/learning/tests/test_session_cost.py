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
        self.assertEqual((first.fresh, first.cached, first.output), (40, 60, 6))
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


if __name__ == "__main__":
    unittest.main()
