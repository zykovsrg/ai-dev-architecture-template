import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "scripts/update-installed-hub.sh"

REMOVED = {
    "knowledge": {
        "ai/rules/knowledge.md",
        "ai/skills/hub-knowledge-enable/SKILL.md",
        "ai/skills/hub-knowledge-capture/SKILL.md",
        "ai/skills/hub-knowledge-review/SKILL.md",
        "ai/skills/hub-info-update/SKILL.md",
    },
    "goals": {
        "ai/rules/goals.md",
        "ai/skills/hub-goal-progress/SKILL.md",
        "scripts/count-goal-progress.sh",
    },
    "learning": {
        "ai/rules/learning.md",
        "ai/skills/hub-session-review/SKILL.md",
        "ai/skills/hub-session-review/resources/review-template.md",
        "scripts/workflow_friction.py",
        "scripts/check-session-review.py",
        "scripts/check-workflow-memory.sh",
    },
}

USER_DATA = {
    "ai/goals.md": "# Goals\n\ncustom goal content\n",
    "ai/goal-log.md": "2026-09-27|demo-goal|1|note\n",
    "ai/workflow-observations.md": "2026-09-27|demo observation\n",
}


class OptionalModulesSwitchTests(unittest.TestCase):
    def run_updater(self, hub, *args, env=None):
        full_env = dict(os.environ)
        full_env["HUB_CALENDAR_SKIP_BRIDGE"] = "1"
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
        env = dict(os.environ)
        env["HUB_CALENDAR_SKIP_BRIDGE"] = "1"
        subprocess.run(["bash", str(ROOT / "scripts/install-hub.sh"), str(hub)],
                        check=True, capture_output=True, env=env)
        return hub

    def write_user_data(self, hub):
        for target, content in USER_DATA.items():
            (hub / target).write_text(content, encoding="utf-8")

    def assert_user_data_unchanged(self, hub):
        for target, content in USER_DATA.items():
            self.assertEqual((hub / target).read_text(), content, target)

    def test_disable_then_enable_each_module(self):
        for module_id in ("knowledge", "goals", "learning"):
            with self.subTest(module=module_id):
                with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
                    hub = self.installed_hub(Path(tmp))
                    self.write_user_data(hub)

                    dry = self.run_updater(hub, "--dry-run", "--without", module_id)
                    self.assertEqual(dry.returncode, 0, dry.stderr)
                    removed = {l.split(": ", 1)[1] for l in dry.stdout.splitlines() if l.startswith("remove: ")}
                    self.assertEqual(removed, REMOVED[module_id], removed)
                    self.assertIn(f"Module change: -{module_id}", dry.stdout)

                    applied = self.run_updater(hub, "--apply", "--without", module_id,
                                                "--confirm-plan", self.plan_sha(dry.stdout))
                    self.assertEqual(applied.returncode, 0, applied.stderr)

                    for target in REMOVED[module_id]:
                        self.assertFalse((hub / target).exists(), target)
                    self.assert_user_data_unchanged(hub)

                    modules_text = (hub / "ai/modules.md").read_text()
                    self.assertNotIn(module_id, modules_text.split("## Events", 1)[0])
                    events_text = modules_text.split("## Events", 1)[1]
                    self.assertNotIn(module_id, events_text)

                    drift = subprocess.run(["python3", str(ROOT / "scripts/hub_release.py"), "drift",
                                            "--source", str(ROOT), "--hub", str(hub)],
                                            capture_output=True, text=True)
                    self.assertEqual(drift.returncode, 0, drift.stdout)

                    dry = self.run_updater(hub, "--dry-run", "--with", module_id)
                    self.assertEqual(dry.returncode, 0, dry.stderr)
                    self.assertIn(f"Module change: +{module_id}", dry.stdout)
                    applied = self.run_updater(hub, "--apply", "--with", module_id,
                                                "--confirm-plan", self.plan_sha(dry.stdout))
                    self.assertEqual(applied.returncode, 0, applied.stderr)

                    for target in REMOVED[module_id]:
                        self.assertTrue((hub / target).exists(), target)
                    self.assert_user_data_unchanged(hub)

    def test_goals_and_learning_removable_with_planning_installed(self):
        # planning only "uses if present" goals and learning (not a hard Depends),
        # so removing them must be allowed while planning stays selected.
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            self.assertTrue((hub / "ai/skills/hub-workflows/SKILL.md").exists())

            dry = self.run_updater(hub, "--dry-run", "--without", "goals", "--without", "learning")
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertIn("Module change: -goals -learning", dry.stdout)

            applied = self.run_updater(hub, "--apply", "--without", "goals", "--without", "learning",
                                        "--confirm-plan", self.plan_sha(dry.stdout))
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertTrue((hub / "ai/skills/hub-workflows/SKILL.md").exists())
            for target in REMOVED["goals"] | REMOVED["learning"]:
                self.assertFalse((hub / target).exists(), target)

    def test_all_three_removed_at_once_leaves_no_trace_in_remaining_skills(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            dry = self.run_updater(hub, "--dry-run", "--without", "knowledge",
                                    "--without", "goals", "--without", "learning")
            self.assertEqual(dry.returncode, 0, dry.stderr)
            applied = self.run_updater(hub, "--apply", "--without", "knowledge",
                                        "--without", "goals", "--without", "learning",
                                        "--confirm-plan", self.plan_sha(dry.stdout))
            self.assertEqual(applied.returncode, 0, applied.stderr)

            for target in REMOVED["knowledge"] | REMOVED["goals"] | REMOVED["learning"]:
                self.assertFalse((hub / target).exists(), target)

            skills_dir = hub / "ai/skills"
            remaining = "\n".join(p.read_text(encoding="utf-8") for p in skills_dir.rglob("SKILL.md"))
            removed_skill_names = {"hub-knowledge-enable", "hub-knowledge-capture", "hub-knowledge-review",
                                    "hub-info-update", "hub-goal-progress", "hub-session-review"}
            for name in removed_skill_names:
                self.assertNotIn(name, remaining)

            modules_text = (hub / "ai/modules.md").read_text()
            for module_id in ("knowledge", "goals", "learning"):
                self.assertNotIn(module_id, modules_text)

            # Widened scan: a surviving module (e.g. planning, which only
            # "uses if present" goals/learning) may still legitimately mention
            # a removed module's skill or script name in its own resources —
            # but only inside a paragraph that also guards on that module's
            # presence in `ai/modules.md` (the existing
            # "only when `learning` is listed in `ai/modules.md`" pattern).
            # Rule, kept deliberately simple: split every remaining text file
            # into blank-line-separated paragraphs; any paragraph naming a
            # removed identifier must, in that same paragraph, contain both
            # the backtick-quoted module id and the phrase
            # "listed in `ai/modules.md`". This catches the exact planning
            # bug (unconditional mentions of goal/learning machinery) while
            # tolerating guarded mentions and generic English use of common
            # words like "goals"/"learning" that don't sit next to a removed
            # identifier at all.
            removed_identifiers = {
                "knowledge": ["hub-knowledge-enable", "hub-knowledge-capture", "hub-knowledge-review",
                              "hub-info-update"],
                "goals": ["hub-goal-progress", "count-goal-progress.sh"],
                "learning": ["hub-session-review", "workflow_friction.py", "check-session-review.py",
                             "check-workflow-memory.sh"],
            }
            text_suffixes = (".md", ".sh", ".py")
            scan_roots = (hub / "ai/skills", hub / "ai/rules", hub / "scripts")
            violations = []
            for scan_root in scan_roots:
                if not scan_root.is_dir():
                    continue
                for path in sorted(scan_root.rglob("*")):
                    if not path.is_file() or path.suffix not in text_suffixes:
                        continue
                    try:
                        text = path.read_text(encoding="utf-8")
                    except (UnicodeDecodeError, OSError):
                        continue
                    for module_id, identifiers in removed_identifiers.items():
                        for paragraph in text.split("\n\n"):
                            for identifier in identifiers:
                                if identifier not in paragraph:
                                    continue
                                guarded = (f"`{module_id}`" in paragraph
                                           and "listed in `ai/modules.md`" in paragraph)
                                if not guarded:
                                    violations.append(
                                        f"{path.relative_to(hub)}: {identifier!r} unguarded for {module_id!r}")
            self.assertEqual(violations, [], "\n".join(violations))


if __name__ == "__main__":
    unittest.main()
