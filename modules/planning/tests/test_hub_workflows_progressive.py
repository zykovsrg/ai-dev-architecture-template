import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
SKILL = ROOT / "skills/hub-workflows/SKILL.md"
RESOURCE_DIR = SKILL.parent / "resources"
RESOURCES = {
    "day-plan": "day-plan.md",
    "evening-review": "evening-review.md",
    "weekly-review": "weekly-review.md",
}


class HubWorkflowProgressiveDisclosureTests(unittest.TestCase):
    def test_scenario_resources_exist_and_are_referenced(self):
        core = SKILL.read_text(encoding="utf-8")
        for scenario, filename in RESOURCES.items():
            path = RESOURCE_DIR / filename
            self.assertTrue(path.is_file(), filename)
            self.assertIn(f"resources/{filename}", core)
            text = path.read_text(encoding="utf-8")
            self.assertIn("core `SKILL.md`", text)
            self.assertIn(scenario, text)

    def test_common_authority_stays_in_core(self):
        core = SKILL.read_text(encoding="utf-8")
        for phrase in (
            "## Фиксированная последовательность",
            "правилам подтверждения записи",
            "`hub-task-overview`",
        ):
            self.assertIn(phrase, core)
        overview = (REPO_ROOT / "modules/tasks/skills/hub-task-overview/SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "## Пределы личного помощника",
            "## Оболочка предложения",
            "## Граница записи",
            "правилам подтверждения записи",
            "scripts/read-compact-task-index.py",
            "resources/capture.md",
        ):
            self.assertIn(phrase, overview)
        self.assertTrue((REPO_ROOT / "modules/tasks/skills/hub-task-overview/resources/capture.md").is_file())

    def test_detailed_scenario_formats_leave_core(self):
        core = SKILL.read_text(encoding="utf-8")
        for phrase in (
            "### Day plan format",
            "### Evening review format",
            "### Weekly review format",
            "## Capture rules",
            "## Текущий календарь",
            "## Сегодняшний календарь",
            "## Архипроекты",
        ):
            self.assertNotIn(phrase, core)

    def test_learning_state_machine_stays_in_its_resource(self):
        core = SKILL.read_text(encoding="utf-8")
        evening = (RESOURCE_DIR / "evening-review.md").read_text(encoding="utf-8")
        lifecycle = (RESOURCE_DIR / "learning-lifecycle.md").read_text(encoding="utf-8")
        self.assertIn("resources/learning-lifecycle.md", core)
        self.assertIn("не вызывает редакционное обучение или `resources/learning-lifecycle.md`", evening)
        for invariant in ("accepted: journal_append", "rejected: no_journal_append", "append_failure: pending"):
            self.assertIn(invariant, lifecycle)
            self.assertNotIn(invariant, evening)

    def test_dated_day_plan_actions_pair_task_and_timed_event(self):
        day_plan = " ".join((RESOURCE_DIR / "day-plan-legacy.md").read_text(encoding="utf-8").split())
        for phrase in (
            "относительными и явными датами",
            "свободный 30-минутный интервал",
            "Запланировано: YYYY-MM-DD HH:MM-HH:MM",
            "Явный интервал сохраняйте без изменений",
            "Прошлая дата не означает завершение",
            "записывайте событие вместе с задачей",
        ):
            self.assertIn(phrase, day_plan)

    def test_day_plan_and_evening_review_keep_calendar_titles_and_day_scope(self):
        required = (
            "весь день",
            "Сохраняйте названия дословно",
            "не сокращайте, не переводите, не объединяйте и не пересказывайте",
        )
        for filename in ("day-plan.md", "evening-review.md"):
            text = " ".join((RESOURCE_DIR / filename).read_text(encoding="utf-8").split())
            for phrase in required:
                self.assertIn(phrase, text, f"{filename}: {phrase}")

            if filename == "day-plan.md":
                self.assertIn("утром не показывайте; не удаляйте", text)
            else:
                self.assertRegex(text.lower(), r"каждое целодневное(?: событие(?: показывайте)?)? отдельно")

    def test_day_plan_and_evening_review_require_exact_task_sync(self):
        required = (
            "update_task",
            "update_due",
            "update_waiting",
            "путь цели",
            "различия",
            "неоднозначн",
        )
        for filename in ("day-plan.md", "evening-review.md"):
            text = " ".join((RESOURCE_DIR / filename).read_text(encoding="utf-8").split())
            for phrase in required:
                self.assertIn(phrase.casefold(), text.casefold(), f"{filename}: {phrase}")

    def test_architecture_requires_task_diff_before_workflow_sync(self):
        rules = " ".join((REPO_ROOT / "modules/planning/rules.md").read_text(encoding="utf-8").split())
        self.assertIn("События календаря никогда не доказывают завершение", rules)
        self.assertIn("сразу применяется к канонической записи", rules)


if __name__ == "__main__":
    unittest.main()
