#!/usr/bin/env python3
"""List and resolve open session-review improvement proposals across the hub.

Reads only the `## Improvement proposals` section of `ai/session-reviews/*.md`
in active registered projects. `list` prints open proposals (`proposed` or
`accepted`) as JSON; `set` rewrites exactly one proposal's `Disposition:` line.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

OPEN = ("proposed", "accepted")
DECISIONS = ("accepted", "rejected", "implemented")
REVIEW_DATE = re.compile(r"(\d{4})-?(\d{2})-?(\d{2})")
FIELD = re.compile(r"^([A-Z][A-Za-z ]*): ?(.*)$")


def active_projects(hub: Path) -> dict[str, Path]:
    projects, current = {}, {}
    registry = hub / "ai/project-registry.md"
    for line in registry.read_text(encoding="utf-8").splitlines() + ["## "]:
        if line.startswith("## "):
            if current.get("status") == "active" and current.get("path"):
                projects[current["id"]] = Path(current["path"])
            current = {"id": line[3:].strip()}
        elif line.startswith("Status: "):
            current["status"] = line[8:].strip()
        elif line.startswith("Path: "):
            current["path"] = line[6:].strip()
    root = (hub / "projects").resolve()
    return {pid: path for pid, path in projects.items()
            if path.resolve().parent == root and not path.is_symlink()}


def proposal_blocks(lines: list[str]):
    """Yield (proposal_id, fields, disposition_line_index) for each proposal."""
    in_section, pid, fields, disp, key = False, None, {}, None, None
    for index, line in enumerate(lines + ["## end"]):
        if line.startswith("## "):
            if pid:
                yield pid, fields, disp
            in_section, pid = line.strip() == "## Improvement proposals", None
            continue
        if not in_section:
            continue
        if line.startswith("### "):
            if pid:
                yield pid, fields, disp
            pid, fields, disp, key = line[4:].strip(), {}, None, None
            continue
        match = FIELD.match(line)
        if pid and match:
            key = match.group(1)
            fields[key] = match.group(2).strip()
            if key == "Disposition":
                disp = index
        elif pid and key and line.startswith(" ") and line.strip():
            fields[key] = f"{fields[key]} {line.strip()}".strip()


def review_files(project: Path):
    directory = project / "ai/session-reviews"
    if directory.is_dir() and not directory.is_symlink():
        for path in sorted(directory.glob("*.md")):
            if path.is_file() and not path.is_symlink():
                yield path


def review_date(name: str):
    match = REVIEW_DATE.search(name)
    if not match:
        return None
    try:
        return dt.date(*map(int, match.groups()))
    except ValueError:
        return None


def command_list(hub: Path, until: dt.date) -> int:
    items = []
    for pid, project in sorted(active_projects(hub).items()):
        for path in review_files(project):
            lines = path.read_text(encoding="utf-8").splitlines()
            for proposal, fields, _ in proposal_blocks(lines):
                disposition = fields.get("Disposition", "").split()[0:1]
                if not disposition or disposition[0] not in OPEN:
                    continue
                day = review_date(path.name)
                items.append({
                    "project": pid,
                    "review": f"ai/session-reviews/{path.name}",
                    "proposal": proposal,
                    "disposition": disposition[0],
                    "change": fields.get("Change", "(без описания)")[:300],
                    "age_days": (until - day).days if day else None,
                })
    print(json.dumps(items, ensure_ascii=False, indent=1))
    return 0


def command_set(hub: Path, project_id: str, review: str, proposal: str, decision: str) -> int:
    projects = active_projects(hub)
    if project_id not in projects:
        sys.exit(f"not an active registered project: {project_id}")
    relative = Path(review)
    if relative.parent != Path("ai/session-reviews") or relative.suffix != ".md":
        sys.exit("review must be ai/session-reviews/<file>.md")
    path = projects[project_id] / relative
    if path not in set(review_files(projects[project_id])):
        sys.exit(f"review not found: {review}")
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    for pid, _fields, disp in proposal_blocks(lines):
        if pid == proposal and disp is not None:
            lines[disp] = f"Disposition: {decision}"
            path.write_text("\n".join(lines), encoding="utf-8")
            print(f"{project_id} {review} {proposal}: {decision}")
            return 0
    sys.exit(f"proposal with a Disposition line not found: {proposal}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hub", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--until", required=True, type=dt.date.fromisoformat)
    setting = commands.add_parser("set")
    setting.add_argument("--project", required=True)
    setting.add_argument("--review", required=True)
    setting.add_argument("--proposal", required=True)
    setting.add_argument("--decision", required=True, choices=DECISIONS)
    args = parser.parse_args()
    hub = args.hub.resolve()
    if args.command == "list":
        return command_list(hub, args.until)
    return command_set(hub, args.project, args.review, args.proposal, args.decision)


if __name__ == "__main__":
    sys.exit(main())
