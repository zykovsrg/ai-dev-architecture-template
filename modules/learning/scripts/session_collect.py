#!/usr/bin/env python3
"""Find new Hub sessions in Claude Code and Codex transcripts and normalize them.

Read-only over transcript folders. Writes only ai/learning/scan-ledger.json and
the batch folder outside the Hub (default ${TMPDIR:-/tmp}/hub-session-scan/):
one plain-text file per session plus index.json. No transcript text is written
inside the Hub.
"""
from __future__ import annotations

import argparse
import hashlib
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
BATCH_CHARS = 60000
SESSION_CHARS = 40000
# Turns that run the learning scripts belong to the scan itself, not to user work
SCAN_SCRIPTS = re.compile(r"session_collect\.py|session_rules\.py")


@dataclass
class Session:
    tool: str
    id: str
    cwd: str
    started: str
    path: Path
    turns: list = field(default_factory=list)
    source_sha256: str = ""


def _lines(path, strict=False):
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            try:
                yield json.loads(raw)
            except ValueError:
                if strict:
                    raise ValueError(f"invalid transcript record in {path}")
                continue


def _short(value, limit=200):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


def _tool_turn(name, value):
    full = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return ("scan" if SCAN_SCRIPTS.search(full or "") else "tool", f"{name}: {_short(value)}")


def drop_scan_turns(turns):
    """Remove turns that run the learning scripts and the assistant report after them."""
    out, dropping = [], False
    for role, text in turns:
        if role == "scan":
            dropping = True
            continue
        if dropping:
            if role == "user":
                dropping = False
            else:
                if role == "assistant":
                    dropping = False
                continue
        out.append((role, text))
    return out


def parse_claude(path):
    sid = cwd = started = None
    turns, names = [], {}
    for rec in _lines(path, strict=True):
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
                turns.append(_tool_turn(item.get("name"), item.get("input")))
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
    for rec in _lines(path, strict=True):
        payload = rec.get("payload") or {}
        if rec.get("type") == "session_meta":
            meta = payload
            continue
        if rec.get("type") != "response_item":
            continue
        kind = payload.get("type")
        if kind == "message" and payload.get("role") in ("user", "assistant"):
            text = " ".join(part.get("text", "") for part in payload.get("content") or []).strip()
            if text and not text.startswith(("<environment_context>", "<permissions instructions>", "<collaboration_mode>")) and not text.startswith("# AGENTS.md"):
                turns.append((payload["role"], text))
        elif kind in ("custom_tool_call", "function_call"):
            last_tool = payload.get("name", "tool")
            turns.append(_tool_turn(last_tool, payload.get("input") or payload.get("arguments")))
        elif kind in ("custom_tool_call_output", "function_call_output"):
            output = payload.get("output")
            output = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
            if "error" in output.lower():
                turns.append(("error", f"{last_tool}: {_short(output)}"))
    if not meta or not meta.get("id") or (isinstance(meta.get("source"), dict) and "subagent" in meta["source"]):
        return None
    return Session("codex", meta["id"], meta.get("cwd", ""), meta.get("timestamp", ""), Path(path), turns)


def normalize(session, limit=SESSION_CHARS):
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
    """Active registered project containing cwd; archived or unknown -> hub."""
    best = None
    for pid, entry in registry(hub).items():
        if entry.get("status") != "active":
            continue
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


def source_hash(session):
    return hashlib.sha256(session.path.read_bytes()).hexdigest() if session.path.is_file() else hashlib.sha256(full_text(session).encode()).hexdigest()


def source_key(tool, sid, digest):
    return f"{tool}:{sid}:{digest}"


def full_text(session):
    return "\n".join(f"{role.upper()}: {text}" for role, text in session.turns)


def _metadata_id(tool, path):
    """Read only a bounded header prefix, never full unrelated transcript bodies."""
    field = "sessionId" if tool == "claude" else "id"
    with path.open("r", encoding="utf-8") as handle:
        for _ in range(8):
            prefix = handle.readline(16384)
            if not prefix:
                break
            if tool == "claude" or re.search(r'"type"\s*:\s*"session_meta"', prefix):
                match = re.search(r'"' + field + r'"\s*:\s*("(?:[^"\\]|\\.)*")', prefix)
                if match:
                    return json.loads(match.group(1))
            if not prefix.endswith("\n"):
                break
    return None


def pending(hub, ledger, now, claude_root, codex_root, active_minutes=15, replay=()):
    wanted = {key for key in replay if not (key[0] == "claude" and key[1].startswith(("obs-", "review-")))}
    if replay and not wanted:
        return []
    if not ledger.get("cutover"):
        if wanted:
            raise ValueError("selected replay sources require an initialized cutover")
        return []
    cutover = ledger["cutover"]
    fresh = now - timedelta(minutes=active_minutes)
    latest, found = {}, set()
    for tool, path in _files(claude_root, codex_root):
        if replay and (tool, _metadata_id(tool, path)) not in replay:
            continue
        mtime = path.stat().st_mtime
        if datetime.fromtimestamp(mtime, timezone.utc) > fresh:
            if replay:
                raise ValueError(f"selected replay source still active: {tool}:{path.name}")
            continue
        before_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        session = parse_claude(path) if tool == "claude" else parse_codex(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != before_hash:
            raise ValueError("source changed during parsing")
        if (session is None or (session.id in ledger["processed"].get(tool, []) and (tool, session.id) not in replay
                    and not any(k.startswith(f"{tool}:{session.id}:") for k in ledger.get("completed_sources", [])))
                or session.started[:10] < cutover or not _inside(session.cwd, hub)):
            continue
        # Skip sessions started by the learning scanner itself
        if session.turns and session.turns[0][0] == "user" and session.turns[0][1].startswith("[hub-session-scan]"):
            continue
        if replay and (tool, session.id) not in replay:
            continue
        session.source_sha256 = before_hash
        found.add((tool, session.id))
        if source_key(tool, session.id, session.source_sha256) in ledger.get("completed_sources", []):
            continue
        session.turns = drop_scan_turns(session.turns)
        key = (session.tool, session.id)
        if key not in latest or mtime >= latest[key][0]:
            latest[key] = (mtime, session)
    if wanted - found:
        raise ValueError("selected replay sources unavailable: " + ", ".join(f"{t}:{sid}" for t, sid in sorted(wanted - found)))
    return [session for _, session in latest.values()]


def _find_date(text):
    match = re.search(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)|(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)", text)
    if not match:
        return None
    parts = match.groups()[:3] if match.group(1) else match.groups()[3:]
    return "-".join(parts)


def _read_snapshot(path):
    raw = path.read_bytes()
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()


def extra_sources(hub, ledger, replay=()):
    """New workflow observations and session-review findings as pseudo-sessions."""
    wanted = {key for key in replay if key[0] == "claude" and key[1].startswith(("obs-", "review-"))}
    cutover = ledger.get("cutover")
    if not cutover:
        if wanted:
            raise ValueError("selected replay sources require an initialized cutover")
        return []
    out, done = [], set(ledger["processed"].get("claude", []))
    journal = hub / "ai/workflow-observations.md"
    journal_selected = not replay or any(tool == "claude" and sid.startswith("obs-") for tool, sid in replay)
    if journal_selected and journal.exists():
        journal_text, journal_digest = _read_snapshot(journal)
        entries = [l for l in journal_text.splitlines() if re.match(r"^- \d{4}-\d{2}-\d{2} \|", l)]
        for number, line in enumerate(entries, 1):
            sid = f"obs-{number}"
            if replay and ("claude", sid) not in replay:
                continue
            if (sid not in done or ("claude", sid) in replay) and line[2:12] >= cutover:
                out.append(Session("claude", sid, str(hub), line[2:12], journal, [("user", line[2:])], source_sha256=journal_digest))
    for pid, entry in registry(hub).items():
        if entry.get("status") != "active":
            continue
        for review in sorted(Path(entry["path"], "ai/session-reviews").glob("*.md")):
            sid = f"review-{pid}-{review.stem}"
            if replay and ("claude", sid) not in replay:
                continue
            if sid in done and ("claude", sid) not in replay:
                continue
            text, review_digest = _read_snapshot(review)
            date = _find_date(review.stem) or _find_date(text)
            if not date or date < cutover:
                continue
            if "## Findings" not in text:
                continue
            findings = text.split("## Findings", 1)[1].split("\n## ", 1)[0].strip()
            if (findings and findings != "none") or ("claude", sid) in wanted:
                turns = [("user", findings)] if findings and findings != "none" else []
                out.append(Session("claude", sid, entry["path"], date, review, turns, source_sha256=review_digest))
    selected, found = [], set()
    for session in out:
        if replay and (session.tool, session.id) not in replay:
            continue
        if source_hash(session) != session.source_sha256:
            raise ValueError("source changed after reading extra source")
        found.add((session.tool, session.id))
        if source_key(session.tool, session.id, session.source_sha256) not in ledger.get("completed_sources", []):
            selected.append(session)
    if wanted - found:
        raise ValueError("selected replay extra sources unavailable: " + ", ".join(f"{t}:{sid}" for t, sid in sorted(wanted - found)))
    return selected


def default_batch_dir():
    return Path(os.environ.get("TMPDIR") or "/tmp") / "hub-session-scan"


def _session_file(tool, sid):
    return f"{tool}-{re.sub(r'[^A-Za-z0-9._-]', '_', sid)}.txt"


def write_batch(hub, sessions, out_dir, limit=10, max_chars=BATCH_CHARS):
    """Write bounded, contiguous parts. `remaining` retains its source-count meaning."""
    out_dir = Path(out_dir)
    if _inside(out_dir, hub):
        raise ValueError("batch folder must be outside the Hub")
    if limit < 1 or max_chars < 1024:
        raise ValueError("batch budget must allow at least one part")
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger = load_ledger(hub)
    entries, names, total, chosen = [], set(), 0, 0
    for session in sessions:
        if len(entries) >= limit:
            break
        project = project_for(session.cwd, hub)
        digest = session.source_sha256 or source_hash(session)
        if source_hash(session) != digest:
            raise ValueError("source changed before collection")
        key = source_key(session.tool, session.id, digest)
        done = ledger.get("parts", {}).get(key, {})
        text = full_text(session)
        size = next(iter(done.values()))["size"] if done else min(30000, max_chars - 512)
        if size + 512 > max_chars:
            raise ValueError("budget smaller than existing part layout")
        pieces = [text[n:n + size] for n in range(0, len(text), size)] or [""]
        added = False
        # One part per source per batch prevents a long source monopolising a batch.
        for number, piece in enumerate(pieces):
            part_id = hashlib.sha256(f"{key}:{number * size}:{len(piece)}".encode()).hexdigest()
            if part_id in done:
                continue
            offset, cursor, start_role = number * size, 0, "user"
            for role, turn_text in session.turns:
                end = cursor + len(f"{role.upper()}: {turn_text}") + 1
                if cursor <= offset < end:
                    start_role = role
                    break
                cursor = end
            head = f"Session: {session.tool} {session.id}\nDate: {session.started[:10]}\nProject: {project}\nPart: {number + 1}/{len(pieces)}\nRole at part start: {start_role.upper()}\n\n"
            body = head + piece
            if total + len(body) > max_chars:
                break
            name = _session_file(session.tool, session.id)[:-4] + "-" + part_id[:16] + ".txt"
            path = out_dir / name
            path.write_text(body, encoding="utf-8")
            entries.append({"tool": session.tool, "id": session.id, "date": session.started[:10], "project": project,
                            "file": str(path), "chars": len(body), "part_id": part_id,
                            "part_index": number, "part_count": len(pieces), "part_size": size,
                            "sha256": hashlib.sha256(body.encode()).hexdigest(), "source_sha256": digest,
                            "source_file": str(session.path.resolve()) if session.path.is_file() else None})
            names.add(name)
            total += len(body)
            added = True
            break
        if added:
            chosen += 1
    for stale in out_dir.glob("*.txt"):
        if stale.name not in names and stale.stat().st_size:
            stale.write_text("", encoding="utf-8")
    index = {"format": 2, "sessions": entries}
    save_json(out_dir / "index.json", index)
    return index, len(sessions) - chosen


def _keys(values):
    keys = set()
    for value in values or []:
        tool, _, sid = value.partition(":")
        if tool not in ("claude", "codex") or not sid:
            raise SystemExit(f"ERROR: expected <claude|codex>:<session id>, got {value}")
        keys.add((tool, sid))
    return keys


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
    batch.add_argument("--max-chars", type=int, default=BATCH_CHARS)
    batch.add_argument("--out-dir", type=Path, default=None)
    batch.add_argument("--session", action="append", help="only this <tool>:<id> (repeatable)")
    batch.add_argument("--skip", action="append", help="leave out this <tool>:<id> (repeatable)")
    batch.add_argument("--replay", action="append", help="replay only selected processed <tool>:<id> without clearing history")
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
    replay = _keys(getattr(args, "replay", None))
    try:
        sessions = pending(hub, ledger, now, args.claude_root, args.codex_root, replay=replay) + extra_sources(hub, ledger, replay=replay)
    except (OSError, ValueError) as error:
        raise SystemExit(f"ERROR: {error}")
    if args.cmd == "status":
        # `pending` counts every queued item; journal lines and review files are
        # pseudo-sessions, so they are also reported apart from real sessions.
        counts = {"claude": 0, "codex": 0}
        real = {"claude": 0, "codex": 0}
        journal = reviews = 0
        for s in sessions:
            counts[s.tool] += 1
            if s.id.startswith("obs-"):
                journal += 1
            elif s.id.startswith("review-"):
                reviews += 1
            else:
                real[s.tool] += 1
        print(json.dumps({"cutover": ledger.get("cutover"), "last_scan": ledger.get("last_scan"),
                          "pending": counts, "sessions": real, "journal": journal,
                          "reviews": reviews}, ensure_ascii=False))
        return
    only, skip = _keys(args.session), _keys(args.skip)
    sessions = [s for s in sessions if (s.tool, s.id) not in skip and (not only or (s.tool, s.id) in only)]
    out_dir = (args.out_dir or default_batch_dir()).resolve()
    if _inside(out_dir, hub):
        raise SystemExit("ERROR: the batch folder must be outside the Hub")
    index, remaining = write_batch(hub, sessions, out_dir, args.limit, args.max_chars)
    print(json.dumps({"written": len(index["sessions"]), "remaining": remaining,
                      "index": str(out_dir / "index.json"),
                      "files": [e["file"] for e in index["sessions"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
