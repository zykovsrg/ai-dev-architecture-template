#!/usr/bin/env python3
"""Regression checks: status reports journal lines apart from real sessions."""

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]  # modules/learning
SCRIPT = ROOT / "scripts" / "session_collect.py"


def make_hub(tmp: Path) -> Path:
    hub = tmp / "hub"
    (hub / "ai/learning").mkdir(parents=True)
    (hub / "ai/project-registry.md").write_text("# Registry\n")
    (hub / "ai/learning/scan-ledger.json").write_text(json.dumps(
        {"cutover": "2026-10-01", "last_scan": None, "processed": {"claude": [], "codex": []}}))
    (hub / "ai/workflow-observations.md").write_text(
        "# Observations\n\n- 2026-10-07 | calendar | moved a block\n- 2026-10-07 | calendar | cancelled a block\n")
    return hub


def write_claude_session(root: Path, hub: Path, sid: str) -> None:
    folder = root / "hub"
    folder.mkdir(parents=True, exist_ok=True)
    rec = {"type": "user", "sessionId": sid, "cwd": str(hub), "timestamp": "2026-10-07T10:00:00Z",
           "message": {"content": "привет"}}
    path = folder / f"{sid}.jsonl"
    path.write_text(json.dumps(rec) + "\n")
    old = time.time() - 3600
    os.utime(path, (old, old))


class SessionCollectStatusTests(unittest.TestCase):
    def test_journal_counted_apart_from_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            hub = make_hub(tmp)
            claude, codex = tmp / "claude", tmp / "codex"
            codex.mkdir()
            write_claude_session(claude, hub, "s1")
            result = subprocess.run(
                ["python3", str(SCRIPT), "--hub", str(hub), "--claude-root", str(claude),
                 "--codex-root", str(codex), "status"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["pending"], {"claude": 3, "codex": 0})
            self.assertEqual(data["sessions"], {"claude": 1, "codex": 0})
            self.assertEqual(data["journal"], 2)
            self.assertEqual(data["reviews"], 0)


if __name__ == "__main__":
    unittest.main()
