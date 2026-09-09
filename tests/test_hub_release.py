import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.hub_release import apply, decide, preview, target_path


class ReleaseDecisionTests(unittest.TestCase):
    def test_equal_current_and_incoming_is_kept(self):
        self.assertEqual(decide("new", "old", "new"), "keep")

    def test_unchanged_installed_file_is_replaced(self):
        self.assertEqual(decide("old", "old", "new"), "replace")

    def test_changed_installed_file_is_a_conflict(self):
        self.assertEqual(decide("mine", "old", "new"), "conflict")

    def test_missing_file_is_created(self):
        self.assertEqual(decide(None, "old", "new"), "create")

    def test_file_without_baseline_is_not_overwritten(self):
        self.assertEqual(decide("mine", None, "new"), "conflict")

    def test_unmodified_retired_file_is_removed(self):
        self.assertEqual(decide("old", "old", None), "remove")

    def test_modified_retired_file_is_a_conflict(self):
        self.assertEqual(decide("mine", "old", None), "conflict")

    def test_symlinked_target_component_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outside").mkdir()
            (root / "ai").symlink_to(root / "outside", target_is_directory=True)
            with self.assertRaises(ValueError):
                target_path(root, "ai/architecture.md")

    def test_first_adoption_does_not_overwrite_a_changed_managed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / "hub"
            hub.mkdir()
            (hub / "AGENTS.md").write_text("mine", encoding="utf-8")
            source = Path(__file__).resolve().parents[1]
            plan = preview(source, hub)
            agents = next(row for row in plan["operations"] if row["target"] == "AGENTS.md")
            self.assertEqual(agents["action"], "conflict")

    def test_apply_replaces_only_a_file_matching_its_installed_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / "hub"
            hub.mkdir()
            old = b"old managed entry\n"
            (hub / "AGENTS.md").write_bytes(old)
            state = hub / ".local" / "hub-release"
            state.mkdir(parents=True)
            state.joinpath("installed.json").write_text(json.dumps({"files": [{"target": "AGENTS.md", "sha256": hashlib.sha256(old).hexdigest()}]}), encoding="utf-8")
            source = Path(__file__).resolve().parents[1]
            plan = preview(source, hub)
            result = apply(source, hub, plan["plan_sha256"])
            self.assertIn("AGENTS.md", result["changed"])
            self.assertEqual((hub / "AGENTS.md").read_bytes(), (source / "hub-template" / "AGENTS.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
