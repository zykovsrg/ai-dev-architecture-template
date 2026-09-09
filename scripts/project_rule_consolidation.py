#!/usr/bin/env python3
"""Preview or apply the safe first batch of project-rule consolidation."""

import argparse
import re
from pathlib import Path


RULE_FILES = ("AGENTS.md", "CLAUDE.md", "ai/architecture.md")
OLD_OUTPUT = """Before editing, state `Mode: ...`, the next step, and real risks. After editing, state the mode, summarize changes, list checks, name risks or unfinished parts, say whether task memory changed, and propose `task-finish` if the task appears complete.\n"""


def render_entry():
    return (Path(__file__).resolve().parents[1] / "hub-template" / "ai" / "skills"
            / "hub-project-register" / "resources" / "registered-project-entry.md").read_text(encoding="utf-8")


def eligible_files(source_root, project):
    eligible = []
    for relative in RULE_FILES:
        legacy = source_root / "template" / relative
        current = project / relative
        if current.is_file() and current.read_text(encoding="utf-8") in {
            legacy.read_text(encoding="utf-8"), legacy_shared_variant(legacy.read_text(encoding="utf-8"))
        }:
            eligible.append(relative)
    return eligible


def legacy_shared_variant(text):
    """The former generic entry with only its known obsolete output wording."""
    if "## Output\n" not in text:
        return ""
    text = text.replace(
        "- Keep persistent AI-facing instructions in English.\n",
        "- Keep persistent AI-facing instructions in English.\n"
        "- Use a concise, direct, informational style with very simple words. Default to a short answer; give long explanations only when the user asks. This holds for output produced under any external methodology, including Superpowers.\n",
    )
    output = text.index("## Output\n") + len("## Output\n\n")
    return text[:output] + OLD_OUTPUT


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
