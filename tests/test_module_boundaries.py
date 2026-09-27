import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check-module-boundaries.py"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def passport(module_id, depends, installs, keywords="—"):
    lines = "\n".join(f"- {s} -> {t}" for s, t in installs)
    return (f"# Module: {module_id}\n\nId: {module_id}\nRequired: no\nSwitchable: no\n"
            f"Depends: {depends}\nUses if present: —\nRules: —\nKeywords: {keywords}\n\n"
            f"## Purpose\n\nx\n\n## Installs\n\n{lines}\n")


class BoundaryTests(unittest.TestCase):
    def fixture(self, root, a_depends):
        write(root / "modules/core/module.md", passport("core", "—", [("core/rules.md", "ai/rules.md")]))
        write(root / "core/rules.md", "core\n")
        write(root / "modules/a/module.md", passport("a", a_depends, [("a/skills/hub-a/SKILL.md", "ai/skills/hub-a/SKILL.md")]))
        write(root / "a/skills/hub-a/SKILL.md", "Run `bash scripts/b-tool.sh` and see the Vault note.\n")
        write(root / "modules/b/module.md", passport("b", "core", [("b/b-tool.sh", "scripts/b-tool.sh")], "Vault"))
        write(root / "b/b-tool.sh", "echo b\n")

    def run_check(self, root, *flags):
        return subprocess.run([sys.executable, str(SCRIPT), "--source", str(root), *flags],
                              capture_output=True, text=True, check=False)

    def test_violation_is_reported_but_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, "core")
            result = self.run_check(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("WARN a/skills/hub-a/SKILL.md: b via b-tool.sh", result.stdout)
            self.assertIn("WARN a/skills/hub-a/SKILL.md: b via Vault", result.stdout)

    def test_strict_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, "core")
            self.assertEqual(self.run_check(root, "--strict").returncode, 1)

    def test_declared_dependency_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, "core, b")
            result = self.run_check(root, "--strict")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertNotIn("WARN", result.stdout)

    def test_repository_runs_in_warning_mode(self):
        result = self.run_check(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("via Obsidian", result.stdout)
        self.assertNotIn("via obsidian-", result.stdout)


if __name__ == "__main__":
    unittest.main()
