import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "scripts/update-installed-hub.sh"
REMOVED = {"scripts/obsidian-task-sync.sh", "scripts/generate-obsidian-projects-kanban.sh", "ai/rules/obsidian.md"}


def tree_digest(path):
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(path)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


class ObsidianSwitchTests(unittest.TestCase):
    def run_updater(self, hub, *args):
        env = dict(os.environ)
        env["HUB_CALENDAR_SKIP_BRIDGE"] = "1"
        env["HUB_CALENDAR_SKIP_VENV"] = "1"
        return subprocess.run(["bash", str(UPDATER), "--source", str(ROOT), "--hub", str(hub), "--allow-dirty", *args],
                              capture_output=True, text=True, check=False, env=env)

    def plan_sha(self, output):
        return next(l.split(": ", 1)[1] for l in output.splitlines() if l.startswith("Plan SHA256: "))

    def installed_hub(self, root):
        hub = root / "_ai-hub"  # install-hub.sh requires this name and a symlink-free path
        env = dict(os.environ)
        env["HUB_CALENDAR_SKIP_BRIDGE"] = "1"
        env["HUB_CALENDAR_SKIP_VENV"] = "1"
        subprocess.run(["bash", str(ROOT / "scripts/install-hub.sh"), str(hub)],
                        check=True, capture_output=True, env=env)
        vault = hub / "projects/ai-dev-architecture/obsidian-vault/Obsidian"
        vault.mkdir(parents=True)
        (vault / "Board.md").write_text("board\n", encoding="utf-8")
        (hub / ".local/obsidian-scope").write_text("demo\n", encoding="utf-8")
        return hub

    def test_disable_then_enable(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            vault = hub / "projects/ai-dev-architecture/obsidian-vault"
            before = tree_digest(vault)

            dry = self.run_updater(hub, "--dry-run", "--without", "obsidian")
            self.assertEqual(dry.returncode, 0, dry.stderr)
            removed = {l.split(": ", 1)[1] for l in dry.stdout.splitlines() if l.startswith("remove: ")}
            self.assertEqual(removed, REMOVED)
            self.assertIn("replace: ai/modules.md", dry.stdout)
            self.assertIn("Module change: -obsidian", dry.stdout)

            applied = self.run_updater(hub, "--apply", "--without", "obsidian", "--confirm-plan", self.plan_sha(dry.stdout))
            self.assertEqual(applied.returncode, 0, applied.stderr)
            for target in REMOVED:
                self.assertFalse((hub / target).exists(), target)
            self.assertEqual(tree_digest(vault), before)
            self.assertEqual((hub / ".local/obsidian-scope").read_text(), "demo\n")
            self.assertNotIn("obsidian", (hub / "ai/modules.md").read_text().split("## Events")[0])

            check = self.run_updater(hub, "--check")
            self.assertEqual(check.returncode, 0, check.stdout)
            drift = subprocess.run(["python3", str(ROOT / "scripts/hub_release.py"), "drift",
                                    "--source", str(ROOT), "--hub", str(hub)], capture_output=True, text=True)
            self.assertEqual(drift.returncode, 0, drift.stdout)

            dry = self.run_updater(hub, "--dry-run", "--with", "obsidian")
            self.assertIn("Module change: +obsidian", dry.stdout)
            applied = self.run_updater(hub, "--apply", "--with", "obsidian", "--confirm-plan", self.plan_sha(dry.stdout))
            self.assertEqual(applied.returncode, 0, applied.stderr)
            for target in REMOVED:
                self.assertTrue((hub / target).exists(), target)

    def test_locally_changed_obsidian_script_blocks_disable(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            script = hub / "scripts/obsidian-task-sync.sh"
            script.write_text(script.read_text() + "\n# local\n")
            dry = self.run_updater(hub, "--dry-run", "--without", "obsidian")
            self.assertIn("conflict: scripts/obsidian-task-sync.sh", dry.stdout)
            applied = self.run_updater(hub, "--apply", "--without", "obsidian", "--confirm-plan", self.plan_sha(dry.stdout))
            self.assertNotEqual(applied.returncode, 0)
            self.assertTrue(script.exists())

    def test_required_module_cannot_be_disabled(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            result = self.run_updater(hub, "--dry-run", "--without", "tasks")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot be switched", result.stderr)


if __name__ == "__main__":
    unittest.main()
