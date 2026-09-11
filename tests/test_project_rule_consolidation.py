import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "project_rule_consolidation", ROOT / "scripts" / "project_rule_consolidation.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProjectRuleConsolidationTests(unittest.TestCase):
    def test_only_exact_legacy_copies_are_eligible(self):
        fixtures = {
            "AGENTS.md": b"legacy agents\n",
            "CLAUDE.md": b"legacy claude\n",
            "ai/architecture.md": b"legacy architecture\n",
        }
        legacy_hashes = {
            relative: {MODULE.git_blob_id(data)} for relative, data in fixtures.items()
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(MODULE, "LEGACY_RULE_BLOBS", legacy_hashes):
            root = Path(directory)
            project = root / "projects" / "demo"
            (project / "ai").mkdir(parents=True)
            for relative, data in fixtures.items():
                target = project / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            self.assertEqual(MODULE.eligible_files(ROOT, project), [
                "AGENTS.md", "CLAUDE.md", "ai/architecture.md"
            ])
            (project / "AGENTS.md").write_text("project-specific rule\n", encoding="utf-8")
            self.assertEqual(MODULE.eligible_files(ROOT, project), [
                "CLAUDE.md", "ai/architecture.md"
            ])

    def test_known_pre_retirement_fingerprints_are_retained(self):
        self.assertIn("becbbbf18ad656f5fff70e578ae458d548b493db", MODULE.LEGACY_RULE_BLOBS["AGENTS.md"])
        self.assertIn("a83c9f790a7ad1b4f572b9553b89cbaaccb97adb", MODULE.LEGACY_RULE_BLOBS["CLAUDE.md"])
        self.assertIn("46d8cd64721ad7de61b6108ec56341dca20ac9d9", MODULE.LEGACY_RULE_BLOBS["ai/architecture.md"])

    def test_entry_has_no_copied_workflow_rules(self):
        entry = MODULE.render_entry()
        self.assertIn("../../AGENTS.md", entry)
        self.assertNotIn("Superpowers", entry)

    def test_no_retired_template_dependency(self):
        source = (ROOT / "scripts/project_rule_consolidation.py").read_text(encoding="utf-8")
        self.assertNotIn('source_root / "template"', source)
        self.assertFalse((ROOT / "template").exists())


if __name__ == "__main__":
    unittest.main()
