#!/usr/bin/env python3
"""Find new Hub sessions in Claude Code and Codex transcripts and normalize them.

Read-only over transcript folders. Writes only ai/learning/scan-ledger.json and
the batch file named on the command line.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

LEDGER = "ai/learning/scan-ledger.json"
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
LINE_LIMIT = 500


@dataclass
class Session:
    tool: str
    id: str
    cwd: str
    started: str
    path: Path
    turns: list = field(default_factory=list)


def _lines(path):
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            try:
                yield json.loads(raw)
            except ValueError:
                continue


def _short(value, limit=200):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


def parse_claude(path):
    sid = cwd = started = None
    turns, names = [], {}
    for rec in _lines(path):
        if rec.get("type") not in ("user", "assistant") or rec.get("isSidechain") or rec.get("isMeta"):
            continue
        sid = sid or rec.get("sessionId")
        cwd = cwd or rec.get("cwd")
        started = started or rec.get("timestamp")
        content = (rec.get("message") or {}).get("content")
        if isinstance(content, str):
            text = REMINDER.sub("", content).strip()
            if text and rec["type"] == "user":
                turns.append(("user", text))
            continue
        for item in content or []:
            kind = item.get("type")
            if kind == "text" and item.get("text", "").strip():
                role = "assistant" if rec["type"] == "assistant" else "user"
                turns.append((role, REMINDER.sub("", item["text"]).strip()))
            elif kind == "tool_use":
                names[item.get("id")] = item.get("name", "tool")
                turns.append(("tool", f"{item.get('name')}: {_short(item.get('input'))}"))
            elif kind == "tool_result" and item.get("is_error"):
                body = item.get("content")
                if isinstance(body, list):
                    body = " ".join(part.get("text", "") for part in body if isinstance(part, dict))
                turns.append(("error", f"{names.get(item.get('tool_use_id'), 'tool')}: {_short(body)}"))
    if not sid:
        return None
    return Session("claude", sid, cwd or "", started or "", Path(path), turns)


def parse_codex(path):
    meta, turns, last_tool = None, [], "tool"
    for rec in _lines(path):
        payload = rec.get("payload") or {}
        if rec.get("type") == "session_meta":
            meta = payload
            continue
        if rec.get("type") != "response_item":
            continue
        kind = payload.get("type")
        if kind == "message" and payload.get("role") in ("user", "assistant"):
            text = " ".join(part.get("text", "") for part in payload.get("content") or []).strip()
            if text and not text.startswith("<") and not text.startswith("# AGENTS.md"):
                turns.append((payload["role"], text))
        elif kind in ("custom_tool_call", "function_call"):
            last_tool = payload.get("name", "tool")
            turns.append(("tool", f"{last_tool}: {_short(payload.get('input') or payload.get('arguments'))}"))
        elif kind in ("custom_tool_call_output", "function_call_output"):
            output = payload.get("output")
            output = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
            if "error" in output.lower():
                turns.append(("error", f"{last_tool}: {_short(output)}"))
    if not meta or not meta.get("id"):
        return None
    return Session("codex", meta["id"], meta.get("cwd", ""), meta.get("timestamp", ""), Path(path), turns)


def normalize(session, limit=40000):
    lines = [f"{role.upper()}: {text[:LINE_LIMIT]}" for role, text in session.turns]
    text = "\n".join(lines)
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + "\n[cut]\n" + text[-half:]


def registry(hub):
    projects, current = {}, {}
    for line in (hub / "ai/project-registry.md").read_text(encoding="utf-8").splitlines() + ["## "]:
        if line.startswith("## "):
            if current.get("path"):
                projects[current["id"]] = current
            current = {"id": line[3:].strip()}
        elif line.startswith("Status: "):
            current["status"] = line[8:].strip()
        elif line.startswith("Path: "):
            current["path"] = line[6:].strip()
    return projects


def _inside(child, parent):
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def project_for(cwd, hub):
    best = None
    for pid, entry in registry(hub).items():
        if _inside(cwd, entry["path"]) and (best is None or len(entry["path"]) > len(best[1])):
            best = (pid, entry["path"])
    return best[0] if best else "hub"


def empty_ledger():
    return {"format": 1, "cutover": None, "last_scan": None, "last_weekly_review": None,
            "processed": {"claude": [], "codex": []},
            "sources": {"observations_lines": 0, "session_reviews": []}}


def load_ledger(hub):
    path = hub / LEDGER
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else empty_ledger()


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def mark_processed(ledger, tool, ids, now):
    done = ledger["processed"].setdefault(tool, [])
    done.extend(i for i in ids if i not in done)
    ledger["last_scan"] = now


def _files(claude_root, codex_root):
    for path in sorted(Path(claude_root).glob("*/*.jsonl")):
        yield "claude", path
    for path in sorted(Path(codex_root).glob("**/*.jsonl")):
        yield "codex", path


def pending(hub, ledger, now, claude_root, codex_root, active_minutes=15):
    if not ledger.get("cutover"):
        return []
    cutover = ledger["cutover"]
    fresh = now - timedelta(minutes=active_minutes)
    out = []
    for tool, path in _files(claude_root, codex_root):
        if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) > fresh:
            continue
        session = parse_claude(path) if tool == "claude" else parse_codex(path)
        if (session is None or session.id in ledger["processed"].get(tool, [])
                or session.started[:10] < cutover or not _inside(session.cwd, hub)):
            continue
        # Skip sessions started by the learning scanner itself
        if session.turns and session.turns[0][0] == "user" and session.turns[0][1].startswith("[hub-session-scan]"):
            continue
        out.append(session)
    return out


def extra_sources(hub, ledger):
    """New workflow observations and session-review findings as pseudo-sessions."""
    cutover = ledger.get("cutover")
    if not cutover:
        return []
    out, done = [], set(ledger["processed"].get("claude", []))
    journal = hub / "ai/workflow-observations.md"
    if journal.exists():
        entries = [l for l in journal.read_text(encoding="utf-8").splitlines() if re.match(r"^- \d{4}-\d{2}-\d{2} \|", l)]
        for number, line in enumerate(entries, 1):
            sid = f"obs-{number}"
            if sid not in done and line[2:12] >= cutover:
                out.append(Session("claude", sid, str(hub), line[2:12], journal, [("user", line[2:])]))
    for pid, entry in registry(hub).items():
        if entry.get("status") != "active":
            continue
        for review in sorted(Path(entry["path"], "ai/session-reviews").glob("*.md")):
            sid = f"review-{pid}-{review.stem}"
            if sid in done or review.stem[:10] < cutover:
                continue
            text = review.read_text(encoding="utf-8")
            if "## Findings" not in text:
                continue
            findings = text.split("## Findings", 1)[1].split("\n## ", 1)[0].strip()
            if findings and findings != "none":
                out.append(Session("claude", sid, entry["path"], review.stem[:10], review, [("user", findings)]))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", required=True, type=Path)
    parser.add_argument("--claude-root", type=Path, default=Path.home() / ".claude/projects")
    parser.add_argument("--codex-root", type=Path, default=Path.home() / ".codex/sessions")
    sub = parser.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init")
    init.add_argument("--cutover", required=True)
    sub.add_parser("status")
    batch = sub.add_parser("batch")
    batch.add_argument("--limit", type=int, default=10)
    batch.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    hub = args.hub.resolve()
    ledger = load_ledger(hub)
    now = datetime.now(timezone.utc)
    if args.cmd == "init":
        if ledger.get("cutover"):
            raise SystemExit(f"ERROR: cutover already set to {ledger['cutover']}")
        ledger["cutover"] = args.cutover
        save_json(hub / LEDGER, ledger)
        print(json.dumps({"cutover": args.cutover}))
        return
    sessions = pending(hub, ledger, now, args.claude_root, args.codex_root) + extra_sources(hub, ledger)
    if args.cmd == "status":
        counts = {"claude": 0, "codex": 0}
        for s in sessions:
            counts[s.tool] += 1
        print(json.dumps({"cutover": ledger.get("cutover"), "last_scan": ledger.get("last_scan"),
                          "pending": counts}, ensure_ascii=False))
        return
    chosen = sessions[: args.limit]
    payload = {"sessions": [{"tool": s.tool, "id": s.id, "date": s.started[:10],
                             "project": project_for(s.cwd, hub), "text": normalize(s)} for s in chosen]}
    save_json(args.out, payload)
    print(json.dumps({"written": len(chosen), "remaining": len(sessions) - len(chosen)}))


if __name__ == "__main__":
    main()
