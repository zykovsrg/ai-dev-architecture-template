#!/usr/bin/env python3
"""Archiproject groups: parsing, validation, and group membership.

Groups live in ai/archiprojects.md as a heading followed by a fenced YAML
block (id, name, status, kind: group, optional parent, optional
calendar_name). Cards reference at most one group via `primary_archiproject:`
and may set a Cyrillic `Calendar name:`. Calendar event titles show the whole
available chain: group calendar names from the root, then the project's
calendar name, then the task. Standard library only.
"""

import argparse
import re
import sys
from pathlib import Path

HEADING_RE = re.compile(r"^## (.+)$")
FIELD_RE = re.compile(r"^([A-Za-z_]+):\s*(.*)$")
REQUIRED_FIELDS = ("id", "name", "status", "kind")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STATUSES = ("active", "paused", "archived", "missing", "registration-pending")


def _raw_entries(text):
    """Yield (heading_id, fence_lines, unterminated) for each '## ' entry.

    `heading_id` is None for text before the first heading. `fence_lines` is
    None when no fenced yaml block appeared. `unterminated` is True when the
    fence was still open (never closed) when the entry ended.
    """
    heading = None
    fence_lines = None
    in_fence = False
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        match = HEADING_RE.match(line)
        if match:
            yield (heading, fence_lines, in_fence)
            candidate = match.group(1).strip()
            heading = None if candidate == "Schema" else candidate
            fence_lines = None
            in_fence = False
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
    yield (heading, fence_lines, in_fence)


def _parse_fields(fence_lines, heading_id):
    fields = {}
    for line in fence_lines:
        match = FIELD_RE.match(line)
        if not match:
            raise ValueError(f"unrecognized YAML line in archiproject entry: {heading_id}")
        key, value = match.group(1), match.group(2).strip()
        if key in fields:
            raise ValueError(f"duplicate field {key} in archiproject entry: {heading_id}")
        fields[key] = value
    return fields


def _validate_fields(heading_id, fields):
    for field in REQUIRED_FIELDS:
        if field not in fields or not fields[field]:
            raise ValueError(f"missing {field} in archiproject entry: {heading_id}")
    if fields["kind"] == "goal":
        raise ValueError(f"goal entry not allowed in archiprojects.md: {heading_id}")
    if fields["kind"] != "group":
        raise ValueError(f"invalid kind in archiproject entry: {heading_id}")
    if fields["id"] != heading_id:
        raise ValueError(f"archiproject entry ID mismatch: {heading_id}")
    if not ID_RE.match(fields["id"]):
        raise ValueError(f"invalid archiproject ID: {heading_id}")
    if fields["status"] not in STATUSES:
        raise ValueError(f"invalid archiproject status: {heading_id}")


def _parse_groups_with_errors(path):
    """Parse ai/archiprojects.md, tolerating per-entry errors.

    Returns (groups, errors): `groups` holds every entry that parsed cleanly;
    `errors` holds one message per entry that did not (goal entry, missing or
    unterminated YAML block, missing/invalid field, duplicate id).
    Skips template entries whose heading id contains "<".
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    groups = {}
    errors = []
    for heading_id, fence_lines, unterminated in _raw_entries(text):
        if heading_id is None or "<" in heading_id:
            continue
        if unterminated:
            errors.append(f"unterminated archiproject registry entry: {heading_id}")
            continue
        if fence_lines is None:
            errors.append(f"missing YAML block for archiproject entry: {heading_id}")
            continue
        try:
            fields = _parse_fields(fence_lines, heading_id)
            _validate_fields(heading_id, fields)
        except ValueError as error:
            errors.append(str(error))
            continue
        group_id = fields["id"]
        if group_id in groups:
            errors.append(f"duplicate archiproject ID: {heading_id}")
            continue
        groups[group_id] = {
            "id": group_id,
            "name": fields["name"],
            "status": fields["status"],
            "parent": fields.get("parent") or None,
            "calendar_name": fields.get("calendar_name") or None,
        }
    return groups, errors


def parse_groups(path):
    """Parse ai/archiprojects.md into {id: {"id","name","status","parent"}}.

    Skips template entries whose heading id contains "<". Raises ValueError
    (the first problem found) on a `kind: goal` entry, a duplicate id, an
    invalid id or status, an unterminated or missing YAML block, or a missing
    field. Use `validate()` when every problem must be collected.
    """
    groups, errors = _parse_groups_with_errors(path)
    if errors:
        raise ValueError(errors[0])
    return groups


CARD_ID_RE = re.compile(r"^Project ID:\s*(.+)$")
CARD_PRIMARY_RE = re.compile(r"^primary_archiproject:\s*(.+)$")
CARD_CALENDAR_RE = re.compile(r"^Calendar name:\s*(.+)$")
GROUP_PROJECT = "—"
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
        calendar = None
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
            calendar_match = CARD_CALENDAR_RE.match(line)
            if calendar_match:
                calendar = calendar_match.group(1).strip()
                continue
            if any(line.startswith(field) for field in FORBIDDEN_FIELDS):
                forbidden = True
        cards.append({
            "path": card_path,
            "project_id": project_id,
            "primary_archiproject": primary,
            "calendar_name": calendar,
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
    """Return every problem found: group-entry errors, unknown/cyclic/deep
    parents, and card-level errors. Never stops at the first failure."""
    hub = Path(hub)
    archiprojects_file = hub / "ai" / "archiprojects.md"
    groups, errors = _parse_groups_with_errors(archiprojects_file)
    errors = list(errors)

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

    errors.extend(_calendar_errors(groups, read_cards(hub)))
    return errors


def _group_calendar_name(group):
    return (group["calendar_name"] or group["name"]).strip().lower()


def calendar_chain(groups, card):
    """Calendar title prefix of a project: group names from the root, then the project."""
    chain = []
    current = card["primary_archiproject"]
    seen = set()
    while current and current != "none" and current in groups and current not in seen:
        seen.add(current)
        chain.insert(0, _group_calendar_name(groups[current]))
        current = groups[current]["parent"]
    name = (card["calendar_name"] or card["project_id"]).strip().lower()
    # `Calendar name: —` marks the group's general project: the group chain only.
    if name != GROUP_PROJECT or not chain:
        chain.append(name)
    return chain


def calendar_title(groups, cards, project_id, task):
    """Build `<chain>/<task>` for a project; raises KeyError for an unknown project."""
    for card in cards:
        if card["project_id"] == project_id:
            return "/".join(calendar_chain(groups, card) + [task.strip().lower()])
    raise KeyError(project_id)


def resolve_title(groups, cards, title):
    """Return (project_id, task) for a calendar title, or None when unknown or ambiguous.

    The longest matching chain wins; legacy `<category>/<project-id>/<task>`
    titles still resolve through the project ID in the second part.
    """
    parts = title.split("/")
    folded = [part.strip().casefold() for part in parts]
    best, best_len = [], 0
    for card in cards:
        if not card["project_id"]:
            continue
        chain = [part.casefold() for part in calendar_chain(groups, card)]
        if len(chain) < len(parts) and folded[:len(chain)] == chain:
            if len(chain) > best_len:
                best, best_len = [card], len(chain)
            elif len(chain) == best_len:
                best.append(card)
    if not best and len(parts) >= 3:
        best = [c for c in cards if c["project_id"] and c["project_id"].casefold() == folded[1]]
        best_len = 2
    if len(best) != 1:
        return None
    task = "/".join(parts[best_len:]).strip()
    return (best[0]["project_id"], task) if task else None


def _calendar_errors(groups, cards):
    errors = []
    names = [(f"group {gid}", g["calendar_name"]) for gid, g in groups.items()]
    names += [(f"project {c['project_id']}", c["calendar_name"]) for c in cards]
    for owner, name in names:
        if name is not None and (not name.strip() or "/" in name):
            errors.append(f"invalid calendar name for {owner}: {name}")
    for card in cards:
        if (card["calendar_name"] or "").strip() == GROUP_PROJECT and (
                card["primary_archiproject"] in (None, "none") or card["primary_archiproject"] not in groups):
            errors.append(f"invalid calendar name for project {card['project_id']}: {GROUP_PROJECT} needs an archiproject")
    chains = {}
    for card in cards:
        if card["project_id"]:
            chains.setdefault(tuple(calendar_chain(groups, card)), []).append(card["project_id"])
    for chain, owners in chains.items():
        if len(owners) > 1:
            errors.append(f"duplicate calendar title prefix {'/'.join(chain)}: {', '.join(sorted(owners))}")
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

    title_p = sub.add_parser("calendar-title")
    title_p.add_argument("--hub", required=True, type=Path)
    title_p.add_argument("--project", required=True)
    title_p.add_argument("--task", required=True)

    resolve_p = sub.add_parser("resolve-title")
    resolve_p.add_argument("--hub", required=True, type=Path)
    resolve_p.add_argument("--title", required=True)

    args = parser.parse_args()

    if args.command in ("calendar-title", "resolve-title"):
        try:
            groups = parse_groups(args.hub / "ai" / "archiprojects.md")
        except ValueError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
        cards = read_cards(args.hub)
        if args.command == "calendar-title":
            try:
                print(calendar_title(groups, cards, args.project, args.task))
            except KeyError:
                print(f"ERROR: unknown project: {args.project}", file=sys.stderr)
                return 1
            return 0
        import json
        found = resolve_title(groups, cards, args.title)
        print(json.dumps(None if found is None else {"project_id": found[0], "task": found[1]}, ensure_ascii=False))
        return 0 if found else 1

    if args.command == "validate":
        errors = validate(args.hub)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("archiprojects: ok")
        return 0

    if args.command == "tree":
        try:
            groups = parse_groups(args.hub / "ai" / "archiprojects.md")
        except ValueError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
        cards = read_cards(args.hub)
        for line in render_tree(groups, cards):
            print(line)
        return 0

    if args.command == "members":
        try:
            groups = parse_groups(args.hub / "ai" / "archiprojects.md")
        except ValueError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
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
