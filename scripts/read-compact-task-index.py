#!/usr/bin/env python3
"""Emit compact task discovery rows for active registered Hub projects."""

import argparse
import json
import re
import sys
from pathlib import Path

from task_records import read_records_lines

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


def build_index(hub: Path) -> list[dict[str, object]]:
    hub = hub.resolve()
    rows = []
    for project in sorted(parse_registry(hub / "ai/project-registry.md"), key=lambda item: item["project_id"]):
        if project["status"] != "active":
            continue
        project_root = registered_project_root(hub, project)
        for kind, relative in SOURCE_FILES.items():
            path = safe_record(project_root, relative)
            with path.open("r", encoding="utf-8") as stream:
                records = read_records_lines(project["project_id"], kind, stream)
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
    args = parser.parse_args()
    try:
        print(json.dumps(build_index(args.hub), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
