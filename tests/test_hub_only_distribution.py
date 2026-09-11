import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HubOnlyDistributionTests(unittest.TestCase):
    def make_install_fixture(self, root: Path) -> Path:
        scripts = root / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(ROOT / "scripts/install.sh", scripts / "install.sh")
        (scripts / "install-hub.sh").write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\\n' \"${1:-}\" > \"${INSTALL_HUB_MARKER:?}\"\n",
            encoding="utf-8",
        )
        os.chmod(scripts / "install-hub.sh", 0o755)
        template = root / "template"
        template.mkdir()
        (template / "legacy.txt").write_text("legacy", encoding="utf-8")
        return scripts / "install.sh"

    def run_fixture_install(self, mode=None):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        script = self.make_install_fixture(root)
        target = root / "_ai-hub"
        marker = root / "hub-called.txt"
        command = ["bash", str(script)]
        if mode is not None:
            command += ["--mode", mode]
        command += [str(target)]
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            env={**os.environ, "INSTALL_HUB_MARKER": str(marker)},
        )
        return tmp, target, marker, result

    def test_default_install_selects_hub(self):
        tmp, target, marker, result = self.run_fixture_install()
        self.addCleanup(tmp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(marker.is_file())
        self.assertEqual(marker.read_text(encoding="utf-8").strip(), str(target))
        self.assertFalse((target / "legacy.txt").exists())

    def test_explicit_hub_selects_hub(self):
        tmp, target, marker, result = self.run_fixture_install("hub")
        self.addCleanup(tmp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(marker.is_file())
        self.assertFalse((target / "legacy.txt").exists())

    def test_standalone_is_rejected_without_writes(self):
        tmp, target, marker, result = self.run_fixture_install("standalone")
        self.addCleanup(tmp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(marker.exists())
        self.assertFalse(target.exists())
        self.assertIn("standalone", (result.stdout + result.stderr).lower())

    def test_installer_has_no_standalone_copy_path(self):
        text = (ROOT / "scripts/install.sh").read_text(encoding="utf-8")
        self.assertNotIn('SOURCE_DIR="$REPO_ROOT/template"', text)
        self.assertNotIn('rsync -av --exclude=".DS_Store" "$SOURCE_DIR/" "$TARGET_DIR/"', text)

    def test_legacy_updater_is_read_only_retirement_entrypoint(self):
        text = (ROOT / "scripts/update-installed-architecture.sh").read_text(encoding="utf-8")
        self.assertIn("retired", text.lower())
        self.assertNotIn("template/AGENTS.md", text)
        self.assertNotIn("rsync", text)
        self.assertNotIn("cp ", text)

    def test_active_docs_do_not_offer_standalone_install_or_update(self):
        roots = [ROOT / "README.md", ROOT / "getting-started", ROOT / "docs"]
        forbidden = ("--mode standalone", "standalone architecture", "update-installed-architecture.sh")
        hits = []
        for base in roots:
            paths = [base] if base.is_file() else sorted(base.rglob("*.md")) if base.exists() else []
            for path in paths:
                relative = path.relative_to(ROOT)
                if str(relative).startswith("docs/superpowers/") or str(relative).startswith("docs/audits/"):
                    continue
                text = path.read_text(encoding="utf-8").lower()
                for needle in forbidden:
                    if needle.lower() in text:
                        hits.append(f"{relative}: {needle}")
        self.assertEqual(hits, [])

    def test_hub_knowledge_skills_remain_available(self):
        for name in ("hub-knowledge-enable", "hub-knowledge-capture", "hub-knowledge-review"):
            self.assertTrue((ROOT / f"hub-template/ai/skills/{name}/SKILL.md").is_file(), name)

    def test_no_standalone_distributable_template_tree(self):
        self.assertFalse((ROOT / "template").exists())


if __name__ == "__main__":
    unittest.main()
