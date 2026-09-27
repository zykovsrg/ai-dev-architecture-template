"""Synthetic fixtures only: never inspect the user's other projects or vault."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
_STAGE_DIR = None
GENERATOR = Path(os.environ["OBSIDIAN_GENERATOR"]) if os.environ.get("OBSIDIAN_GENERATOR") else None


def setUpModule():
    global _STAGE_DIR, GENERATOR
    if GENERATOR is not None:
        return
    _STAGE_DIR = tempfile.mkdtemp(dir="/private/tmp")
    subprocess.run(
        ["bash", str(ROOT / "modules/obsidian/tests/stage-scripts.sh"), _STAGE_DIR],
        check=True, capture_output=True, text=True, timeout=30)
    GENERATOR = Path(_STAGE_DIR) / "generate-obsidian-projects-kanban.sh"


def tearDownModule():
    if _STAGE_DIR:
        import shutil
        shutil.rmtree(_STAGE_DIR, ignore_errors=True)


class ScopedRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="scoped-obsidian-", dir="/private/tmp")
        self.addCleanup(self.temp.cleanup)
        self.hub = Path(self.temp.name)
        self.projects = self.hub / "projects"
        (self.hub / "ai/project-cards").mkdir(parents=True)
        (self.hub / "ai/archiprojects.md").write_text("# Archiprojects\n")
        self.registry = self.hub / "ai/project-registry.md"
        self.registry.write_text("# Projects\n")
        self.ids = ["ai-dev-architecture", "alpha", "beta"]
        for project in self.ids:
            self.add_project(project)
        self.scope = self.hub / "scope.txt"
        self.scope.write_text("\n".join(self.ids) + "\n")
        self.vault = self.projects / "ai-dev-architecture/obsidian-vault"
        self.views = self.vault / "Obsidian"
        self.views.mkdir(parents=True)
        self.manifest = self.views / "AI-Architecture.manifest.json"
        self.overview = self.views / "Projects-Overview.md"
        self.run_generator()
        self.scope.write_text("alpha\n")

    def add_project(self, project):
        memory = self.projects / project / "ai"
        memory.mkdir(parents=True)
        (memory / "current-task.md").write_text(
            f"Status: active\nTask ID: TASK-{project}-20260915-001\n\n## Goal\n\n{project} task\n")
        for name in ["future-tasks.md", "paused-tasks.md"]:
            (memory / name).write_text("# No tasks\n")
        (self.hub / f"ai/project-cards/{project}.md").write_text(
            f"Name: {project}\nprimary_archiproject: none\n")
        with self.registry.open("a") as handle:
            handle.write(f"\n## {project}\nName: {project}\nPath: {self.projects / project}\n"
                         f"Card: ai/project-cards/{project}.md\nStatus: active\n")

    def board(self, project):
        return self.views / f"Projects/{project}/Kanban.md"

    def run_generator(self, success=True, flags=None, env=None):
        result = subprocess.run(
            ["bash", str(GENERATOR), "--hub", str(self.hub), "--scope", str(self.scope),
             "--vault", str(self.vault)] + (flags or ["--write", "--refresh-from-architecture"]),
            capture_output=True, text=True, env={**os.environ, "SOURCE_DATE_EPOCH": "1700000000", **(env or {})},
            timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def snapshot(self):
        return {str(p.relative_to(self.views)): p.read_bytes() for p in self.views.rglob("*") if p.is_file()}

    def complete_alpha(self):
        task = self.projects / "alpha/ai/current-task.md"
        task.write_text(task.read_text().replace("Status: active", "Status: done").replace("alpha task", "alpha completed"))

    def test_single_project_preserves_other_boards_and_shared_entries(self):
        before = json.loads(self.manifest.read_text())
        overview_before = self.overview.read_text().splitlines()
        # A manual change elsewhere must neither block this refresh nor be read.
        self.board("beta").write_text("manual beta edit\n")
        beta_stat = self.board("beta").stat()
        self.complete_alpha()
        self.run_generator()
        self.assertIn("- [x] alpha completed", self.board("alpha").read_text())
        self.assertEqual(self.board("beta").read_text(), "manual beta edit\n")
        self.assertEqual(self.board("beta").stat().st_mtime_ns, beta_stat.st_mtime_ns)
        after = json.loads(self.manifest.read_text())
        for key, id_key in [("project_boards", "project_id"), ("tasks", "project_id"), ("sources", "id")]:
            self.assertEqual([r for r in before[key] if r[id_key] != "alpha"],
                             [r for r in after[key] if r[id_key] != "alpha"])
        self.assertEqual([r for r in overview_before if not r.startswith("| [[Projects/alpha/")],
                         [r for r in self.overview.read_text().splitlines() if not r.startswith("| [[Projects/alpha/")])
        self.assertEqual(after["views"]["projects_overview"]["sha256"], hashlib.sha256(self.overview.read_bytes()).hexdigest())
        alpha = next(r for r in after["project_boards"] if r["project_id"] == "alpha")
        self.assertEqual(alpha["sha256"], hashlib.sha256(self.board("alpha").read_bytes()).hexdigest())

    def test_unscoped_sources_cards_and_boards_are_not_opened(self):
        # FIFOs would hang any attempted read; the child has a strict timeout.
        # This also catches cleanup trying to hash an out-of-scope board.
        for project in ["beta", "ai-dev-architecture"]:
            paths = [self.projects / project / "ai" / name for name in
                     ["current-task.md", "future-tasks.md", "paused-tasks.md"]]
            paths += [self.hub / f"ai/project-cards/{project}.md", self.board(project)]
            for path in paths:
                path.unlink()
                os.mkfifo(path)
        self.complete_alpha()
        self.run_generator()
        self.assertIn("- [x] alpha completed", self.board("alpha").read_text())

    def test_manual_selected_board_and_overview_block_without_writes(self):
        for target in [self.board("alpha"), self.overview]:
            original = target.read_bytes()
            target.write_bytes(original + b"\nmanual edit\n")
            before = self.snapshot()
            result = self.run_generator(success=False)
            self.assertIn("proposal pending: manual", result.stderr)
            self.assertEqual(before, self.snapshot())
            target.write_bytes(original)

    def test_partial_refresh_cannot_migrate_v3(self):
        old = json.loads(self.manifest.read_text())
        old["format_version"] = 3
        self.manifest.write_text(json.dumps(old))
        before = self.snapshot()
        result = self.run_generator(success=False, flags=["--write", "--confirm-generated-write"])
        self.assertIn("partial refresh requires manifest v4", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_unregistered_duplicate_and_unsafe_scope_fail_without_writes(self):
        for scope in ["unknown\n", "alpha\nalpha\n", "../alpha\n", "\n"]:
            self.scope.write_text(scope)
            before = self.snapshot()
            self.run_generator(success=False)
            self.assertEqual(before, self.snapshot())

    def test_full_refresh_still_updates_all_and_detects_manual_edits(self):
        self.complete_alpha()
        self.scope.write_text("\n".join(self.ids) + "\n")
        self.run_generator()
        self.assertIn("- [x] alpha completed", self.board("alpha").read_text())
        self.assertEqual(len(json.loads(self.manifest.read_text())["project_boards"]), 3)
        self.board("beta").write_text("manual beta\n")
        before = self.snapshot()
        self.run_generator(success=False)
        self.assertEqual(before, self.snapshot())

    def test_partial_adds_new_project_without_removing_existing_entries(self):
        before = json.loads(self.manifest.read_text())
        self.add_project("new-project")
        self.scope.write_text("new-project\n")
        self.run_generator()
        after = json.loads(self.manifest.read_text())
        self.assertEqual(after["project_boards"][:3], before["project_boards"])
        self.assertTrue(self.board("new-project").is_file())
        self.assertEqual(self.overview.read_text().count("Projects/new-project/"), 1)

    def test_partial_without_previous_generated_views_initializes_only_scope(self):
        for path in [self.board("alpha"), self.manifest, self.overview]:
            path.unlink()
        beta = self.board("beta").read_bytes()
        self.run_generator()
        manifest = json.loads(self.manifest.read_text())
        self.assertEqual([r["project_id"] for r in manifest["project_boards"]], ["alpha"])
        self.assertEqual(self.board("beta").read_bytes(), beta)

    def test_partial_publication_rolls_back_each_failed_move(self):
        self.complete_alpha()
        fake_bin = self.hub / "fake-bin"
        fake_bin.mkdir()
        wrapper = fake_bin / "mv"
        wrapper.write_text('''#!/bin/sh
count=0
[ ! -f "$MOVE_COUNT" ] || count=$(cat "$MOVE_COUNT")
count=$((count + 1))
printf '%s' "$count" > "$MOVE_COUNT"
[ "$count" -ne "$FAIL_MOVE" ] || exit 91
exec /bin/mv "$@"
''')
        wrapper.chmod(0o755)
        counter = self.hub / "move-count"
        for fail_at in [1, 2, 3]:
            counter.unlink(missing_ok=True)
            before = self.snapshot()
            self.run_generator(success=False, env={"PATH": str(fake_bin) + ":" + os.environ["PATH"],
                               "MOVE_COUNT": str(counter), "FAIL_MOVE": str(fail_at)})
            self.assertEqual(before, self.snapshot())
            self.assertFalse(list(self.views.glob(".AI-Architecture*")))

    def test_selected_symlink_paths_and_outside_registration_are_rejected(self):
        target = self.board("alpha")
        original = target.read_bytes()
        target.unlink()
        target.symlink_to(self.board("beta"))
        before = self.snapshot()
        self.run_generator(success=False)
        self.assertEqual(before, self.snapshot())
        target.unlink()
        target.write_bytes(original)
        original_registry = self.registry.read_text()
        self.registry.write_text(original_registry.replace(str(self.projects / "alpha"), str(self.hub)))
        self.run_generator(success=False)
        self.registry.write_text(original_registry)
        current = self.projects / "alpha/ai/current-task.md"
        current.unlink()
        current.symlink_to(self.projects / "beta/ai/current-task.md")
        self.run_generator(success=False)

    def test_partial_refresh_replaces_only_selected_task_entries(self):
        before = json.loads(self.manifest.read_text())
        (self.projects / "alpha/ai/current-task.md").write_text("Status: empty\n")
        self.run_generator()
        after = json.loads(self.manifest.read_text())
        self.assertEqual(after["tasks"], [r for r in before["tasks"] if r["project_id"] != "alpha"])
        self.assertNotIn("^alpha--", self.board("alpha").read_text())
        self.assertEqual(self.overview.read_text().count("Projects/alpha/"), 1)

    def test_selected_preview_is_read_only(self):
        before = self.snapshot()
        result = self.run_generator(flags=["--preview"])
        self.assertIn("alpha task", result.stdout)
        self.assertNotIn("beta task", result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_ambiguous_shared_metadata_blocks_without_writes(self):
        invalid = json.loads(self.manifest.read_text())
        invalid["tasks"] = None
        self.manifest.write_text(json.dumps(invalid))
        invalid_snapshot = self.snapshot()
        self.run_generator(success=False)
        self.assertEqual(invalid_snapshot, self.snapshot())

    def test_confirmed_reverse_proposal_refreshes_only_selected_project(self):
        alpha = self.board("alpha")
        alpha.write_text(alpha.read_text().replace("alpha task", "renamed alpha task"))
        self.board("beta").write_text("manual beta edit\n")
        command = ["bash", str(GENERATOR.parent / "obsidian-task-sync.sh")]
        arguments = ["--project-id", "alpha", "--hub", str(self.hub), "--scope", str(self.scope),
                     "--vault", str(self.vault)]
        scan = subprocess.run(command + ["scan"] + arguments, capture_output=True, text=True, timeout=30)
        self.assertEqual(scan.returncode, 0, scan.stderr)
        proposal = self.vault / ".ai-architecture-sync/pending-proposal.json"
        payload = json.loads(proposal.read_text())
        apply = subprocess.run(command + ["apply"] + arguments + ["--confirm-proposal", payload["proposal_sha256"]],
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(apply.returncode, 0, apply.stderr)
        self.assertIn("renamed alpha task", (self.projects / "alpha/ai/current-task.md").read_text())
        self.assertIn("renamed alpha task", alpha.read_text())
        self.assertEqual(self.board("beta").read_text(), "manual beta edit\n")
        self.assertFalse(proposal.exists())

    def test_duplicate_overview_row_blocks_without_writes(self):
        row = next(line for line in self.overview.read_text().splitlines() if line.startswith("| [[Projects/alpha/"))
        self.overview.write_text(self.overview.read_text() + "\n" + row)
        manifest = json.loads(self.manifest.read_text())
        manifest["views"]["projects_overview"]["sha256"] = hashlib.sha256(self.overview.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps(manifest))
        invalid_snapshot = self.snapshot()
        self.run_generator(success=False)
        self.assertEqual(invalid_snapshot, self.snapshot())


if __name__ == "__main__":
    unittest.main()
