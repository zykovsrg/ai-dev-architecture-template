#!/usr/bin/env python3
"""Confirm which model a hub-session-scanner subagent actually used.

Reads, read-only, only `~/.claude/projects/*/*/subagents/agent-<id>.jsonl`
and only the `message.model` field of assistant entries. Prints one JSON line
and exits 1 when the transcript is missing, has no model, or any model does
not contain the expected substring.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

AGENT_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def models_for(projects: Path, agent_id: str) -> tuple[list[str], list[str]]:
    paths = sorted(projects.glob(f"*/*/subagents/agent-{agent_id}.jsonl"))
    found: list[str] = []
    for path in paths:
        if path.is_symlink() or not path.is_file():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict) or entry.get("type") != "assistant":
                    continue
                message = entry.get("message")
                model = message.get("model") if isinstance(message, dict) else None
                if isinstance(model, str) and model not in found:
                    found.append(model)
    return [str(p) for p in paths], found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-id", action="append", required=True)
    parser.add_argument("--expect", default="haiku")
    parser.add_argument("--projects-dir", default=str(Path.home() / ".claude/projects"))
    args = parser.parse_args()

    projects = Path(args.projects_dir)
    ok = True
    for agent_id in args.agent_id:
        if not AGENT_ID.match(agent_id):
            print(json.dumps({"agent": agent_id, "ok": False, "error": "bad agent id"}))
            ok = False
            continue
        paths, models = models_for(projects, agent_id)
        result = {"agent": agent_id, "models": models, "ok": False}
        if not paths:
            result["error"] = "transcript not found"
        elif not models:
            result["error"] = "no model recorded"
        elif any(args.expect not in m for m in models):
            result["error"] = f"unexpected model, expected '{args.expect}'"
        else:
            result["ok"] = True
        ok = ok and result["ok"]
        print(json.dumps(result, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
