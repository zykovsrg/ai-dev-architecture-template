#!/usr/bin/env python3
"""Archiproject groups: parsing, validation, and group membership.

Groups live in ai/archiprojects.md as a heading followed by a fenced YAML
block (id, name, status, kind: group, optional parent). Cards reference at
most one group via `primary_archiproject:`. Standard library only.
"""

import argparse
import re
import sys
from pathlib import Path

HEADING_RE = re.compile(r"^## (.+)$")
FIELD_RE = re.compile(r"^([A-Za-z_]+):\s*(.*)$")
REQUIRED_FIELDS = ("id", "name", "status", "kind")


def parse_groups(path):
    """Parse ai/archiprojects.md into {id: {"id","name","status","parent"}}.

    Skips template entries whose heading id contains "<". Raises ValueError
    on a `kind: goal` entry, a duplicate id, or a missing required field.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    groups = {}
    heading = None
    in_fence = False
    fence_lines = None

    def flush(heading_id, fence_lines):
        if heading_id is None:
            return
        if "<" in heading_id:
            return
        if fence_lines is None:
            raise ValueError(f"missing YAML block for archiproject entry: {heading_id}")
        fields = {}
        for line in fence_lines:
            match = FIELD_RE.match(line)
            if not match:
                raise ValueError(f"unrecognized YAML line in archiproject entry: {heading_id}")
            key, value = match.group(1), match.group(2).strip()
            if key in fields:
                raise ValueError(f"duplicate field {key} in archiproject entry: {heading_id}")
            fields[key] = value
        for field in REQUIRED_FIELDS:
            if field not in fields or not fields[field]:
                raise ValueError(f"missing {field} in archiproject entry: {heading_id}")
        if fields["kind"] == "goal":
            raise ValueError(f"goal entry not allowed in archiprojects.md: {heading_id}")
        if fields["kind"] != "group":
            raise ValueError(f"invalid kind in archiproject entry: {heading_id}")
        if fields["id"] != heading_id:
            raise ValueError(f"archiproject entry ID mismatch: {heading_id}")
        if heading_id in groups:
            raise ValueError(f"duplicate archiproject ID: {heading_id}")
        groups[heading_id] = {
            "id": fields["id"],
            "name": fields["name"],
            "status": fields["status"],
            "parent": fields.get("parent") or None,
        }

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        match = HEADING_RE.match(line)
        if match:
            flush(heading, fence_lines)
            candidate = match.group(1).strip()
            heading = None if candidate == "Schema" else candidate
            in_fence = False
            fence_lines = None
            continue
        if heading is None:
            continue
        if not in_fence:
            if line.strip() == "":
                continue
            if line == "```yaml":
                in_fence = True
                fence_lines = []
            continue
        if line == "```":
            in_fence = False
            continue
        fence_lines.append(line)
    flush(heading, fence_lines)
    return groups


CARD_ID_RE = re.compile(r"^Project ID:\s*(.+)$")
CARD_PRIMARY_RE = re.compile(r"^primary_archiproject:\s*(.+)$")
FORBIDDEN_FIELDS = ("archiproject_contribution:", "related_archiprojects:")


def read_cards(hub):
    """Read ai/project-cards/*.md, returning list of dicts with card data."""
    cards_dir = Path(hub) / "ai" / "project-cards"
    cards = []
    if not cards_dir.is_dir():
        return cards
    for card_path in sorted(cards_dir.glob("*.md")):
        text = card_path.read_text(encoding="utf-8")
        project_id = None
        primary = None
        forbidden = False
        for line in text.splitlines():
            id_match = CARD_ID_RE.match(line)
            if id_match:
                project_id = id_match.group(1).strip()
                continue
            primary_match = CARD_PRIMARY_RE.match(line)
            if primary_match:
                primary = primary_match.group(1).strip()
                continue
            if any(line.startswith(field) for field in FORBIDDEN_FIELDS):
                forbidden = True
        cards.append({
            "path": card_path,
            "project_id": project_id,
            "primary_archiproject": primary,
            "forbidden_fields": forbidden,
        })
    return cards


def _depth(groups, group_id):
    seen = []
    current = group_id
    while current is not None:
        if current in seen:
            return None  # cycle
        seen.append(current)
        current = groups[current]["parent"]
    return len(seen)


def validate(hub):
    hub = Path(hub)
    errors = []
    archiprojects_file = hub / "ai" / "archiprojects.md"
    try:
        groups = parse_groups(archiprojects_file)
    except ValueError as error:
        return [str(error)]

    for group_id, group in groups.items():
        parent = group["parent"]
        if parent is not None and parent not in groups:
            errors.append(f"unknown parent for archiproject group {group_id}: {parent}")

    for group_id, group in groups.items():
        parent = group["parent"]
        if parent is None or parent not in groups:
            continue
        seen = [group_id]
        current = parent
        cyclic = False
        while current is not None:
            if current in seen:
                cyclic = True
                break
            seen.append(current)
            current = groups[current]["parent"]
            if current is not None and current not in groups:
                break
        if cyclic:
            errors.append(f"cycle detected in archiproject group ancestry: {group_id}")

    for group_id, group in groups.items():
        parent = group["parent"]
        if parent is not None and parent not in groups:
            continue
        depth = _depth(groups, group_id)
        if depth is None:
            continue  # already reported as a cycle above
        if depth > 3:
            errors.append(f"archiproject group depth exceeds 3: {group_id}")

    for card in read_cards(hub):
        project_id = card["project_id"] or card["path"].name
        primary = card["primary_archiproject"]
        if primary is not None and primary != "none" and primary not in groups:
            errors.append(f"unknown primary archiproject for {project_id}: {primary}")
        if card["forbidden_fields"]:
            errors.append(
                f"card must not contain archiproject_contribution or "
                f"related_archiprojects: {project_id}"
            )

    return errors


def _descendants(groups, group_id):
    result = {group_id}
    changed = True
    while changed:
        changed = False
        for gid, group in groups.items():
            if group["parent"] in result and gid not in result:
                result.add(gid)
                changed = True
    return result


def members(groups, cards, group_id):
    if group_id not in groups:
        raise KeyError(group_id)
    group_ids = _descendants(groups, group_id)
    project_ids = set()
    for card in cards:
        if card["primary_archiproject"] in group_ids and card["project_id"]:
            project_ids.add(card["project_id"])
    return sorted(project_ids)


def _children_map(groups):
    children = {gid: [] for gid in groups}
    for gid, group in groups.items():
        parent = group["parent"]
        if parent in children:
            children[parent].append(gid)
    for gid in children:
        children[gid].sort()
    return children


def render_tree(groups, cards):
    children = _children_map(groups)
    roots = sorted(gid for gid, group in groups.items() if group["parent"] not in groups)
    lines = []

    def visit(gid, depth):
        indent = "  " * depth
        lines.append(f"{indent}{gid} — {groups[gid]['name']}")
        project_ids = sorted(
            card["project_id"]
            for card in cards
            if card["primary_archiproject"] == gid and card["project_id"]
        )
        for project_id in project_ids:
            lines.append(f"{indent}  - {project_id}")
        for child in children.get(gid, []):
            visit(child, depth + 1)

    for root in roots:
        visit(root, 0)
    return lines


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    validate_p = sub.add_parser("validate")
    validate_p.add_argument("--hub", required=True, type=Path)

    tree_p = sub.add_parser("tree")
    tree_p.add_argument("--hub", required=True, type=Path)

    members_p = sub.add_parser("members")
    members_p.add_argument("--hub", required=True, type=Path)
    members_p.add_argument("--group", required=True)

    args = parser.parse_args()

    if args.command == "validate":
        errors = validate(args.hub)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("archiprojects: ok")
        return 0

    if args.command == "tree":
        groups = parse_groups(args.hub / "ai" / "archiprojects.md")
        cards = read_cards(args.hub)
        for line in render_tree(groups, cards):
            print(line)
        return 0

    if args.command == "members":
        groups = parse_groups(args.hub / "ai" / "archiprojects.md")
        cards = read_cards(args.hub)
        try:
            for project_id in members(groups, cards, args.group):
                print(project_id)
        except KeyError:
            print(f"unknown archiproject group: {args.group}", file=sys.stderr)
            return 2
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
