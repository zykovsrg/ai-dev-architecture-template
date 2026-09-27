import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.hub_release import apply, preview, release_sources


ROOT = Path(__file__).resolve().parents[1]


class RetiredManagedFileTests(unittest.TestCase):
    def source_copy(self, root):
        source = root / "source"
        for relative in release_sources(ROOT):
            src = ROOT / relative
            dst = source / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return source

    def install(self, source, hub):
        hub.mkdir()
        plan = preview(source, hub)
        apply(source, hub, plan["plan_sha256"])

    def operation(self, plan, target):
        return next(row for row in plan["operations"] if row["target"] == target)

    def retire(self, source, relative):
        """Model real upstream retirement: delete the source file AND drop its
        'Installs' line from the owning passport, so the passport never
        declares a source that no longer exists."""
        (source / relative).unlink()
        needle = f"- {relative} ->"
        for passport in sorted((source / "modules").glob("*/module.md")):
            lines = passport.read_text(encoding="utf-8").splitlines()
            kept = [line for line in lines if not line.strip().startswith(needle)]
            if kept != lines:
                passport.write_text("\n".join(kept) + "\n", encoding="utf-8")

    def test_managed_file_disappeared_upstream_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source_copy(root)
            hub = root / "hub"
            self.install(source, hub)
            retired = source / "modules/core/data/CLAUDE.md"
            self.retire(source, "modules/core/data/CLAUDE.md")

            plan = preview(source, hub)
            self.assertEqual(self.operation(plan, "CLAUDE.md")["action"], "remove")
            result = apply(source, hub, plan["plan_sha256"])

            self.assertIn("CLAUDE.md", result["changed"])
            self.assertFalse((hub / "CLAUDE.md").exists())

    def test_modified_retired_managed_file_is_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source_copy(root)
            hub = root / "hub"
            self.install(source, hub)
            (hub / "CLAUDE.md").write_text("local edit\n", encoding="utf-8")
            self.retire(source, "modules/core/data/CLAUDE.md")

            plan = preview(source, hub)
            self.assertEqual(self.operation(plan, "CLAUDE.md")["action"], "conflict")
            with self.assertRaisesRegex(ValueError, "conflicting local changes"):
                apply(source, hub, plan["plan_sha256"])
            self.assertEqual((hub / "CLAUDE.md").read_text(encoding="utf-8"), "local edit\n")

    def test_retired_create_if_missing_memory_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source_copy(root)
            hub = root / "hub"
            self.install(source, hub)
            memory = hub / "ai/project-registry.md"
            before = memory.read_bytes()
            self.retire(source, "modules/projects/data/ai/project-registry.md")

            plan = preview(source, hub)
            rows = [row for row in plan["operations"] if row["target"] == "ai/project-registry.md"]
            self.assertTrue(not rows or rows[0]["action"] == "keep")
            apply(source, hub, plan["plan_sha256"])
            self.assertEqual(memory.read_bytes(), before)

    def test_failure_after_removal_restores_exact_bytes_and_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source_copy(root)
            hub = root / "hub"
            self.install(source, hub)
            retired_target = hub / "CLAUDE.md"
            before = retired_target.read_bytes()
            os.chmod(retired_target, 0o640)
            before_mode = stat.S_IMODE(retired_target.stat().st_mode)
            self.retire(source, "modules/core/data/CLAUDE.md")

            architecture = source / "modules/core/data/ai/architecture.md"
            architecture.write_text(architecture.read_text(encoding="utf-8") + "\n<!-- changed after removal -->\n", encoding="utf-8")
            plan = preview(source, hub)
            self.assertEqual(self.operation(plan, "CLAUDE.md")["action"], "remove")
            self.assertEqual(self.operation(plan, "ai/architecture.md")["action"], "replace")

            original_replace = os.replace

            def fail_later_replace(src, dst):
                if Path(dst).resolve() == (hub / "ai/architecture.md").resolve():
                    raise OSError("failure after removal")
                return original_replace(src, dst)

            with mock.patch("scripts.hub_release.os.replace", side_effect=fail_later_replace):
                with self.assertRaisesRegex(OSError, "failure after removal"):
                    apply(source, hub, plan["plan_sha256"])

            self.assertEqual(retired_target.read_bytes(), before)
            self.assertEqual(stat.S_IMODE(retired_target.stat().st_mode), before_mode)


if __name__ == "__main__":
    unittest.main()
