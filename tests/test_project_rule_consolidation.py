import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "project_rule_consolidation", ROOT / "scripts" / "project_rule_consolidation.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProjectRuleConsolidationTests(unittest.TestCase):
    def test_only_exact_legacy_copies_are_eligible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "projects" / "demo"
            (project / "ai").mkdir(parents=True)
            for relative in ("AGENTS.md", "CLAUDE.md", "ai/architecture.md"):
                source = ROOT / "template" / relative
                target = project / relative
                target.write_bytes(source.read_bytes())
            self.assertEqual(MODULE.eligible_files(ROOT, project), [
                "AGENTS.md", "CLAUDE.md", "ai/architecture.md"
            ])
            (project / "AGENTS.md").write_text("project-specific rule\n", encoding="utf-8")
            self.assertEqual(MODULE.eligible_files(ROOT, project), [
                "CLAUDE.md", "ai/architecture.md"
            ])

    def test_entry_has_no_copied_workflow_rules(self):
        entry = MODULE.render_entry()
        self.assertIn("../../AGENTS.md", entry)
        self.assertNotIn("Superpowers", entry)

    def test_accepts_the_known_old_shared_output_rule(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "projects" / "demo"
            (project / "ai").mkdir(parents=True)
            for relative in ("AGENTS.md", "CLAUDE.md"):
                source = MODULE.legacy_shared_variant(
                    (ROOT / "template" / relative).read_text(encoding="utf-8")
                )
                (project / relative).write_text(source, encoding="utf-8")
            self.assertEqual(MODULE.eligible_files(ROOT, project), ["AGENTS.md", "CLAUDE.md"])


if __name__ == "__main__":
    unittest.main()
