#!/usr/bin/env python3
"""Emit compact task discovery rows for active registered Hub projects."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Installed Hub: archiprojects.py (owned by projects) sits next to this script
# in the same scripts/ target directory. Repository source tree: it lives
# under modules/projects/scripts/ instead, so fall back to that path.
_HERE = Path(__file__).resolve().parent
if not (_HERE / "archiprojects.py").exists():
    sys.path.insert(0, str(_HERE / ".." / ".." / "projects" / "scripts"))

from archiprojects import members as archiproject_members
from archiprojects import parse_groups, read_cards
from task_records import read_records_lines, unrecognized_headings

SOURCE_FILES = {
    "current": "ai/current-task.md",
    "future": "ai/future-tasks.md",
    "paused": "ai/paused-tasks.md",
}
SOURCE_ORDER = {"current": 0, "future": 1, "paused": 2}


def parse_registry(path: Path) -> list[dict[str, str]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("invalid project registry")
    projects = []
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if current is not None:
                projects.append(current)
            project_id = line[3:].strip()
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", project_id):
                raise ValueError("invalid project id")
            current = {"project_id": project_id}
        elif current is not None and ": " in line:
            key, value = line.split(": ", 1)
            if key in {"Status", "Path"}:
                current[key.lower()] = value.strip()
    if current is not None:
        projects.append(current)
    seen = set()
    for project in projects:
        if project["project_id"] in seen:
            raise ValueError("duplicate project id")
        seen.add(project["project_id"])
        if "status" not in project or "path" not in project:
            raise ValueError("incomplete project registry entry")
    return projects


def registered_project_root(hub: Path, project: dict[str, str]) -> Path:
    allowed_root = hub / "projects"
    if allowed_root.is_symlink() or not allowed_root.is_dir():
        raise ValueError("invalid Hub projects root")
    allowed_root = allowed_root.resolve()
    candidate = Path(project["path"]).expanduser()
    if not candidate.is_absolute() or ".." in candidate.parts or candidate.is_symlink():
        raise ValueError(f"invalid registered project path: {project['project_id']}")
    resolved = candidate.resolve()
    if not resolved.is_dir() or resolved.parent != allowed_root:
        raise ValueError(f"invalid registered project path: {project['project_id']}")
    return resolved


def safe_record(project_root: Path, relative: str) -> Path:
    project_root = project_root.resolve()
    path = project_root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing or unsafe canonical task record: {relative}")
    path.resolve().relative_to(project_root)
    return path


def resolve_group_project_ids(hub: Path, group_id: str) -> set[str]:
    """Return the member project ids for `group_id` (KeyError if unknown)."""
    groups = parse_groups(hub / "ai/archiprojects.md")
    cards = read_cards(hub)
    return set(archiproject_members(groups, cards, group_id))


def build_index(hub: Path, group_id: str | None = None) -> list[dict[str, object]]:
    hub = hub.resolve()
    allowed_project_ids = None
    if group_id is not None:
        allowed_project_ids = resolve_group_project_ids(hub, group_id)
    rows = []
    for project in sorted(parse_registry(hub / "ai/project-registry.md"), key=lambda item: item["project_id"]):
        if project["status"] != "active":
            continue
        if allowed_project_ids is not None and project["project_id"] not in allowed_project_ids:
            continue
        project_root = registered_project_root(hub, project)
        for kind, relative in SOURCE_FILES.items():
            path = safe_record(project_root, relative)
            with path.open("r", encoding="utf-8") as stream:
                records = read_records_lines(project["project_id"], kind, stream)
            with path.open("r", encoding="utf-8") as stream:
                for number, heading in unrecognized_headings(kind, stream):
                    print(f"WARNING: unrecognized task heading skipped: {project['project_id']} {relative}:{number}: {heading}", file=sys.stderr)
            for record in records:
                rows.append({
                    "project_id": project["project_id"],
                    "task_id": record["task_id"],
                    "title": record["title"],
                    "status": record["status"],
                    "due": record["due"],
                    "source_kind": kind,
                    "source_path": str(path),
                })
    rows.sort(key=lambda row: (row["project_id"], SOURCE_ORDER[row["source_kind"]], row["task_id"]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", required=True, type=Path)
    parser.add_argument("--group")
    args = parser.parse_args()
    if args.group is not None:
        try:
            resolve_group_project_ids(args.hub.resolve(), args.group)
        except KeyError:
            print(f"unknown archiprojects group: {args.group}", file=sys.stderr)
            return 2
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2
    try:
        print(json.dumps(build_index(args.hub, args.group), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
