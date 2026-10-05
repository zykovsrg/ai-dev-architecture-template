#!/usr/bin/env python3
"""Regression checks for the scanner model confirmation."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "session_scan_model.py"


def write_agent(projects: Path, agent_id: str, models: list[str]) -> None:
    folder = projects / "hub" / "session-1" / "subagents"
    folder.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"type": "user", "message": {"content": "x"}})]
    lines += [json.dumps({"type": "assistant", "message": {"model": m}}) for m in models]
    (folder / f"agent-{agent_id}.jsonl").write_text("\n".join(lines) + "\n")


def run(projects: Path, *agent_ids: str) -> subprocess.CompletedProcess:
    args = ["python3", str(SCRIPT), "--projects-dir", str(projects)]
    for agent_id in agent_ids:
        args += ["--agent-id", agent_id]
    return subprocess.run(args, capture_output=True, text=True)


class SessionScanModelTests(unittest.TestCase):
    def test_accepts_haiku(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_agent(Path(tmp), "a1", ["claude-haiku-4-5-20251001"])
            result = run(Path(tmp), "a1")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(json.loads(result.stdout)["ok"])

    def test_rejects_other_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_agent(Path(tmp), "a2", ["claude-haiku-4-5-20251001", "claude-opus-5-5"])
            result = run(Path(tmp), "a2")
            self.assertEqual(result.returncode, 1)
            self.assertIn("unexpected model", result.stdout)

    def test_rejects_missing_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(Path(tmp), "missing")
            self.assertEqual(result.returncode, 1)
            self.assertIn("transcript not found", result.stdout)

    def test_rejects_bad_agent_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(Path(tmp), "../x")
            self.assertEqual(result.returncode, 1)
            self.assertIn("bad agent id", result.stdout)


if __name__ == "__main__":
    unittest.main()
