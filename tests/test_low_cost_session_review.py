import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "modules/learning/skills/hub-session-review/SKILL.md"
FINISH = ROOT / "modules/tasks/skills/hub-task-finish/SKILL.md"
LEARNING = ROOT / "modules/learning/rules.md"


def section(text, heading):
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError(f"missing section: {heading}")
    return match.group(1)


def compact(text):
    return " ".join(text.split())


class LowCostSessionReviewTests(unittest.TestCase):
    def test_deterministic_validation_precedes_semantic_review(self):
        cost = compact(section(REVIEW.read_text(encoding="utf-8"), "Контроль затрат"))
        deterministic = cost.index("До любого вызова модели выполните детерминированные проверки")
        semantic = cost.index("Для смыслового разбора")
        self.assertLess(deterministic, semantic)

    def test_semantic_review_defaults_low_cost_and_escalates_conditionally(self):
        cost = compact(section(REVIEW.read_text(encoding="utf-8"), "Контроль затрат"))
        self.assertIn("по умолчанию используйте Luna", cost)
        self.assertRegex(
            cost,
            r"Используйте Terra, только если Luna .*неоднозначность.*существенный риск",
        )

    def test_review_keeps_evidence_bounded(self):
        review = compact(REVIEW.read_text(encoding="utf-8"))
        self.assertIn("минимальный доступный диапазон доказательств", review)
        self.assertIn("Никогда автоматически не расширяйте частичную историю", review)
        self.assertIn("читайте только выбранную сессию или диапазон", review)

    def test_closure_runs_checks_and_review_before_context_cleanup(self):
        finish = compact(FINISH.read_text(encoding="utf-8"))
        deterministic = finish.index("До любого вызова модели запустите детерминированные проверки записей задач и разборов")
        review = finish.index("запустите событие `before-task-close`")
        cleanup = finish.index("очистите `ai/current-task.md`", review)
        self.assertLess(deterministic, review)
        self.assertLess(review, cleanup)
        self.assertIn("Ошибка подписчика оставляет задачу открытой и сохраняет её контекст", finish)
        learning = compact(LEARNING.read_text(encoding="utf-8"))
        self.assertNotIn("## before-task-close", learning)
        self.assertIn("Закрытие задачи не запускает разбор сессии", learning)


if __name__ == "__main__":
    unittest.main()
