import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "scripts/update-installed-hub.sh"

PLANNING_REMOVED = {
    "ai/skills/hub-workflows/SKILL.md",
    "scripts/snapshot-calendar.sh",
    "scripts/calendar-context.py",
    "scripts/calendar_task_sync.py",
    "scripts/validate-day-plan-output.py",
    "ai/rules/planning.md",
}
CALENDAR_REMOVED = {"ai/skills/hub-calendar/SKILL.md"}


class PlanningCalendarSwitchTests(unittest.TestCase):
    def run_updater(self, hub, *args, env=None):
        import os
        full_env = dict(os.environ)
        if env:
            full_env.update(env)
        return subprocess.run(
            ["bash", str(UPDATER), "--source", str(ROOT), "--hub", str(hub), "--allow-dirty", *args],
            capture_output=True, text=True, check=False, env=full_env,
        )

    def plan_sha(self, output):
        return next(l.split(": ", 1)[1] for l in output.splitlines() if l.startswith("Plan SHA256: "))

    def installed_hub(self, root):
        hub = root / "_ai-hub"  # install-hub.sh requires this name and a symlink-free path
        import os
        env = dict(os.environ)
        env["HUB_CALENDAR_SKIP_BRIDGE"] = "1"
        env["HUB_CALENDAR_SKIP_VENV"] = "1"
        subprocess.run(["bash", str(ROOT / "scripts/install-hub.sh"), str(hub)],
                        check=True, capture_output=True, env=env)
        return hub

    def add_other_mcp_server(self, hub):
        mcp_path = hub / ".mcp.json"
        payload = {"mcpServers": {"other": {"command": "echo", "args": ["hi"]}}}
        mcp_path.write_text(json.dumps(payload), encoding="utf-8")

    def add_fixture_snapshot(self, hub):
        snapshots = hub / "ai/tmp/calendar-snapshots"
        snapshots.mkdir(parents=True, exist_ok=True)
        (snapshots / "2026-09-27-0900.md").write_text("09:00|10:00|demo|Personal\n", encoding="utf-8")

    def test_disable_then_enable_planning_and_calendar(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            self.add_other_mcp_server(hub)
            self.add_fixture_snapshot(hub)
            allowlist = hub / ".local/apple-calendar/allowlist.json"
            self.assertTrue(allowlist.exists())
            allowlist_before = allowlist.read_text()

            dry = self.run_updater(hub, "--dry-run", "--without", "planning", "--without", "calendar",
                                    env={"HUB_CALENDAR_SKIP_BRIDGE": "1", "HUB_CALENDAR_SKIP_VENV": "1"})
            self.assertEqual(dry.returncode, 0, dry.stderr)
            removed = {l.split(": ", 1)[1] for l in dry.stdout.splitlines() if l.startswith("remove: ")}
            self.assertTrue(PLANNING_REMOVED.issubset(removed), removed)
            self.assertTrue(CALENDAR_REMOVED.issubset(removed), removed)
            self.assertIn("Module change: -calendar -planning", dry.stdout)
            self.assertIn("Extra step: remove calendar server (tools/apple-calendar-policy, .mcp.json hub_calendar)",
                           dry.stdout)

            applied = self.run_updater(hub, "--apply", "--without", "planning", "--without", "calendar",
                                        "--confirm-plan", self.plan_sha(dry.stdout),
                                        env={"HUB_CALENDAR_SKIP_BRIDGE": "1", "HUB_CALENDAR_SKIP_VENV": "1"})
            self.assertEqual(applied.returncode, 0, applied.stderr)

            for target in PLANNING_REMOVED | CALENDAR_REMOVED:
                self.assertFalse((hub / target).exists(), target)
            self.assertFalse((hub / "tools/apple-calendar-policy").exists())

            mcp = json.loads((hub / ".mcp.json").read_text())
            self.assertNotIn("hub_calendar", mcp["mcpServers"])
            self.assertIn("other", mcp["mcpServers"])

            self.assertEqual(allowlist.read_text(), allowlist_before)
            self.assertEqual((hub / "ai/tmp/calendar-snapshots/2026-09-27-0900.md").read_text(),
                              "09:00|10:00|demo|Personal\n")

            modules_events = (hub / "ai/modules.md").read_text().split("## Events", 1)[1]
            before_write_section = modules_events.split("### before-task-write", 1)[1]
            before_write_section = before_write_section.split("###", 1)[0]
            self.assertNotIn("planning", before_write_section)

            self.assertTrue((hub / "ai/skills/hub-task-intake/SKILL.md").exists())

            drift = subprocess.run(["python3", str(ROOT / "scripts/hub_release.py"), "drift",
                                    "--source", str(ROOT), "--hub", str(hub)],
                                    capture_output=True, text=True)
            self.assertEqual(drift.returncode, 0, drift.stdout)

            # Restore both modules.
            dry = self.run_updater(hub, "--dry-run", "--with", "planning", "--with", "calendar",
                                    env={"HUB_CALENDAR_SKIP_BRIDGE": "1", "HUB_CALENDAR_SKIP_VENV": "1"})
            self.assertIn("Module change: +calendar +planning", dry.stdout)
            self.assertIn(
                "Extra step: refresh calendar server (tools/apple-calendar-policy, bridge rebuild, .mcp.json hub_calendar if missing)",
                dry.stdout,
            )
            applied = self.run_updater(hub, "--apply", "--with", "planning", "--with", "calendar",
                                        "--confirm-plan", self.plan_sha(dry.stdout),
                                        env={"HUB_CALENDAR_SKIP_BRIDGE": "1", "HUB_CALENDAR_SKIP_VENV": "1"})
            self.assertEqual(applied.returncode, 0, applied.stderr)

            for target in PLANNING_REMOVED | CALENDAR_REMOVED:
                self.assertTrue((hub / target).exists(), target)
            self.assertTrue((hub / "tools/apple-calendar-policy").is_dir())
            mcp = json.loads((hub / ".mcp.json").read_text())
            self.assertIn("hub_calendar", mcp["mcpServers"])
            self.assertIn("other", mcp["mcpServers"])
            self.assertEqual(mcp["mcpServers"]["hub_calendar"]["args"], ["-m", "hub_calendar_policy"])
            self.assertEqual(allowlist.read_text(), allowlist_before)

    def test_calendar_alone_cannot_be_disabled(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            result = self.run_updater(hub, "--dry-run", "--without", "calendar",
                                       env={"HUB_CALENDAR_SKIP_BRIDGE": "1", "HUB_CALENDAR_SKIP_VENV": "1"})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("calendar", result.stderr)

    def test_unchanged_selection_preview_still_shows_extra_step(self):
        # calendar is selected by default (fresh install); a preview with no
        # --with/--without at all must still describe the post-apply step,
        # because sync-calendar-policy.sh runs on every apply regardless of
        # whether the module selection changed.
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            dry = self.run_updater(hub, "--dry-run", env={"HUB_CALENDAR_SKIP_BRIDGE": "1", "HUB_CALENDAR_SKIP_VENV": "1"})
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertNotIn("Module change:", dry.stdout)
            self.assertIn(
                "Extra step: refresh calendar server (tools/apple-calendar-policy, bridge rebuild, .mcp.json hub_calendar if missing)",
                dry.stdout,
            )


class CalendarSyncScriptSafetyTests(unittest.TestCase):
    SYNC = ROOT / "modules/calendar/scripts/sync-calendar-policy.sh"

    def run_sync(self, hub, *args, env=None):
        import os
        full_env = dict(os.environ)
        full_env["HUB_CALENDAR_SKIP_BRIDGE"] = "1"
        full_env["HUB_CALENDAR_SKIP_VENV"] = "1"
        if env:
            full_env.update(env)
        return subprocess.run(
            ["bash", str(self.SYNC), "--source", str(ROOT), "--hub", str(hub), *args],
            capture_output=True, text=True, check=False, env=full_env,
        )

    def make_hub(self, root):
        hub = root / "_ai-hub"
        hub.mkdir()
        return hub

    def test_malformed_mcp_json_blocks_install_and_remove(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.make_hub(Path(tmp))
            mcp_path = hub / ".mcp.json"
            mcp_path.write_text("not json at all", encoding="utf-8")
            before = mcp_path.read_text()

            result = self.run_sync(hub)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not valid JSON", result.stderr)
            self.assertEqual(mcp_path.read_text(), before)
            self.assertFalse((hub / "tools").exists())

            dry = self.run_sync(hub, "--dry-run")
            self.assertNotEqual(dry.returncode, 0)
            self.assertIn("not valid JSON", dry.stderr)
            self.assertEqual(mcp_path.read_text(), before)

            result = self.run_sync(hub, "--remove")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not valid JSON", result.stderr)
            self.assertEqual(mcp_path.read_text(), before)

    def test_mcp_servers_not_an_object_blocks_install_and_remove(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.make_hub(Path(tmp))
            mcp_path = hub / ".mcp.json"
            mcp_path.write_text(json.dumps({"mcpServers": ["not", "a", "dict"]}), encoding="utf-8")
            before = mcp_path.read_text()

            result = self.run_sync(hub)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("mcpServers", result.stderr)
            self.assertEqual(mcp_path.read_text(), before)
            self.assertFalse((hub / "tools").exists())

            result = self.run_sync(hub, "--remove")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("mcpServers", result.stderr)
            self.assertEqual(mcp_path.read_text(), before)

    def test_symlinked_tool_dir_blocks_remove(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.make_hub(Path(tmp))
            outside = Path(tmp) / "outside-target"
            outside.mkdir()
            (outside / "marker.txt").write_text("do not delete me\n", encoding="utf-8")
            tools_dir = hub / "tools"
            tools_dir.mkdir()
            link = tools_dir / "apple-calendar-policy"
            link.symlink_to(outside)

            result = self.run_sync(hub, "--remove")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr)
            self.assertTrue(link.is_symlink())
            self.assertTrue((outside / "marker.txt").exists())


if __name__ == "__main__":
    unittest.main()
