import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "hub-template/ai/skills/hub-workflows/SKILL.md"
LIFECYCLE = ROOT / "hub-template/ai/skills/hub-workflows/resources/learning-lifecycle.md"
LEARNING_ACTIONS = {"goal_progress", "add_observation", "promote_rule", "retire_rule"}
EXPECTED_INVARIANTS = {
    "proposal_display": "pending",
    "accepted": "journal_append -> resolve_accepted",
    "rejected": "no_journal_append -> resolve_rejected",
    "append_failure": "pending",
}


def lifecycle_invariants():
    values = {}
    for line in LIFECYCLE.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"- `([a-z_]+): (.+)`", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


class HubLearningContractTests(unittest.TestCase):
    def test_proposal_actions_cover_learning_lifecycle(self):
        text = SKILL.read_text(encoding="utf-8")
        match = re.search(r"^action: <([^>]+)>$", text, re.MULTILINE)
        self.assertIsNotNone(match, "canonical proposal action enum is missing")
        declared = set(match.group(1).split("|"))
        self.assertTrue(LEARNING_ACTIONS <= declared, LEARNING_ACTIONS - declared)

    def test_learning_state_machine_has_stable_invariants(self):
        self.assertEqual(lifecycle_invariants(), EXPECTED_INVARIANTS)

    def test_learning_resolution_contract_is_centralized(self):
        core = SKILL.read_text(encoding="utf-8")
        lifecycle = LIFECYCLE.read_text(encoding="utf-8")
        self.assertIn("resources/learning-lifecycle.md", core)
        self.assertIn("source-id: <ID>", lifecycle)
        self.assertEqual(lifecycle_invariants()["proposal_display"], "pending")
        self.assertEqual(lifecycle_invariants()["append_failure"], "pending")
        self.assertLess(
            lifecycle_invariants()["accepted"].index("journal_append"),
            lifecycle_invariants()["accepted"].index("resolve_accepted"),
        )
        self.assertTrue(lifecycle_invariants()["rejected"].startswith("no_journal_append"))

    def test_referenced_learning_actions_are_declared(self):
        text = SKILL.read_text(encoding="utf-8")
        match = re.search(r"^action: <([^>]+)>$", text, re.MULTILINE)
        self.assertIsNotNone(match)
        declared = set(match.group(1).split("|"))
        referenced = set(re.findall(r"`(goal_progress|add_observation|promote_rule|retire_rule)`", text))
        self.assertEqual(referenced, LEARNING_ACTIONS)
        self.assertTrue(referenced <= declared, referenced - declared)


if __name__ == "__main__":
    unittest.main()
