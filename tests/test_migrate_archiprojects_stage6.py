import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "migrate-archiprojects-stage6.py"

ARCHIPROJECTS_TEXT = """# Archiprojects

This is the canonical hub-owned archiproject registry, not a parallel task
store. Project/task files remain canonical for project work.

## Schema

Use one human heading and one fenced YAML block for each concrete entry.

## <archiproject-id>

```yaml
id: <archiproject-id>
name: <human name>
status: <status>
kind: group
```

## <archiproject-id>

```yaml
id: <archiproject-id>
name: <human name>
status: <status>
kind: goal
target: <target>
unit: <unit>
due: YYYY-MM-DD or none
```

## hadassah

```yaml
id: hadassah
name: Хадасса
status: active
kind: group
```

## hadassah-promo-32-aug-sep

```yaml
id: hadassah-promo-32-aug-sep
name: 32 промо-страницы за август-сентябрь
status: active
kind: goal
target: 32
unit: pages
due: 2026-09-30
```

## seo-pages-80-sep

```yaml
id: seo-pages-80-sep
name: 80 SEO-страниц за сентябрь
status: active
kind: goal
target: 80
unit: pages
due: 2026-09-30
```
"""


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def card(project_id, name, purpose, primary="hadassah", extra=""):
    return (
        f"# {name}\n"
        f"Project ID: {project_id}\n"
        f"Name: {name}\n"
        "Type: workspace\n"
        "Status: active\n"
        f"Purpose: {purpose}\n"
        "Memory entry point: /tmp/x\n"
        f"primary_archiproject: {primary}\n"
        f"{extra}"
    )


def make_fixture(tmp):
    hub = Path(tmp) / "_ai-hub"
    write(hub / "ai" / "archiprojects.md", ARCHIPROJECTS_TEXT)
    cards = {
        "promo-pages": card("promo-pages", "Промо-страницы", "Готовить промо.", extra="archiproject_contribution: none\nrelated_archiprojects: hadassah-promo-32-aug-sep\n"),
        "release-page-cardiology-center": card("release-page-cardiology-center", "Релиз страницы кардиологии", "Выпустить страницу.", extra="archiproject_contribution: none\nrelated_archiprojects: hadassah-promo-32-aug-sep\n"),
        "stranitsa-stomatologii": card("stranitsa-stomatologii", "Страница стоматологии", "Выпустить страницу.", primary="none"),
        "hadassah-seo-analytics": card("hadassah-seo-analytics", "SEO-аналитика", "Свод SEO-аналитики.", extra="archiproject_contribution: none\nrelated_archiprojects: none\n"),
        "hadassah-seo-tech": card("hadassah-seo-tech", "Hadassah SEO Tech", "Техническое SEO."),
        "hadassah-content": card("hadassah-content", "Hadassah Content", "Обычный контент клиники."),
        "unrelated-project": card("unrelated-project", "Другой проект", "Не хадасса.", primary="none"),
    }
    for project_id, text in cards.items():
        write(hub / "ai" / "project-cards" / f"{project_id}.md", text)
    return hub


class MigrationTests(unittest.TestCase):
    def test_dry_run_reports_changes_and_writes_nothing(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_fixture(tmp)
            before = (hub / "ai" / "archiprojects.md").read_text(encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--hub", str(hub), "--dry-run"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("promo projects: 3", result.stdout)
            self.assertIn("hadassah-seo-analytics", result.stdout)
            self.assertIn("hadassah-seo-tech", result.stdout)
            self.assertNotIn("hadassah-content\n", result.stdout.split("seo projects:")[-1])
            after = (hub / "ai" / "archiprojects.md").read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertFalse((hub / "ai" / "goals.md").exists())

    def test_apply_moves_goals_and_sets_cards_then_validates(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_fixture(tmp)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--hub", str(hub), "--apply"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("archiprojects: ok", result.stdout)

            archi_text = (hub / "ai" / "archiprojects.md").read_text(encoding="utf-8")
            self.assertNotIn("hadassah-promo-32-aug-sep", archi_text)
            self.assertNotIn("seo-pages-80-sep", archi_text)
            self.assertIn("hadassah-promo", archi_text)
            self.assertIn("hadassah-seo", archi_text)

            goals_text = (hub / "ai" / "goals.md").read_text(encoding="utf-8")
            self.assertIn("group: hadassah-promo", goals_text)
            self.assertIn("group: hadassah-seo", goals_text)

            promo_card = (hub / "ai" / "project-cards" / "promo-pages.md").read_text(encoding="utf-8")
            self.assertIn("primary_archiproject: hadassah-promo", promo_card)
            self.assertNotIn("archiproject_contribution", promo_card)
            self.assertNotIn("related_archiprojects", promo_card)

            release_card = (hub / "ai" / "project-cards" / "release-page-cardiology-center.md").read_text(encoding="utf-8")
            self.assertIn("primary_archiproject: hadassah-promo", release_card)

            stomat_card = (hub / "ai" / "project-cards" / "stranitsa-stomatologii.md").read_text(encoding="utf-8")
            self.assertIn("primary_archiproject: hadassah-promo", stomat_card)

            seo_card = (hub / "ai" / "project-cards" / "hadassah-seo-analytics.md").read_text(encoding="utf-8")
            self.assertIn("primary_archiproject: hadassah-seo", seo_card)
            self.assertNotIn("archiproject_contribution", seo_card)

            seo_tech_card = (hub / "ai" / "project-cards" / "hadassah-seo-tech.md").read_text(encoding="utf-8")
            self.assertIn("primary_archiproject: hadassah-seo", seo_tech_card)

            content_card = (hub / "ai" / "project-cards" / "hadassah-content.md").read_text(encoding="utf-8")
            self.assertIn("primary_archiproject: hadassah", content_card)

            unrelated_card = (hub / "ai" / "project-cards" / "unrelated-project.md").read_text(encoding="utf-8")
            self.assertIn("primary_archiproject: none", unrelated_card)

    def test_apply_is_idempotent(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_fixture(tmp)
            subprocess.run([sys.executable, str(SCRIPT), "--hub", str(hub), "--apply"], capture_output=True, text=True, check=True)
            archi_after_first = (hub / "ai" / "archiprojects.md").read_text(encoding="utf-8")
            goals_after_first = (hub / "ai" / "goals.md").read_text(encoding="utf-8")
            cards_after_first = {
                p.name: p.read_text(encoding="utf-8")
                for p in sorted((hub / "ai" / "project-cards").glob("*.md"))
            }

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--hub", str(hub), "--apply"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("archiprojects: ok", result.stdout)

            self.assertEqual(archi_after_first, (hub / "ai" / "archiprojects.md").read_text(encoding="utf-8"))
            self.assertEqual(goals_after_first, (hub / "ai" / "goals.md").read_text(encoding="utf-8"))
            cards_after_second = {
                p.name: p.read_text(encoding="utf-8")
                for p in sorted((hub / "ai" / "project-cards").glob("*.md"))
            }
            self.assertEqual(cards_after_first, cards_after_second)

    def test_unknown_goal_id_aborts_with_no_writes(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_fixture(tmp)
            bad_text = ARCHIPROJECTS_TEXT.replace("seo-pages-80-sep", "mystery-goal")
            write(hub / "ai" / "archiprojects.md", bad_text)
            before = bad_text
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--hub", str(hub), "--apply"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("mystery-goal", result.stderr)
            after = (hub / "ai" / "archiprojects.md").read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertFalse((hub / "ai" / "goals.md").exists())

if __name__ == "__main__":
    unittest.main()
