"""Проверки командных границ маршрутизации на выдуманном временном Хабе.

Они проверяют сценарии, а не способность модели запрашивать подтверждение.
Ни один сценарий не получает путь к рабочему Хабу или настоящему проекту.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "modules/core/scripts"


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class RoutingSafetyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="routing-safety-", dir="/private/tmp")
        self.addCleanup(temporary.cleanup)
        self.hub = Path(temporary.name) / "hub"
        self.project = self.hub / "projects/fictional"
        self.registry = self.hub / "ai/project-registry.md"
        self.card = self.hub / "ai/project-cards/fictional.md"
        write(self.hub / "ai/allowed-roots.md", f"- {self.hub}/projects\n")
        write(self.hub / "ai/archiprojects.md", "# Archiprojects\n")
        self.memory(self.project)
        write(self.registry,
              "# Project Registry\n\n## fictional\nName: Fictional\nType: project\n"
              f"Status: active\nPath: {self.project}\nTags: fixture\n"
              "Card: ai/project-cards/fictional.md\n")
        write(self.card,
              "# Project Card\nProject ID: fictional\nName: Fictional\nType: project\n"
              "Status: active\nLast updated: 2026-10-16\nPurpose: Synthetic fixture.\n"
              f"Typical tasks: fixture.\nMemory entry point: {self.project}/ai/current-task.md\n"
              "primary_archiproject: none\n")

    def memory(self, project):
        for name in ("current-task", "paused-tasks", "future-tasks", "project-context", "decisions", "changelog"):
            write(project / "ai" / f"{name}.md", "Synthetic memory.\n")

    def run_script(self, name, *options):
        return subprocess.run(["bash", str(SCRIPTS / name), str(self.hub), *options],
                              capture_output=True, text=True, timeout=15)

    def reject(self, name, message):
        result = self.run_script(name)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(message, result.stderr)
        if name == "read-compact-project-index.sh":
            self.assertEqual(result.stdout, "", "Нельзя выпускать частичный указатель после ошибки")

    def test_valid_registry_and_compact_index(self):
        result = self.run_script("check-hub-registry.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Registry check passed: 1 projects", result.stdout)
        result = self.run_script("read-compact-project-index.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "project_id\tname\ttags\tstatus\tpurpose_brief\tgroup\n"
                         "fictional\tFictional\tfixture\tactive\tSynthetic fixture.\tnone\n")

    def test_selected_registry_check_skips_other_project_cards(self):
        original = self.registry.read_text()
        write(self.registry, original + "\n## retired\nName: Retired\nType: project\n"
              "Status: archived\nPath: /unread-archive\nTags: fixture\n"
              "Card: ai/project-cards/retired.md\n")
        result = self.run_script("check-hub-registry.sh", "--project", "fictional")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("selected project fictional", result.stdout)
        # Выбранный проект всё ещё проходит полную проверку границ.
        write(self.card, self.card.read_text().replace(str(self.project), "/external"))
        result = self.run_script("check-hub-registry.sh", "--project", "fictional")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Memory entry point", result.stderr)

    def test_selected_registry_check_rejects_missing_archive_directory(self):
        write(self.registry, self.registry.read_text().replace("Status: active", "Status: archived"))
        write(self.card, self.card.read_text().replace("Status: active", "Status: archived"))
        import shutil
        shutil.rmtree(self.project)
        result = self.run_script("check-hub-registry.sh", "--project", "fictional")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("selected project directory is missing", result.stderr)

    def test_selected_registry_check_rejects_missing_project(self):
        result = self.run_script("check-hub-registry.sh", "--project", "unknown")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("selected project not found", result.stderr)

    def test_allowed_root_must_be_exact_hub_projects(self):
        for root in (self.hub.parent / "external", self.hub / "projects/nested"):
            with self.subTest(root=root.name):
                root.mkdir(parents=True, exist_ok=True)
                write(self.hub / "ai/allowed-roots.md", f"- {root}\n")
                self.reject("check-hub-registry.sh", "allowed root must be exactly the canonical projects root")

    def test_registered_project_must_be_direct_child(self):
        original_registry = self.registry.read_text()
        original_card = self.card.read_text()
        for project in (self.hub.parent / "external", self.project / "nested"):
            with self.subTest(project=project.name):
                self.memory(project)
                write(self.registry, original_registry.replace(str(self.project), str(project)))
                write(self.card, original_card.replace(str(self.project), str(project)))
                self.reject("check-hub-registry.sh", "project path must be a direct child")

    def test_card_memory_cannot_point_to_another_project(self):
        other = self.hub / "projects/other-fictional"
        self.memory(other)
        write(self.card, self.card.read_text().replace(str(self.project), str(other)))
        self.reject("check-hub-registry.sh", "Memory entry point must stay beneath the registered project")

    def test_symlink_card_is_rejected_by_both_commands(self):
        target = self.hub / "ai/copy.md"
        write(target, self.card.read_text())
        self.card.unlink()
        self.card.symlink_to(target)
        self.reject("check-hub-registry.sh", "card path must stay beneath ai/project-cards")
        self.reject("read-compact-project-index.sh", "symlink is not allowed")

    def test_registry_rejects_duplicate_scalar_fields(self):
        # Две корректные записи также проверяют сброс счётчиков на новом ##.
        other = self.hub / "projects/fictional-two"
        self.memory(other)
        write(self.hub / "ai/project-cards/fictional-two.md",
              self.card.read_text().replace("fictional", "fictional-two"))
        second = self.registry.read_text().split("## fictional\n", 1)[1]
        second = "## fictional-two\n" + second.replace("fictional", "fictional-two")
        original = self.registry.read_text() + "\n" + second
        write(self.registry, original)
        result = self.run_script("check-hub-registry.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        for field in ("Name", "Type", "Status", "Path", "Tags", "Card"):
            for ending in ("\n", ""):
                with self.subTest(field=field, final_newline=bool(ending)):
                    line = next(line for line in second.splitlines() if line.startswith(field + ": "))
                    try:
                        write(self.registry, original + line + ending)
                        self.reject("check-hub-registry.sh", "duplicate " + field + " for fictional-two")
                    finally:
                        write(self.registry, original)

    def test_compact_index_rejects_missing_metadata(self):
        for path, field, value in ((self.registry, "Name", "Fictional"),
                                   (self.registry, "Tags", "fixture"),
                                   (self.registry, "Status", "active"),
                                   (self.card, "Purpose", "Synthetic fixture.")):
            with self.subTest(field=field):
                original = path.read_text()
                try:
                    write(path, original.replace(f"{field}: {value}\n", ""))
                    self.reject("read-compact-project-index.sh", field)
                finally:
                    write(path, original)

    def test_compact_index_rejects_duplicate_metadata(self):
        for path, field, value in ((self.registry, "Name", "Fictional"),
                                   (self.registry, "Tags", "fixture"),
                                   (self.registry, "Status", "active"),
                                   (self.card, "Purpose", "Synthetic fixture."),
                                   (self.card, "primary_archiproject", "none")):
            with self.subTest(field=field):
                original = path.read_text()
                try:
                    write(path, original + f"{field}: {value}\n")
                    self.reject("read-compact-project-index.sh", field)
                finally:
                    write(path, original)


if __name__ == "__main__":
    unittest.main()
