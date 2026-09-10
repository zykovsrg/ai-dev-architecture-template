import json
import tempfile
import unittest
from pathlib import Path

from scripts.workflow_friction import list_pending, resolve


class WorkflowFrictionTests(unittest.TestCase):
    def test_unresolved_source_survives_a_list_and_resolves_once(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory)
            source = hub / "ai" / "tmp" / "workflow-friction"
            source.mkdir(parents=True)
            source.joinpath("2026-09-09.txt").write_text("first\nsecond\n", encoding="utf-8")
            pending = list_pending(hub, "2026-09-09")
            self.assertEqual(len(pending["entries"]), 2)
            resolve(hub, "2026-09-09", pending["source_sha256"], pending["entries"][0]["id"], "accepted")
            again = list_pending(hub, "2026-09-09")
            self.assertEqual([item["text"] for item in again["entries"]], ["second"])
            self.assertTrue(source.joinpath("2026-09-09.txt").exists())

    def test_stale_source_cannot_be_resolved(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory)
            source = hub / "ai" / "tmp" / "workflow-friction"
            source.mkdir(parents=True)
            file = source / "2026-09-09.txt"
            file.write_text("first\n", encoding="utf-8")
            pending = list_pending(hub, "2026-09-09")
            file.write_text("changed\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                resolve(hub, "2026-09-09", pending["source_sha256"], pending["entries"][0]["id"], "accepted")


if __name__ == "__main__":
    unittest.main()
