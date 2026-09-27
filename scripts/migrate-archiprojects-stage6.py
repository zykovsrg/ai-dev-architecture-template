#!/usr/bin/env python3
"""One-time stage 6 migration: archiproject groups and goals.

Moves `kind: goal` entries out of `ai/archiprojects.md` into `ai/goals.md`
under two new groups (`hadassah-promo`, `hadassah-seo`), and sets
`primary_archiproject` on the promo/SEO project cards. See
docs/superpowers/sdd task-5-brief.md for the full behaviour. Python stdlib
only; run once per Hub, then delete or ignore (idempotent on re-run).
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

NEW_GROUPS = {
    "hadassah-promo": {"id": "hadassah-promo", "name": "Промо", "status": "active", "parent": "hadassah"},
    "hadassah-seo": {"id": "hadassah-seo", "name": "SEO", "status": "active", "parent": "hadassah"},
}

GOAL_ID_TO_GROUP = {
    "hadassah-promo-32-aug-sep": "hadassah-promo",
    "seo-pages-80-sep": "hadassah-seo",
}

PROMO_EXACT_IDS = {"promo-pages", "stranitsa-stomatologii", "stranitsa-vyezdnoy-sluzhby"}
PROMO_PREFIX = "release-page-"

FORBIDDEN_FIELDS = ("archiproject_contribution:", "related_archiprojects:")

ID_RE = re.compile(r"^id:\s*(.+)$")
KIND_RE = re.compile(r"^kind:\s*(.+)$")
FIELD_RE = re.compile(r"^([A-Za-z_]+):\s*(.*)$")

GOALS_HEADER = """# Goals

Canonical hub-owned numeric goal registry. Each goal references a group in
`ai/archiprojects.md` via `group`; `ai/archiprojects.md` never references
goals. `ai/goal-log.md` records progress against a goal's `id` here.

## Schema

Use one human heading and one fenced YAML block for each goal. `group` must
name a known group in `ai/archiprojects.md`.

## <goal-id>

```yaml
id: <goal-id>
name: <human name>
status: <status>
group: <archiproject-group-id>
target: <target>
unit: <unit>
due: YYYY-MM-DD or none
```
"""


class MigrationError(Exception):
    pass


def _split_blocks(text):
    """Split archiprojects.md text into (heading_or_None, lines) blocks.

    Concatenating every block's lines back in order (joined with "\\n")
    reproduces `text` exactly.
    """
    lines = text.split("\n")
    blocks = []
    heading = None
    current = []
    for line in lines:
        if line.startswith("## "):
            blocks.append((heading, current))
            heading = line[3:].strip()
            current = [line]
        else:
            current.append(line)
    blocks.append((heading, current))
    return blocks


def _render_blocks(blocks):
    lines = []
    for _heading, block_lines in blocks:
        lines.extend(block_lines)
    return "\n".join(lines)


def _block_fields(block_lines):
    fields = {}
    in_fence = False
    for line in block_lines:
        if not in_fence:
            if line == "```yaml":
                in_fence = True
            continue
        if line == "```":
            in_fence = False
            continue
        match = FIELD_RE.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def _render_group_block(group):
    lines = [f"## {group['id']}", "", "```yaml", f"id: {group['id']}", f"name: {group['name']}",
              f"status: {group['status']}", "kind: group"]
    if group.get("parent"):
        lines.append(f"parent: {group['parent']}")
    lines.append("```")
    lines.append("")
    return lines


def extract_goals_and_ensure_groups(text):
    """Return (new_text, goal_entries, existing_group_ids, added_group_ids).

    `goal_entries` is a list of dicts with the fields moved out of the file.
    Raises MigrationError on any goal id not in GOAL_ID_TO_GROUP.
    """
    blocks = _split_blocks(text)
    kept_blocks = []
    goal_entries = []
    existing_group_ids = set()

    for heading, block_lines in blocks:
        if heading is None or heading == "Schema" or "<" in heading:
            kept_blocks.append((heading, block_lines))
            continue
        fields = _block_fields(block_lines)
        kind = fields.get("kind")
        if kind == "goal":
            goal_id = fields.get("id", heading)
            if goal_id not in GOAL_ID_TO_GROUP:
                raise MigrationError(f"unknown goal id in ai/archiprojects.md: {goal_id}")
            goal_entries.append({
                "id": goal_id,
                "name": fields.get("name", ""),
                "status": fields.get("status", ""),
                "group": GOAL_ID_TO_GROUP[goal_id],
                "target": fields.get("target", ""),
                "unit": fields.get("unit", ""),
                "due": fields.get("due", ""),
            })
            continue
        if kind == "group":
            group_id = fields.get("id", heading)
            existing_group_ids.add(group_id)
        kept_blocks.append((heading, block_lines))

    added_group_ids = []
    for group_id in ("hadassah-promo", "hadassah-seo"):
        if group_id in existing_group_ids:
            continue
        kept_blocks.append((group_id, _render_group_block(NEW_GROUPS[group_id])))
        added_group_ids.append(group_id)

    new_text = _render_blocks(kept_blocks)
    if not new_text.endswith("\n"):
        new_text += "\n"
    return new_text, goal_entries, existing_group_ids, added_group_ids


def render_goal_block(goal):
    return (
        f"\n## {goal['id']}\n\n```yaml\n"
        f"id: {goal['id']}\n"
        f"name: {goal['name']}\n"
        f"status: {goal['status']}\n"
        f"group: {goal['group']}\n"
        f"target: {goal['target']}\n"
        f"unit: {goal['unit']}\n"
        f"due: {goal['due']}\n"
        "```\n"
    )


def build_goals_text(existing_text, goal_entries, existing_goal_ids):
    text = existing_text if existing_text is not None else GOALS_HEADER
    if not text.endswith("\n"):
        text += "\n"
    for goal in goal_entries:
        if goal["id"] in existing_goal_ids:
            continue
        text += render_goal_block(goal)
    return text


def existing_goal_ids(goals_text):
    if goals_text is None:
        return set()
    ids = set()
    for heading, block_lines in _split_blocks(goals_text):
        if heading is None or heading == "Schema" or (heading and "<" in heading):
            continue
        fields = _block_fields(block_lines)
        if fields.get("id"):
            ids.add(fields["id"])
    return ids


CARD_ID_RE = re.compile(r"^Project ID:\s*(.+)$")
CARD_NAME_RE = re.compile(r"^Name:\s*(.+)$")
CARD_PURPOSE_RE = re.compile(r"^Purpose:\s*(.+)$")
CARD_PRIMARY_RE = re.compile(r"^primary_archiproject:\s*(.+)$")


def is_promo_id(project_id):
    return project_id in PROMO_EXACT_IDS or project_id.startswith(PROMO_PREFIX)


def plan_card_change(path):
    """Return (new_text_or_None, change_lines) for one card file.

    new_text is None when nothing needs to change.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    project_id = None
    name = ""
    purpose = ""
    current_primary = None
    for line in lines:
        match = CARD_ID_RE.match(line)
        if match:
            project_id = match.group(1).strip()
            continue
        match = CARD_NAME_RE.match(line)
        if match:
            name = match.group(1)
            continue
        match = CARD_PURPOSE_RE.match(line)
        if match:
            purpose = match.group(1)
            continue
        match = CARD_PRIMARY_RE.match(line)
        if match:
            current_primary = match.group(1).strip()

    target_primary = None
    if project_id and is_promo_id(project_id):
        target_primary = "hadassah-promo"
    elif (
        current_primary == "hadassah"
        and ("seo" in name.lower() or "seo" in purpose.lower())
    ):
        target_primary = "hadassah-seo"

    change_lines = []
    new_lines = []
    changed = False
    for line in lines:
        if any(line.startswith(field) for field in FORBIDDEN_FIELDS):
            changed = True
            change_lines.append(f"{path}: {line} -> (removed)")
            continue
        if target_primary and CARD_PRIMARY_RE.match(line):
            if current_primary != target_primary:
                changed = True
                change_lines.append(f"{path}: primary_archiproject: {current_primary} -> {target_primary}")
            new_lines.append(f"primary_archiproject: {target_primary}")
            continue
        new_lines.append(line)

    if not changed:
        return None, [], project_id, target_primary
    return "\n".join(new_lines), change_lines, project_id, target_primary


def atomic_write(path, text):
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def run(hub, apply_changes):
    hub = Path(hub)
    archiprojects_path = hub / "ai" / "archiprojects.md"
    goals_path = hub / "ai" / "goals.md"
    cards_dir = hub / "ai" / "project-cards"

    archi_text = archiprojects_path.read_text(encoding="utf-8")
    new_archi_text, goal_entries, existing_group_ids, added_group_ids = (
        extract_goals_and_ensure_groups(archi_text)
    )

    goals_text = goals_path.read_text(encoding="utf-8") if goals_path.exists() else None
    known_goal_ids = existing_goal_ids(goals_text)
    new_goals_text = build_goals_text(goals_text, goal_entries, known_goal_ids)

    report_lines = []
    for group_id in added_group_ids:
        report_lines.append(f"{archiprojects_path}: (missing) -> group {group_id} added")
    for goal in goal_entries:
        report_lines.append(
            f"{archiprojects_path}: goal {goal['id']} (kind: goal) -> {goals_path} (group: {goal['group']})"
        )

    card_changes = []  # (path, new_text, change_lines)
    promo_ids = []
    seo_ids = []
    if cards_dir.is_dir():
        for card_path in sorted(cards_dir.glob("*.md")):
            new_text, change_lines, project_id, target_primary = plan_card_change(card_path)
            if target_primary == "hadassah-promo":
                promo_ids.append(project_id)
            elif target_primary == "hadassah-seo":
                seo_ids.append(project_id)
            if new_text is not None:
                card_changes.append((card_path, new_text, change_lines))
                report_lines.extend(change_lines)

    for line in report_lines:
        print(line)
    print(f"promo projects: {len(promo_ids)}")
    print("seo projects:")
    for project_id in sorted(seo_ids):
        print(f"  {project_id}")

    if not apply_changes:
        return 0

    archi_changed = new_archi_text != archi_text
    goals_changed = goals_text is None or new_goals_text != goals_text
    if archi_changed:
        atomic_write(archiprojects_path, new_archi_text)
    if goals_changed:
        atomic_write(goals_path, new_goals_text)
    for card_path, new_text, _change_lines in card_changes:
        atomic_write(card_path, new_text)

    validate_result = subprocess.run(
        [sys.executable, str(ROOT / "archiprojects.py"), "validate", "--hub", str(hub)],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(validate_result.stdout)
    sys.stderr.write(validate_result.stderr)
    return validate_result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    try:
        return run(args.hub, args.apply)
    except MigrationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
