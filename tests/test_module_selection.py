import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.hub_release import apply, build_manifest, drift, preview, release_sources

ROOT = Path(__file__).resolve().parents[1]
OBSIDIAN_TARGETS = {"scripts/obsidian-task-sync.sh", "scripts/generate-obsidian-projects-kanban.sh"}


def install(hub, **kw):
    plan = preview(ROOT, hub, **kw)
    apply(ROOT, hub, plan["plan_sha256"], **kw)
    return plan


class ModuleSelectionTests(unittest.TestCase):
    def test_full_manifest_has_all_modules_and_modules_md(self):
        manifest = build_manifest(ROOT)
        self.assertIn("obsidian", manifest["modules"])
        targets = {e["target"] for e in manifest["files"]}
        self.assertTrue(OBSIDIAN_TARGETS <= targets)
        entry = next(e for e in manifest["files"] if e["target"] == "ai/modules.md")
        self.assertIn("## Events", entry["content"])
        self.assertIn("/ai/tmp/", manifest["ignore_lines"])

    def test_manifest_without_obsidian(self):
        manifest = build_manifest(ROOT, ["calendar", "core", "goals", "knowledge",
                                         "learning", "planning", "projects", "tasks"])
        targets = {e["target"] for e in manifest["files"]}
        self.assertFalse(OBSIDIAN_TARGETS & targets)

    def test_selection_persists_and_modules_md_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp) / "hub"
            hub.mkdir()
            install(hub, without=["obsidian"])
            installed = json.loads((hub / ".local/hub-release/installed.json").read_text())
            self.assertNotIn("obsidian", installed["modules"])
            self.assertIn("- core", (hub / "ai/modules.md").read_text())
            again = preview(ROOT, hub)
            self.assertEqual(again["modules"], installed["modules"])
            self.assertEqual({r["action"] for r in again["operations"]}, {"keep"})
            self.assertEqual(drift(ROOT, hub), {"conflicts": [], "unmanaged": []})

    def test_metadata_without_modules_key_means_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp) / "hub"
            hub.mkdir()
            install(hub)
            meta = hub / ".local/hub-release/installed.json"
            data = json.loads(meta.read_text())
            data.pop("modules")
            meta.write_text(json.dumps(data))
            self.assertIsNone(preview(ROOT, hub)["previous_modules"])
            self.assertIn("obsidian", preview(ROOT, hub)["modules"])

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp) / "hub"
            hub.mkdir()
            for kw in ({"without": ["tasks"]}, {"without": ["projects"]}, {"with_": ["nope"]}):
                with self.assertRaises(ValueError):
                    preview(ROOT, hub, **kw)

    def test_release_sources_cover_manifest(self):
        sources = set(release_sources(ROOT))
        for entry in build_manifest(ROOT)["files"]:
            if entry["source"] is not None:
                self.assertIn(entry["source"], sources)

    def test_obsidian_rules_command_matches_subscription(self):
        from scripts.module_passports import load_passports
        command = load_passports(ROOT)["obsidian"].subscribes["after-task-write"]
        self.assertIn(command, (ROOT / "modules/obsidian/rules.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
