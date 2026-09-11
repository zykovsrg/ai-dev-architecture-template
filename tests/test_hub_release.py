import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.hub_release import RUNTIME_SCRIPTS, apply, build_manifest, decide, preview, target_path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseDecisionTests(unittest.TestCase):
    def source_copy(self, root):
        source = root / "source"
        shutil.copytree(ROOT / "hub-template", source / "hub-template")
        for relative in RUNTIME_SCRIPTS:
            src = ROOT / relative
            dst = source / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return source

    def existing_installed_hub(self, root):
        hub = root / "hub"
        hub.mkdir()
        old = b"old managed entry\n"
        agents = hub / "AGENTS.md"
        agents.write_bytes(old)
        os.chmod(agents, 0o640)
        state = hub / ".local" / "hub-release"
        state.mkdir(parents=True)
        installed_bytes = json.dumps({"files": [{
            "target": "AGENTS.md",
            "sha256": hashlib.sha256(old).hexdigest(),
            "policy": "managed",
        }]}, indent=2).encode()
        installed = state / "installed.json"
        installed.write_bytes(installed_bytes)
        return hub, old, installed_bytes

    def assert_existing_before_state(self, hub, old, installed_bytes):
        self.assertEqual((hub / "AGENTS.md").read_bytes(), old)
        self.assertEqual(stat.S_IMODE((hub / "AGENTS.md").stat().st_mode), 0o640)
        self.assertEqual((hub / ".local/hub-release/installed.json").read_bytes(), installed_bytes)
        self.assertFalse((hub / "CLAUDE.md").exists())

    def assert_absent_before_state(self, hub):
        self.assertFalse((hub / "AGENTS.md").exists())
        self.assertFalse((hub / "CLAUDE.md").exists())
        self.assertFalse((hub / ".local/hub-release/installed.json").exists())

    def test_release_includes_task_record_checker(self):
        targets = {entry["target"] for entry in build_manifest(ROOT)["files"]}
        self.assertIn("scripts/check-all-task-records.sh", targets)
        self.assertIn("scripts/read-compact-task-index.py", targets)

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

    def test_preview_hash_changes_when_source_bytes_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source_copy(root)
            hub = root / "hub"
            hub.mkdir()
            before = preview(source, hub)["plan_sha256"]
            agents = source / "hub-template" / "AGENTS.md"
            agents.write_text(agents.read_text(encoding="utf-8") + "\n<!-- changed -->\n", encoding="utf-8")
            after = preview(source, hub)["plan_sha256"]
            self.assertNotEqual(before, after)

    def test_apply_refuses_different_plan_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / "hub"
            hub.mkdir()
            with self.assertRaisesRegex(ValueError, "plan changed"):
                apply(ROOT, hub, "0" * 64)

    def test_first_adoption_does_not_overwrite_a_changed_managed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / "hub"
            hub.mkdir()
            (hub / "AGENTS.md").write_text("mine", encoding="utf-8")
            plan = preview(ROOT, hub)
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
            plan = preview(ROOT, hub)
            result = apply(ROOT, hub, plan["plan_sha256"])
            self.assertIn("AGENTS.md", result["changed"])
            self.assertEqual((hub / "AGENTS.md").read_bytes(), (ROOT / "hub-template" / "AGENTS.md").read_bytes())

    def test_create_if_missing_memory_is_untouched_when_present(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / "hub"
            (hub / "ai").mkdir(parents=True)
            memory = hub / "ai" / "project-registry.md"
            memory.write_text("# user registry\n", encoding="utf-8")
            plan = preview(ROOT, hub)
            row = next(x for x in plan["operations"] if x["target"] == "ai/project-registry.md")
            self.assertEqual(row["action"], "keep")
            apply(ROOT, hub, plan["plan_sha256"])
            self.assertEqual(memory.read_text(encoding="utf-8"), "# user registry\n")

    def test_apply_failure_restores_already_replaced_file(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / "hub"
            hub.mkdir()
            old_ignore = b"old-ignore\n"
            old_agents = b"old-agents\n"
            (hub / ".gitignore").write_bytes(old_ignore)
            (hub / "AGENTS.md").write_bytes(old_agents)
            state = hub / ".local" / "hub-release"
            state.mkdir(parents=True)
            state.joinpath("installed.json").write_text(json.dumps({"files": [
                {"target": ".gitignore", "sha256": hashlib.sha256(old_ignore).hexdigest()},
                {"target": "AGENTS.md", "sha256": hashlib.sha256(old_agents).hexdigest()},
            ]}), encoding="utf-8")
            plan = preview(ROOT, hub)
            original_replace = os.replace
            replacements = 0

            def flaky_replace(src, dst):
                nonlocal replacements
                if "hub-release-" in str(src):
                    replacements += 1
                    if replacements == 2:
                        raise OSError("injected apply failure")
                return original_replace(src, dst)

            with mock.patch("scripts.hub_release.os.replace", side_effect=flaky_replace):
                with self.assertRaisesRegex(OSError, "injected apply failure"):
                    apply(ROOT, hub, plan["plan_sha256"])
            self.assertEqual((hub / ".gitignore").read_bytes(), old_ignore)
            self.assertEqual((hub / "AGENTS.md").read_bytes(), old_agents)

    def test_existing_installed_state_rolls_back_if_metadata_staging_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            hub, old, installed_bytes = self.existing_installed_hub(Path(directory))
            plan = preview(ROOT, hub)
            with mock.patch("scripts.hub_release.tempfile.mkstemp", side_effect=OSError("metadata stage failure")):
                with self.assertRaisesRegex(OSError, "metadata stage failure"):
                    apply(ROOT, hub, plan["plan_sha256"])
            self.assert_existing_before_state(hub, old, installed_bytes)

    def test_absent_installed_state_stays_absent_if_metadata_staging_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / "hub"
            hub.mkdir()
            plan = preview(ROOT, hub)
            with mock.patch("scripts.hub_release.tempfile.mkstemp", side_effect=OSError("metadata stage failure")):
                with self.assertRaisesRegex(OSError, "metadata stage failure"):
                    apply(ROOT, hub, plan["plan_sha256"])
            self.assert_absent_before_state(hub)

    def test_existing_installed_state_rolls_back_if_metadata_replace_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            hub, old, installed_bytes = self.existing_installed_hub(Path(directory))
            installed = hub / ".local/hub-release/installed.json"
            plan = preview(ROOT, hub)
            original_replace = os.replace

            def fail_metadata_replace(src, dst):
                if Path(dst) == installed:
                    raise OSError("metadata replace failure")
                return original_replace(src, dst)

            with mock.patch("scripts.hub_release.os.replace", side_effect=fail_metadata_replace):
                with self.assertRaisesRegex(OSError, "metadata replace failure"):
                    apply(ROOT, hub, plan["plan_sha256"])
            self.assert_existing_before_state(hub, old, installed_bytes)

    def test_absent_installed_state_stays_absent_if_metadata_replace_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / "hub"
            hub.mkdir()
            installed = hub / ".local/hub-release/installed.json"
            plan = preview(ROOT, hub)
            original_replace = os.replace

            def fail_metadata_replace(src, dst):
                if Path(dst) == installed:
                    raise OSError("metadata replace failure")
                return original_replace(src, dst)

            with mock.patch("scripts.hub_release.os.replace", side_effect=fail_metadata_replace):
                with self.assertRaisesRegex(OSError, "metadata replace failure"):
                    apply(ROOT, hub, plan["plan_sha256"])
            self.assert_absent_before_state(hub)


if __name__ == "__main__":
    unittest.main()
