#!/usr/bin/env python3
"""Seed a project's future tasks from its archiproject group's stage template.

A group in ai/archiprojects.md may declare `stage_template: <hub-relative path>`.
The template lists stages as `1. <title>` lines under `## Stages`. The project's
primary group (from its card) and then its ancestors are searched for the
first template. Each stage missing from the project's ai/future-tasks.md is
added as a future task, in template order, above existing records. Titles
already present are skipped, so a second run adds nothing. Standard library only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path

STAGE_RE = re.compile(r"^\d+\.\s+(.+?)\s*$")
TASK_ID_RE = re.compile(r"TASK-[a-z0-9-]+-(\d{8})-(\d{3})")
FUTURE_HEADING = "## Future tasks\n"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _registry_path(hub: Path, project_id: str) -> Path:
    section = None
    for line in (hub / "ai/project-registry.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        elif section == project_id and line.startswith("Path: "):
            return Path(line[6:].strip())
    raise SystemExit(f"error: project not in registry: {project_id}")


def _primary_group(hub: Path, project_id: str) -> str | None:
    card = hub / "ai/project-cards" / f"{project_id}.md"
    if not card.is_file():
        raise SystemExit(f"error: project card missing: {card}")
    for line in card.read_text(encoding="utf-8").splitlines():
        if line.startswith("primary_archiproject:"):
            value = line.split(":", 1)[1].strip()
            return None if value in ("", "none") else value
    return None


def _group_fields(hub: Path) -> dict[str, dict[str, str]]:
    groups: dict[str, dict[str, str]] = {}
    heading, fields, in_fence = None, None, False
    for line in (hub / "ai/archiprojects.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            heading, fields, in_fence = line[3:].strip(), None, False
        elif line == "```yaml" and heading:
            in_fence, fields = True, {}
        elif line == "```" and in_fence:
            in_fence = False
            if fields.get("id"):
                groups[fields["id"]] = fields
        elif in_fence and ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return groups


def find_template(hub: Path, project_id: str) -> str | None:
    groups = _group_fields(hub)
    current, seen = _primary_group(hub, project_id), set()
    while current and current in groups and current not in seen:
        seen.add(current)
        template = groups[current].get("stage_template")
        if template:
            return template
        current = groups[current].get("parent")
    return None


def read_stages(path: Path) -> list[str]:
    stages, in_section = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_section = line.strip() == "## Stages"
            continue
        match = STAGE_RE.match(line) if in_section else None
        if match:
            stages.append(match.group(1))
    if not stages:
        raise SystemExit(f"error: no stages under '## Stages' in {path}")
    return stages


def next_number(project_ai: Path, stamp: str) -> int:
    highest = 0
    for path in project_ai.glob("*.md"):
        for found_stamp, number in TASK_ID_RE.findall(path.read_text(encoding="utf-8")):
            if found_stamp == stamp:
                highest = max(highest, int(number))
    return highest + 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hub", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--done", type=int, default=0, help="mark the first N template stages done")
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    hub = Path(args.hub).resolve()
    project_path = _registry_path(hub, args.project)
    template = find_template(hub, args.project)
    result = {"project": args.project, "template": template, "created": [], "skipped": []}
    if template is None:
        print(json.dumps(result, ensure_ascii=False))
        return 0

    stages = read_stages(hub / template)
    future = project_path / "ai/future-tasks.md"
    text = future.read_text(encoding="utf-8")
    if text.count(FUTURE_HEADING) != 1:
        raise SystemExit(f"error: expected one '## Future tasks' heading in {future}")
    task_records = _load("task_records")
    existing = {r["title"] for r in task_records.read_records_lines(args.project, "future", text.splitlines())}

    stamp = args.today.replace("-", "")
    number = next_number(project_path / "ai", stamp)
    blocks = []
    for index, title in enumerate(stages, start=1):
        if title in existing:
            result["skipped"].append(title)
            continue
        task_id = f"TASK-{args.project}-{stamp}-{number:03d}"
        number += 1
        status = "done" if index <= args.done else "ready"
        blocks.append(
            f"### {task_id} — {title}\n\nStatus: {status}\nCreated: {args.today}\n"
            f"Этап {index} из {len(stages)} (шаблон: `{template}`).\n\n"
        )
        result["created"].append(task_id)

    if blocks and not args.dry_run:
        head, tail = text.split(FUTURE_HEADING, 1)
        tail = tail.lstrip("\n")
        future.write_text(head + FUTURE_HEADING + "\n" + "".join(blocks) + tail, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
