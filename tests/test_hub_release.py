import tempfile
import unittest
from pathlib import Path

from scripts.hub_release import decide, target_path


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


if __name__ == "__main__":
    unittest.main()
