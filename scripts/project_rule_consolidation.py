#!/usr/bin/env python3
"""Preview or apply the safe first batch of project-rule consolidation."""

import argparse
import re
from pathlib import Path


RULE_FILES = ("AGENTS.md", "CLAUDE.md", "ai/architecture.md")


def render_entry():
    return (Path(__file__).resolve().parents[1] / "hub-template" / "ai" / "skills"
            / "hub-project-register" / "resources" / "registered-project-entry.md").read_text(encoding="utf-8")


def eligible_files(source_root, project):
    eligible = []
    for relative in RULE_FILES:
        legacy = source_root / "template" / relative
        current = project / relative
        if current.is_file() and current.read_bytes() == legacy.read_bytes():
            eligible.append(relative)
    return eligible


def registered_projects(hub):
    text = (hub / "ai" / "project-registry.md").read_text(encoding="utf-8")
    project_id = None
    for line in text.splitlines():
        match = re.fullmatch(r"## ([a-z0-9]+(?:-[a-z0-9]+)*)", line)
        if match:
            project_id = match.group(1)
        elif project_id and line.startswith("Path: "):
            yield project_id, Path(line[6:])
            project_id = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source_root = Path(__file__).resolve().parents[1]
    entry = render_entry()
    changed = 0
    for project_id, project in registered_projects(args.hub):
        files = eligible_files(source_root, project)
        if not files:
            continue
        print(f"{project_id}: {', '.join(files)}")
        if args.apply:
            for relative in files:
                (project / relative).write_text(entry, encoding="utf-8")
                changed += 1
    if args.apply:
        print(f"updated {changed} files")


if __name__ == "__main__":
    main()
