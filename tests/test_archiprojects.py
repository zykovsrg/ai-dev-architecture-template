import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from modules.projects.scripts.archiprojects import members, parse_groups, render_tree, validate
from scripts.module_passports import install_pairs, load_passports

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "modules" / "projects" / "scripts" / "archiprojects.py"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def group_block(gid, name, status="active", parent=None):
    lines = [f"## {gid}", "```yaml", f"id: {gid}", f"name: {name}", f"status: {status}", "kind: group"]
    if parent:
        lines.append(f"parent: {parent}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def card(project_id, primary, extra=""):
    return (
        "# Project Card\n"
        f"Project ID: {project_id}\n"
        f"Name: {project_id}\n"
        f"primary_archiproject: {primary}\n"
        f"{extra}"
        "Status: active\n"
        "Purpose: fixture.\n"
    )


def make_hub(tmp, groups_text, cards=None):
    hub = Path(tmp) / "_ai-hub"
    write(hub / "ai" / "archiprojects.md", "# Archiprojects\n\n## Schema\n\n" + groups_text)
    for project_id, text in (cards or {}).items():
        write(hub / "ai" / "project-cards" / f"{project_id}.md", text)
    return hub


class ParseGroupsTests(unittest.TestCase):
    def test_valid_three_level_tree(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            text = (
                group_block("top", "Top")
                + group_block("mid", "Mid", parent="top")
                + group_block("bottom", "Bottom", parent="mid")
            )
            hub = make_hub(tmp, text)
            groups = parse_groups(hub / "ai" / "archiprojects.md")
            self.assertEqual(set(groups), {"top", "mid", "bottom"})
            self.assertEqual(groups["bottom"]["parent"], "mid")
            self.assertEqual(validate(hub), [])

    def test_skips_template_entry(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(tmp, "## <archiproject-id>\n```yaml\nid: <archiproject-id>\nname: x\nstatus: active\nkind: group\n```\n")
            groups = parse_groups(hub / "ai" / "archiprojects.md")
            self.assertEqual(groups, {})

    def test_goal_entry_raises(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            text = (
                "## g1\n```yaml\nid: g1\nname: Goal\nstatus: active\nkind: goal\n"
                "target: 10\nunit: things\ndue: none\n```\n"
            )
            hub = make_hub(tmp, text)
            with self.assertRaises(ValueError):
                parse_groups(hub / "ai" / "archiprojects.md")

    def test_duplicate_id_raises(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            text = group_block("dup", "Dup") + group_block("dup", "Dup2")
            hub = make_hub(tmp, text)
            with self.assertRaises(ValueError):
                parse_groups(hub / "ai" / "archiprojects.md")

    def test_missing_field_raises(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            text = "## g1\n```yaml\nid: g1\nname: G\nkind: group\n```\n"
            hub = make_hub(tmp, text)
            with self.assertRaises(ValueError):
                parse_groups(hub / "ai" / "archiprojects.md")


class ValidateTests(unittest.TestCase):
    def test_missing_parent(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(tmp, group_block("child", "Child", parent="ghost"))
            errors = validate(hub)
            self.assertTrue(any("unknown parent" in e for e in errors))

    def test_cycle(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            text = group_block("a", "A", parent="b") + group_block("b", "B", parent="a")
            hub = make_hub(tmp, text)
            errors = validate(hub)
            self.assertTrue(any("cycle" in e for e in errors))

    def test_depth_four_is_error(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            text = (
                group_block("l1", "L1")
                + group_block("l2", "L2", parent="l1")
                + group_block("l3", "L3", parent="l2")
                + group_block("l4", "L4", parent="l3")
            )
            hub = make_hub(tmp, text)
            errors = validate(hub)
            self.assertTrue(any("depth" in e for e in errors))

    def test_card_unknown_group(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(
                tmp,
                group_block("real", "Real"),
                cards={"p1": card("p1", "ghost")},
            )
            errors = validate(hub)
            self.assertTrue(any("unknown primary archiproject" in e for e in errors))

    def test_card_with_dropped_field_fails(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(
                tmp,
                group_block("real", "Real"),
                cards={"p1": card("p1", "real", extra="archiproject_contribution: architecture\nrelated_archiprojects: none\n")},
            )
            errors = validate(hub)
            self.assertTrue(any("archiproject_contribution" in e for e in errors))

    def test_clean_fixture_has_no_errors(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(
                tmp,
                group_block("real", "Real"),
                cards={"p1": card("p1", "real")},
            )
            self.assertEqual(validate(hub), [])


class MembersTests(unittest.TestCase):
    def test_members_of_top_group_includes_subgroup_projects(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            text = group_block("top", "Top") + group_block("sub", "Sub", parent="top")
            hub = make_hub(
                tmp,
                text,
                cards={
                    "p1": card("p1", "top"),
                    "p2": card("p2", "sub"),
                    "p3": card("p3", "none"),
                },
            )
            groups = parse_groups(hub / "ai" / "archiprojects.md")
            from modules.projects.scripts.archiprojects import read_cards
            cards = read_cards(hub)
            self.assertEqual(members(groups, cards, "top"), ["p1", "p2"])
            self.assertEqual(members(groups, cards, "sub"), ["p2"])

    def test_members_includes_inactive_cards(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(
                tmp,
                group_block("top", "Top"),
                cards={"p1": card("p1", "top").replace("Status: active", "Status: paused")},
            )
            groups = parse_groups(hub / "ai" / "archiprojects.md")
            from modules.projects.scripts.archiprojects import read_cards
            cards = read_cards(hub)
            self.assertEqual(members(groups, cards, "top"), ["p1"])


class TreeTests(unittest.TestCase):
    def test_tree_exact_text(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            text = group_block("top", "Top") + group_block("sub", "Sub", parent="top")
            hub = make_hub(
                tmp,
                text,
                cards={"p1": card("p1", "top"), "p2": card("p2", "sub")},
            )
            groups = parse_groups(hub / "ai" / "archiprojects.md")
            from modules.projects.scripts.archiprojects import read_cards
            cards = read_cards(hub)
            lines = render_tree(groups, cards)
            self.assertEqual(
                lines,
                [
                    "top — Top",
                    "  - p1",
                    "  sub — Sub",
                    "    - p2",
                ],
            )


def goal_block(gid):
    return (
        f"## {gid}\n```yaml\nid: {gid}\nname: {gid}\nstatus: active\nkind: goal\n"
        "target: 10\nunit: things\ndue: none\n```\n"
    )


class ValidateCollectsAllErrorsTests(unittest.TestCase):
    def test_two_goal_entries_and_two_bad_cards_yield_four_errors(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            text = (
                group_block("real", "Real")
                + goal_block("goal1")
                + goal_block("goal2")
            )
            hub = make_hub(
                tmp,
                text,
                cards={
                    "p1": card("p1", "real", extra="archiproject_contribution: architecture\nrelated_archiprojects: none\n"),
                    "p2": card("p2", "real", extra="archiproject_contribution: architecture\nrelated_archiprojects: none\n"),
                },
            )
            errors = validate(hub)
            self.assertEqual(len(errors), 4, errors)
            self.assertEqual(sum("goal entry not allowed" in e for e in errors), 2)
            self.assertEqual(sum("archiproject_contribution" in e for e in errors), 2)


class GroupFieldValidationTests(unittest.TestCase):
    def test_non_kebab_id_is_error(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(tmp, group_block("Bad_ID", "Bad"))
            errors = validate(hub)
            self.assertTrue(any("invalid archiproject ID" in e for e in errors), errors)

    def test_invalid_status_is_error(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(tmp, group_block("real", "Real", status="on-fire"))
            errors = validate(hub)
            self.assertTrue(any("invalid archiproject status" in e for e in errors), errors)

    def test_unterminated_fence_is_error(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            text = "## real\n```yaml\nid: real\nname: Real\nstatus: active\nkind: group\n"
            hub = make_hub(tmp, text)
            errors = validate(hub)
            self.assertTrue(any("unterminated" in e for e in errors), errors)
            with self.assertRaises(ValueError):
                parse_groups(hub / "ai" / "archiprojects.md")


class CliErrorHandlingTests(unittest.TestCase):
    def test_tree_cli_reports_parse_error_without_traceback(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(tmp, goal_block("goal1"))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "tree", "--hub", str(hub)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_members_cli_reports_parse_error_without_traceback(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(tmp, goal_block("goal1"))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "members", "--hub", str(hub), "--group", "goal1"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


class CliTests(unittest.TestCase):
    def test_validate_cli_ok_and_fail(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(tmp, group_block("top", "Top"), cards={"p1": card("p1", "top")})
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", "--hub", str(hub)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("archiprojects: ok", result.stdout)

            write(hub / "ai" / "project-cards" / "p1.md", card("p1", "ghost"))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", "--hub", str(hub)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("unknown primary archiproject", result.stderr)

    def test_members_cli_unknown_group_exit_2(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = make_hub(tmp, group_block("top", "Top"))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "members", "--hub", str(hub), "--group", "ghost"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2)


class RegistryScriptTests(unittest.TestCase):
    def _fixture(self, tmp, groups_text, card_extra=""):
        hub = Path(tmp) / "_ai-hub"
        write(hub / "ai" / "allowed-roots.md", f"- {hub}/projects\n")
        write(hub / "ai" / "archiprojects.md", "# Archiprojects\n\n## Schema\n\n" + groups_text)
        project = hub / "projects" / "p1"
        for f in ("current-task", "paused-tasks", "future-tasks", "project-context", "decisions", "changelog"):
            write(project / "ai" / f"{f}.md", "placeholder\n")
        write(
            hub / "ai" / "project-cards" / "p1.md",
            "# Project Card\n"
            "Project ID: p1\n"
            "Name: P1\n"
            "Type: project\n"
            "Status: active\n"
            "Last updated: 2026-09-27\n"
            "Purpose: fixture.\n"
            "Typical tasks: fixture.\n"
            f"Memory entry point: {project}/ai/current-task.md\n"
            "primary_archiproject: top\n"
            f"{card_extra}",
        )
        write(
            hub / "ai" / "project-registry.md",
            "# Project Registry\n\n## p1\nName: P1\nType: project\nStatus: active\n"
            f"Path: {project}\nTags: fixture\nCard: ai/project-cards/p1.md\n",
        )
        return hub

    def test_clean_fixture_passes(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self._fixture(tmp, group_block("top", "Top"))
            result = subprocess.run(
                ["bash", str(ROOT / "modules" / "core" / "scripts" / "check-hub-registry.sh"), str(hub)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_dropped_field_fails(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self._fixture(
                tmp,
                group_block("top", "Top"),
                card_extra="archiproject_contribution: architecture\nrelated_archiprojects: none\n",
            )
            result = subprocess.run(
                ["bash", str(ROOT / "modules" / "core" / "scripts" / "check-hub-registry.sh"), str(hub)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)


class DroppedCardFieldsRemovedTests(unittest.TestCase):
    # scripts/archiprojects.py is exempt: it must name the dropped fields to
    # reject cards that still carry them (FORBIDDEN_FIELDS), per task 1.
    EXEMPT = {"modules/projects/scripts/archiprojects.py"}

    def test_no_installed_file_mentions_dropped_fields(self):
        passports = load_passports(ROOT)
        hits = []
        for module_id in passports:
            for source, _ in install_pairs(ROOT, passports, [module_id]):
                if source in self.EXEMPT:
                    continue
                text = (ROOT / source).read_text(encoding="utf-8", errors="replace")
                if "archiproject_contribution" in text or "related_archiprojects" in text:
                    hits.append(source)
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
