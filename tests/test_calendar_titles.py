import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from modules.projects.scripts.archiprojects import calendar_title, parse_groups, read_cards, resolve_title, validate

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "modules" / "projects" / "scripts" / "archiprojects.py"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def group(gid, name, parent=None, calendar=None):
    lines = [f"## {gid}", "```yaml", f"id: {gid}", f"name: {name}", "status: active", "kind: group"]
    if parent:
        lines.append(f"parent: {parent}")
    if calendar:
        lines.append(f"calendar_name: {calendar}")
    return "\n".join(lines + ["```", ""])


def card(project_id, primary="none", calendar=None):
    text = f"# Card\nProject ID: {project_id}\nName: {project_id}\nStatus: active\nprimary_archiproject: {primary}\n"
    if calendar:
        text += f"Calendar name: {calendar}\n"
    return text


def make_hub(tmp):
    hub = Path(tmp) / "hub"
    write(hub / "ai/archiprojects.md", "# Archiprojects\n\n## Schema\n\n"
          + group("hadassah", "Хадасса", calendar="хадасса")
          + group("hadassah-promo", "Промо", parent="hadassah", calendar="промостраницы")
          + group("dela", "Дела"))
    cards = {
        "release-page-varicocele": card("release-page-varicocele", "hadassah-promo", "варикоцеле"),
        "promo-pages": card("promo-pages", "hadassah-promo", "—"),
        "rutina-i-byt": card("rutina-i-byt", "dela", "дела"),
        "zdorove": card("zdorove", "none", "здоровье"),
        "legacy": card("legacy", "dela"),
    }
    for pid, text in cards.items():
        write(hub / f"ai/project-cards/{pid}.md", text)
    return hub


def load(hub):
    return parse_groups(hub / "ai/archiprojects.md"), read_cards(hub)


class CalendarTitles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hub = make_hub(self.tmp.name)
        self.groups, self.cards = load(self.hub)

    def tearDown(self):
        self.tmp.cleanup()

    def title(self, pid, task):
        return calendar_title(self.groups, self.cards, pid, task)

    def resolve(self, title):
        return resolve_title(self.groups, self.cards, title)

    def test_nested_chain(self):
        self.assertEqual(self.title("release-page-varicocele", "Доработать текст"),
                         "хадасса/промостраницы/варикоцеле/доработать текст")

    def test_group_without_calendar_name_uses_lowercase_name(self):
        self.assertEqual(self.title("rutina-i-byt", "Купить пылесос"), "дела/дела/купить пылесос")

    def test_project_without_archiproject_has_no_prefix(self):
        self.assertEqual(self.title("zdorove", "Измерять давление"), "здоровье/измерять давление")

    def test_card_without_calendar_name_falls_back_to_id(self):
        self.assertEqual(self.title("legacy", "x"), "дела/legacy/x")

    def test_unknown_project_raises(self):
        with self.assertRaises(KeyError):
            self.title("nope", "x")

    def test_resolve_nested(self):
        self.assertEqual(self.resolve("хадасса/промостраницы/варикоцеле/доработать текст"),
                         ("release-page-varicocele", "доработать текст"))

    def test_resolve_is_case_insensitive_and_keeps_slashes_in_task(self):
        self.assertEqual(self.resolve("Хадасса/Промостраницы/Варикоцеле/a/b"), ("release-page-varicocele", "a/b"))

    def test_project_named_like_its_group_is_not_repeated(self):
        self.assertEqual(self.title("promo-pages", "Встреча с Шелунцовым"), "хадасса/промостраницы/встреча с шелунцовым")
        self.assertEqual(self.resolve("хадасса/промостраницы/встреча с шелунцовым"),
                         ("promo-pages", "встреча с шелунцовым"))

    def test_resolve_without_archiproject(self):
        self.assertEqual(self.resolve("здоровье/измерять давление"), ("zdorove", "измерять давление"))

    def test_resolve_legacy_project_id_title(self):
        self.assertEqual(self.resolve("хадасса/release-page-varicocele/написать текст"),
                         ("release-page-varicocele", "написать текст"))

    def test_group_general_project_needs_a_group(self):
        write(self.hub / "ai/project-cards/orphan.md", card("orphan", "none", "—"))
        self.assertTrue(any("needs an archiproject" in e for e in validate(self.hub)))

    def test_resolve_unknown_or_empty_task(self):
        self.assertIsNone(self.resolve("хадасса/неизвестно/x"))
        self.assertIsNone(self.resolve("хадасса/промостраницы/варикоцеле/"))
        self.assertIsNone(self.resolve("просто событие"))

    def test_round_trip_for_every_card(self):
        for c in self.cards:
            pid = c["project_id"]
            self.assertEqual(self.resolve(self.title(pid, "задача")), (pid, "задача"))

    def test_validate_rejects_duplicate_chains(self):
        write(self.hub / "ai/project-cards/dup.md", card("dup", "hadassah-promo", "варикоцеле"))
        self.assertTrue(any("calendar title" in e for e in validate(self.hub)))

    def test_validate_rejects_slash_in_calendar_name(self):
        write(self.hub / "ai/project-cards/bad.md", card("bad", "dela", "a/b"))
        self.assertTrue(any("calendar name" in e for e in validate(self.hub)))

    def test_cli_title_and_resolve(self):
        out = subprocess.run([sys.executable, str(SCRIPT), "calendar-title", "--hub", str(self.hub),
                              "--project", "zdorove", "--task", "Давление"], capture_output=True, text=True)
        self.assertEqual((out.returncode, out.stdout.strip()), (0, "здоровье/давление"))
        out = subprocess.run([sys.executable, str(SCRIPT), "resolve-title", "--hub", str(self.hub),
                              "--title", "дела/дела/пылесос"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)
        self.assertIn('"rutina-i-byt"', out.stdout)


if __name__ == "__main__":
    unittest.main()
