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
CATEGORIES = ("error_retry", "repeat_command", "repeat_read")


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
                output=last.get("output_tokens", 0),
                calls=pending, text=said, after_user=user_waiting))
            pending, said, user_waiting = [], False, False
    return session if session and session.id else None


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
