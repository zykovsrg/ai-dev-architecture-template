# Session Cost Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A model-free script that counts token losses (error retries, repeated commands, repeated reads) and startup cost in Hub sessions for one week, shown at the weekly review.

**Architecture:** New `modules/learning/scripts/session_cost.py` reuses discovery helpers from `session_collect.py`, parses Claude Code and Codex transcripts into model-call steps with token numbers, classifies each step, and writes a numbers-only JSON to `ai/learning/cost/<YYYY>-W<ww>.json`. The weekly review resource runs it and asks the agent for three ranked conclusions. Rule text and module passport gain the new script.

**Tech Stack:** Python 3 standard library only; `unittest` (run with `python3 -m unittest`).

**Spec:** `docs/superpowers/specs/2026-10-14-session-cost-diagnostics-design.md`

## Global Constraints

- Read-only over `~/.claude/projects/*/*.jsonl` and `~/.codex/sessions/**/*.jsonl`; only sessions whose working directory is inside the Hub.
- Output holds only numbers, session IDs, project IDs, dates and labels. Never command arguments, file contents, message text or paths outside the Hub.
- Labels for paths inside `projects/<id>/` keep the full path only under `projects/<id>/ai/`; anything else there becomes `projects/<id>/*` (narrows the spec's "Hub-relative path" so project file names never leak).
- `cached` tokens are never summed into `fresh`.
- Each step falls into at most one loss category, in order: `error_retry`, `repeat_command`, `repeat_read`.
- Sessions started by the scanner (first user text starts with `[hub-session-scan]`) are ignored.
- A session with no usage numbers is listed in `skipped`, never counted as zero.
- No new dependencies. Work in this repository on `main`, as earlier tasks did.
- Every commit message ends with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- Codex emits `token_count` events with no `info` (rate-limit only) or repeating the previous `total_token_usage` → no extra step, no double count (Task 1 test).
- Claude writes one model call as several records whose `usage` may differ while streaming → one step with the largest value per field (Task 1 test).
- Weekly run over 1,000+ old transcript files → files last modified before the window are not parsed (Task 3 test).
- Broken JSON lines, empty `cwd`, missing `message` → the session is skipped or parsed partly, never a crash (Task 1 and Task 3 tests).
- A command that names the Hub by absolute path or a script inside a project → label stays Hub-relative or omits the script; no outside path appears (Task 1 label test).

---

### Task 1: Parse transcripts into steps with labels

**Files:**
- Create: `modules/learning/scripts/session_cost.py`
- Test: `modules/learning/tests/test_session_cost.py`

**Interfaces:**
- Consumes: from `session_collect.py`: `_lines(path)`, `REMINDER` (regex), and later `_files`, `_inside`, `project_for`, `save_json`.
- Produces:
  - `Call(tool: str, label: str, command: str | None = None, path: str | None = None, error: bool = False)`
  - `Step(fresh: int = 0, cached: int = 0, output: int = 0, calls: list[Call] = [], text: bool = False, after_user: bool = False)`
  - `CostSession(tool: str, id: str, cwd: str, started: str, first_user: str = "", steps: list[Step] = [], usage_seen: bool = False)`
  - `label(tool: str, value, hub: Path) -> str`
  - `parse_claude(path: Path, hub: Path) -> CostSession | None`
  - `parse_codex(path: Path, hub: Path) -> CostSession | None`
  - constants `SHELL = {"Bash", "exec"}`, `READ = {"Read"}`, `EDIT = {"Edit", "Write", "MultiEdit", "NotebookEdit"}`

- [ ] **Step 1: Write the failing tests**

Create `modules/learning/tests/test_session_cost.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest modules/learning/tests/test_session_cost.py -v`
Expected: ERROR, `FileNotFoundError` / no such file `session_cost.py`.

- [ ] **Step 3: Write the implementation**

Create `modules/learning/scripts/session_cost.py`:

```python
#!/usr/bin/env python3
"""Count token losses and startup cost in Hub sessions for the weekly review.

Read-only over transcript folders (same exception as session_collect.py).
Writes only ai/learning/cost/<YYYY>-W<ww>.json: numbers, session and project
IDs, dates and short labels. Never stores command arguments, file contents,
message text or paths outside the Hub.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from session_collect import REMINDER, _lines  # noqa: E402

SHELL = {"Bash", "exec"}
READ = {"Read"}
EDIT = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
EXIT_CODE = re.compile(r"(?:exit_code|Exit code|exited with code)\D{0,5}(\d+)")
HUB_SCRIPT = re.compile(r"(?<![\w/.])\.?/?(scripts/[\w.-]+\.(?:py|sh))")
PROGRAM = re.compile(r"[A-Za-z0-9_.-]+")


@dataclass
class Call:
    tool: str
    label: str
    command: str | None = None  # compared only for equality, never stored
    path: str | None = None
    error: bool = False


@dataclass
class Step:
    fresh: int = 0
    cached: int = 0
    output: int = 0
    calls: list = field(default_factory=list)
    text: bool = False
    after_user: bool = False


@dataclass
class CostSession:
    tool: str
    id: str
    cwd: str
    started: str
    first_user: str = ""
    steps: list = field(default_factory=list)
    usage_seen: bool = False


def _hub_rel(value, hub):
    if not isinstance(value, str) or not value:
        return "outside-hub"
    try:
        parts = Path(os.path.realpath(value)).relative_to(hub).parts
    except ValueError:
        return "outside-hub"
    if len(parts) >= 2 and parts[0] == "projects" and (len(parts) < 3 or parts[2] != "ai"):
        return f"projects/{parts[1]}/*"
    return "/".join(parts) or "."


def label(tool, value, hub):
    hub = Path(hub)
    if tool in SHELL:
        command = value if isinstance(value, str) else ""
        command = command.replace(f"{hub}/", "")
        script = HUB_SCRIPT.search(command)
        tail = f" {script.group(1)}" if script else ""
        if tool == "Bash":
            words = command.split()
            program = words[0] if words and PROGRAM.fullmatch(words[0]) else "?"
            return f"Bash {program}{tail}"
        return f"exec{tail}"
    if tool in READ or tool in EDIT:
        return f"{tool} {_hub_rel(value, hub)}"
    return tool


def _call(tool, value, hub):
    if tool in SHELL:
        command = value.get("command") if isinstance(value, dict) else value
        if not isinstance(command, str):
            command = json.dumps(command, sort_keys=True, ensure_ascii=False)
        return Call(tool, label(tool, command, hub), command=command)
    if tool in READ or tool in EDIT:
        path = None
        if isinstance(value, dict):
            path = value.get("file_path") or value.get("notebook_path")
        return Call(tool, label(tool, path, hub), path=path)
    return Call(tool, label(tool, value, hub))


def parse_claude(path, hub):
    session, steps_by_id, calls, user_waiting = None, {}, {}, False
    for rec in _lines(path):
        if rec.get("type") not in ("user", "assistant") or rec.get("isSidechain") or rec.get("isMeta"):
            continue
        if session is None:
            if not rec.get("sessionId"):
                continue
            session = CostSession("claude", rec["sessionId"], rec.get("cwd") or "",
                                  rec.get("timestamp") or "")
        message = rec.get("message") or {}
        content = message.get("content")
        if rec["type"] == "user":
            items = [{"type": "text", "text": content}] if isinstance(content, str) else (content or [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text":
                    clean = REMINDER.sub("", item.get("text") or "").strip()
                    if clean:
                        session.first_user = session.first_user or clean
                        user_waiting = True
                elif item.get("type") == "tool_result" and item.get("is_error"):
                    call = calls.get(item.get("tool_use_id"))
                    if call:
                        call.error = True
            continue
        key = message.get("id") or rec.get("uuid") or f"line-{len(steps_by_id)}"
        step = steps_by_id.get(key)
        if step is None:
            step = Step(after_user=user_waiting)
            user_waiting = False
            steps_by_id[key] = step
            session.steps.append(step)
        usage = message.get("usage")
        if isinstance(usage, dict):
            session.usage_seen = True
            fresh = usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
            step.fresh = max(step.fresh, fresh)
            step.cached = max(step.cached, usage.get("cache_read_input_tokens", 0))
            step.output = max(step.output, usage.get("output_tokens", 0))
        for item in content if isinstance(content, list) else []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and (item.get("text") or "").strip():
                step.text = True
            elif item.get("type") == "tool_use":
                call = _call(item.get("name", "tool"), item.get("input") or {}, hub)
                calls[item.get("id")] = call
                step.calls.append(call)
    return session


def parse_codex(path, hub):
    session, calls, pending, said, user_waiting, last_total = None, {}, [], False, False, None
    for rec in _lines(path):
        payload = rec.get("payload") or {}
        if rec.get("type") == "session_meta":
            session = CostSession("codex", payload.get("id") or "", payload.get("cwd") or "",
                                  payload.get("timestamp") or "")
            continue
        if session is None:
            continue
        kind = payload.get("type")
        if rec.get("type") == "response_item":
            if kind == "message" and payload.get("role") in ("user", "assistant"):
                body = " ".join(part.get("text", "") for part in payload.get("content") or []
                                if isinstance(part, dict)).strip()
                if not body:
                    continue
                if payload["role"] == "assistant":
                    said = True
                elif not body.startswith("<") and not body.startswith("# AGENTS.md"):
                    session.first_user = session.first_user or body
                    user_waiting = True
            elif kind in ("custom_tool_call", "function_call"):
                value = payload.get("input")
                call = _call(payload.get("name", "tool"),
                             value if value is not None else payload.get("arguments"), hub)
                calls[payload.get("call_id")] = call
                pending.append(call)
            elif kind in ("custom_tool_call_output", "function_call_output"):
                output = payload.get("output")
                output = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
                code = EXIT_CODE.search(output or "")
                call = calls.get(payload.get("call_id"))
                if call and code and code.group(1) != "0":
                    call.error = True
        elif rec.get("type") == "event_msg" and kind == "token_count":
            info = payload.get("info") or {}
            last = info.get("last_token_usage")
            total = (info.get("total_token_usage") or {}).get("total_tokens")
            if not last or (total is not None and total == last_total):
                continue
            last_total = total
            session.usage_seen = True
            inp, cached = last.get("input_tokens", 0), last.get("cached_input_tokens", 0)
            session.steps.append(Step(
                fresh=max(inp - cached, 0), cached=cached,
                output=last.get("output_tokens", 0) + last.get("reasoning_output_tokens", 0),
                calls=pending, text=said, after_user=user_waiting))
            pending, said, user_waiting = [], False, False
    return session if session and session.id else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest modules/learning/tests/test_session_cost.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add modules/learning/scripts/session_cost.py modules/learning/tests/test_session_cost.py
git commit -m "Parse transcripts into token steps for session cost diagnostics"
```

---

### Task 2: Classify losses and startup

**Files:**
- Modify: `modules/learning/scripts/session_cost.py` (append functions after `parse_codex`)
- Test: `modules/learning/tests/test_session_cost.py` (add class before `if __name__`)

**Interfaces:**
- Consumes: `Call`, `Step`, `READ`, `EDIT` from Task 1.
- Produces:
  - `CATEGORIES = ("error_retry", "repeat_command", "repeat_read")`
  - `classify(steps: list[Step]) -> list[tuple[str | None, str | None]]` — `(category, label)` per step
  - `startup(steps: list[Step]) -> list[Step]`

- [ ] **Step 1: Write the failing tests**

Add to `modules/learning/tests/test_session_cost.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest modules/learning/tests/test_session_cost.py -v`
Expected: `ClassifyTests` fail with `AttributeError: module 'session_cost' has no attribute 'classify'`.

- [ ] **Step 3: Write the implementation**

Add `CATEGORIES` next to the other constants and these functions after `parse_codex` in `session_cost.py`:

```python
CATEGORIES = ("error_retry", "repeat_command", "repeat_read")
```

```python
def classify(steps):
    """Return (category, label) per step; at most one category per step."""
    result, waiting, commands, reads = [], {}, set(), set()
    for step in steps:
        if step.after_user:
            waiting.clear()
        category = label_ = None
        if waiting:
            category, label_ = "error_retry", next(iter(waiting.values()))
        for call in step.calls:
            if call.tool in waiting and not call.error:
                waiting.pop(call.tool)
            if call.command is not None:
                if call.command in commands and category is None:
                    category, label_ = "repeat_command", call.label
                commands.add(call.command)
            if call.tool in READ and call.path:
                if call.path in reads and category is None:
                    category, label_ = "repeat_read", call.label
                reads.add(call.path)
            elif call.tool in EDIT and call.path:
                reads.discard(call.path)
        for call in step.calls:
            if call.error:
                waiting[call.tool] = call.label
        result.append((category, label_))
    return result


def startup(steps):
    """Steps from the session start up to the first assistant text, inclusive."""
    out = []
    for step in steps:
        out.append(step)
        if step.text:
            break
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest modules/learning/tests/test_session_cost.py -v`
Expected: all 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add modules/learning/scripts/session_cost.py modules/learning/tests/test_session_cost.py
git commit -m "Classify loss steps and startup in session cost diagnostics"
```

---

### Task 3: Weekly report and command line

**Files:**
- Modify: `modules/learning/scripts/session_cost.py` (imports, new functions, `main`)
- Test: `modules/learning/tests/test_session_cost.py` (add class)

**Interfaces:**
- Consumes: Tasks 1–2; from `session_collect.py`: `_files(claude_root, codex_root)`, `_inside(child, parent)`, `project_for(cwd, hub)`, `save_json(path, data)`.
- Produces:
  - `collect(hub: Path, until: date, claude_root: Path, codex_root: Path) -> tuple[list[CostSession], list[dict]]`
  - `report(hub: Path, until: date, sessions, skipped) -> dict` with keys `week, since, until, sessions, totals, losses, startup, skipped`
  - `main(argv=None)`; command `python3 scripts/session_cost.py --hub <hub> week --until <YYYY-MM-DD>`; writes `<hub>/ai/learning/cost/<week>.json`

- [ ] **Step 1: Write the failing tests**

Add to `modules/learning/tests/test_session_cost.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest modules/learning/tests/test_session_cost.py -v`
Expected: `WeekTests` fail with `AttributeError: module 'session_cost' has no attribute 'main'`.

- [ ] **Step 3: Write the implementation**

In `session_cost.py` change the imports block to:

```python
import argparse
import json
import os
import re
import statistics
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from session_collect import REMINDER, _files, _inside, _lines, project_for, save_json  # noqa: E402
```

Add the constants next to the others:

```python
COST_DIR = "ai/learning/cost"
SCAN_MARK = "[hub-session-scan]"
```

Append after `startup`:

```python
def collect(hub, until, claude_root, codex_root):
    since = until - timedelta(days=6)
    # A file last written before the window cannot hold a session started in it
    oldest = datetime.combine(since - timedelta(days=1), dtime.min, timezone.utc).timestamp()
    sessions, skipped = [], []
    if not Path(claude_root).exists() and not Path(codex_root).exists():
        return sessions, skipped
    for tool, path in _files(claude_root, codex_root):
        if path.stat().st_mtime < oldest:
            continue
        session = parse_claude(path, hub) if tool == "claude" else parse_codex(path, hub)
        if session is None or not session.cwd or not _inside(session.cwd, hub):
            continue
        if not since.isoformat() <= session.started[:10] <= until.isoformat():
            continue
        if session.first_user.startswith(SCAN_MARK):
            continue
        if not session.usage_seen:
            skipped.append({"session": session.id, "tool": session.tool, "reason": "no usage data"})
            continue
        sessions.append(session)
    return sessions, skipped


def report(hub, until, sessions, skipped):
    totals = {"steps": 0, "fresh": 0, "cached": 0, "output": 0, "loss_fresh": 0}
    groups = {category: {} for category in CATEGORIES}
    starts = []
    for session in sessions:
        for step, (category, label_) in zip(session.steps, classify(session.steps)):
            totals["steps"] += 1
            totals["fresh"] += step.fresh
            totals["cached"] += step.cached
            totals["output"] += step.output
            if category:
                group = groups[category].setdefault(
                    label_, {"label": label_, "steps": 0, "fresh": 0, "cached": 0})
                group["steps"] += 1
                group["fresh"] += step.fresh
                group["cached"] += step.cached
                totals["loss_fresh"] += step.fresh
        first = startup(session.steps)
        starts.append({"session": session.id, "tool": session.tool,
                       "project": project_for(session.cwd, hub), "date": session.started[:10],
                       "steps": len(first), "fresh": sum(s.fresh for s in first),
                       "cached": sum(s.cached for s in first)})
    totals["loss_share"] = round(totals["loss_fresh"] / totals["fresh"], 3) if totals["fresh"] else 0.0
    year, week, _ = until.isocalendar()
    return {
        "week": f"{year}-W{week:02d}",
        "since": (until - timedelta(days=6)).isoformat(),
        "until": until.isoformat(),
        "sessions": len(sessions),
        "totals": totals,
        "losses": {category: sorted(groups[category].values(),
                                    key=lambda g: (-g["fresh"], g["label"]))[:10]
                   for category in CATEGORIES},
        "startup": {"median_fresh": int(statistics.median([s["fresh"] for s in starts])) if starts else 0,
                    "top": sorted(starts, key=lambda s: (-s["fresh"], s["session"]))[:5]},
        "skipped": skipped,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", required=True, type=Path)
    parser.add_argument("--claude-root", type=Path, default=Path.home() / ".claude/projects")
    parser.add_argument("--codex-root", type=Path, default=Path.home() / ".codex/sessions")
    sub = parser.add_subparsers(dest="cmd", required=True)
    week = sub.add_parser("week")
    week.add_argument("--until", required=True)
    args = parser.parse_args(argv)
    hub = args.hub.resolve()
    try:
        until = date.fromisoformat(args.until)
    except ValueError:
        parser.error("--until must be YYYY-MM-DD")
    sessions, skipped = collect(hub, until, args.claude_root, args.codex_root)
    data = report(hub, until, sessions, skipped)
    if not args.claude_root.exists() and not args.codex_root.exists():
        data["note"] = "no transcript folders"
    save_json(hub / COST_DIR / f"{data['week']}.json", data)
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

Note: `c-old` starts `2026-10-07T23:00:00Z` and is excluded; `c-edge` starts `2026-10-08T00:10:00Z` and is included. Dates compare on the transcript's UTC date prefix.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest modules/learning/tests/test_session_cost.py -v`
Expected: all 19 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add modules/learning/scripts/session_cost.py modules/learning/tests/test_session_cost.py
git commit -m "Add weekly session cost report and command line"
```

---

### Task 4: Wire into module, rules and weekly review

**Files:**
- Modify: `modules/learning/module.md` (Installs, Writes)
- Modify: `modules/learning/rules.md` (`## Session learning` end)
- Modify: `modules/core/data/ai/architecture.md:61-72` (`### Transcript read exception`)
- Modify: `modules/planning/skills/hub-workflows/resources/weekly-review.md` (after the mechanism review paragraph, before the rule-home paragraph)
- Modify: `tests/test_optional_modules_switch.py:37` (expected learning files)

**Interfaces:**
- Consumes: command from Task 3.
- Produces: installed path `scripts/session_cost.py`; weekly-review section `## Технические потери`.

- [ ] **Step 1: Update the failing switch test first**

In `tests/test_optional_modules_switch.py`, after the line `"scripts/session_scan_model.py",` add:

```python
        "scripts/session_cost.py",
```

Run: `python3 -m unittest tests/test_optional_modules_switch.py -v`
Expected: FAIL — `scripts/session_cost.py` is not installed by the learning module.

- [ ] **Step 2: Module passport**

In `modules/learning/module.md`, after `- modules/learning/scripts/session_scan_model.py -> scripts/session_scan_model.py` add:

```markdown
- modules/learning/scripts/session_cost.py -> scripts/session_cost.py
```

Under `## Writes` add:

```markdown
- weekly session cost numbers in `ai/learning/cost/`
```

- [ ] **Step 3: Architecture rule**

In `modules/core/data/ai/architecture.md`, in `### Transcript read exception (learning module)`, replace the last sentence `This is the only exception to the allowed-root rule.` with:

```markdown
`scripts/session_cost.py` may read the same transcripts under the same
limits for the weekly review; it stores only numbers, session and project
IDs, dates and short labels in `ai/learning/cost/`, never command arguments,
message text or paths outside the Hub. This is the only exception to the
allowed-root rule.
```

- [ ] **Step 4: Learning rules**

At the end of `## Session learning` in `modules/learning/rules.md` add:

```markdown
`scripts/session_cost.py` counts, without a model, token losses (steps after
a tool error, repeated commands, repeated reads) and startup cost (steps up
to the first reply to the user) for one week; the weekly review shows them.
Nothing is fixed automatically.
```

- [ ] **Step 5: Weekly review**

In `modules/planning/skills/hub-workflows/resources/weekly-review.md`, insert before the paragraph starting `In the same review run the rule-home check`:

```markdown
Only when `learning` is listed in `ai/modules.md`, run
`python3 scripts/session_cost.py --hub <hub> week --until <date>` and show
`## Технические потери` in plain Russian: one line with sessions, fresh and
cached tokens and the loss share; the top 5 labels of each loss category
(`error_retry` «шаги после ошибки», `repeat_command` «повтор команды»,
`repeat_read` «повторное чтение файла») with steps and fresh tokens; the
startup median and the top 3 sessions. Then exactly three ranked conclusions
`- <что чинить> — почему: <цифры> — экономия: <оценка>`, largest saving first;
estimate the saving only from these numbers and say when it is a guess. With
no sessions or no usage data write one line saying so. A fix the user accepts
goes to `## Нужны решения` and follows the Superpowers flow of mechanism
candidates; nothing is fixed without the user's yes.
```

- [ ] **Step 6: Run the whole suite**

Run each and expect all PASS:

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s modules/learning/tests -v
python3 -m unittest discover -s modules/planning/tests -v
python3 -m unittest discover -s modules/obsidian/tests -v
```

Then check line limits of touched rule files (each must stay within 300 lines):

```bash
wc -l modules/learning/rules.md modules/core/data/ai/architecture.md modules/planning/skills/hub-workflows/resources/weekly-review.md
```

If any test outside the learning tests fails, read the failure: a passport or manifest consistency test may list module files and need `scripts/session_cost.py` added the same way as Step 1.

- [ ] **Step 7: Commit**

```bash
git add modules/learning/module.md modules/learning/rules.md modules/core/data/ai/architecture.md modules/planning/skills/hub-workflows/resources/weekly-review.md tests/test_optional_modules_switch.py
git commit -m "Wire session cost diagnostics into learning module and weekly review"
```

---

### Task 5: Deploy to the Hub and run on the real week

**Files:**
- No source changes. Hub copy changes through the installer.

**Interfaces:**
- Consumes: `scripts/update-installed-hub.sh` of this repository; the Hub at `/Users/zykovsrg/Documents/vibecode/_ai-hub`.

- [ ] **Step 1: Dry run**

```bash
scripts/update-installed-hub.sh --dry-run --hub /Users/zykovsrg/Documents/vibecode/_ai-hub --source .
```

Expected: a plan listing `scripts/session_cost.py`, `ai/rules/learning.md`, `ai/architecture.md` and the weekly-review resource, plus the plan and source SHAs. If it refuses because the Hub working tree has uncommitted changes, stop and ask the user; never pass `--allow-dirty` on your own.

- [ ] **Step 2: Apply with the printed SHAs**

```bash
scripts/update-installed-hub.sh --apply --confirm-plan <plan-sha-from-dry-run> --confirm-source-sha <source-sha-from-dry-run> --hub /Users/zykovsrg/Documents/vibecode/_ai-hub --source . --commit
```

Expected: success; the Hub has `scripts/session_cost.py`.

- [ ] **Step 3: Run on the real previous week**

```bash
python3 /Users/zykovsrg/Documents/vibecode/_ai-hub/scripts/session_cost.py --hub /Users/zykovsrg/Documents/vibecode/_ai-hub week --until 2026-10-13
```

Expected: JSON with `sessions` > 0 and both tools present, and a file `ai/learning/cost/2026-W42.json` in the Hub. Check by eye that no argument, message text or outside path appears in it. Report to the user in plain Russian: sessions, loss share, the largest loss label and the startup median.

- [ ] **Step 4: Record and close**

Append a short entry to `ai/changelog.md` of this project (what changed, verification, limitation: subagent transcripts are not counted). Then close the task through `hub-task-finish`.
