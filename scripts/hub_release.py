#!/usr/bin/env python3
"""Build and verify a content-addressed manifest for a hub release."""

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path


MEMORY_FILES = {
    "ai/allowed-roots.md", "ai/active-project.md", "ai/archiprojects.md",
    "ai/project-registry.md", "ai/cross-project-signals.md", "ai/goal-log.md",
    "ai/workflow-observations.md", "ai/workflow-context.md",
}
RUNTIME_SCRIPTS = (
    "scripts/check-hub-registry.sh", "scripts/read-compact-project-index.sh",
    "scripts/obsidian-task-sync.sh", "scripts/generate-obsidian-projects-kanban.sh",
    "scripts/count-goal-progress.sh", "scripts/snapshot-calendar.sh",
    "scripts/check-workflow-memory.sh", "scripts/check-session-review.py",
    "scripts/lib/calendar-date.sh",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decide(current, installed, incoming):
    if incoming is None:
        if current is None:
            return "keep"
        return "remove" if installed is not None and current == installed else "conflict"
    if current == incoming:
        return "keep"
    if current is None:
        return "create"
    if installed is not None and current == installed:
        return "replace"
    return "conflict"


def target_path(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("unsafe relative target")
    root = root.resolve()
    probe = root
    for part in relative.parts:
        probe = probe / part
        if probe.is_symlink():
            raise ValueError("symlink target component")
    result = root / relative
    result.resolve().relative_to(root)
    return result


def source_root(source):
    source = source.resolve()
    if (source / "hub-template").is_dir():
        return source
    raise ValueError("source must be the architecture repository containing hub-template")


def file_entry(root, source, target, policy):
    path = root / source
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe source file: {source}")
    return {"source": source, "target": target, "sha256": digest(path),
            "mode": stat.S_IMODE(path.stat().st_mode), "policy": policy}


def build_manifest(source):
    root = source_root(source)
    files = []
    template = root / "hub-template"
    for path in sorted(template.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        target = str(path.relative_to(template))
        policy = "create-if-missing" if target in MEMORY_FILES or target.startswith("ai/project-cards/") or target.startswith("ai/archive/") else "managed"
        files.append(file_entry(root, str(path.relative_to(root)), target, policy))
    for name in RUNTIME_SCRIPTS:
        files.append(file_entry(root, name, name, "managed"))
    files.sort(key=lambda entry: entry["target"])
    if len({entry["target"] for entry in files}) != len(files):
        raise ValueError("duplicate manifest target")
    return {"format": 1, "files": files, "remove": [], "ignore_lines": ["/.local/", "/projects/"]}


def emit(payload):
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "check"):
        command = commands.add_parser(name)
        command.add_argument("--source", required=True, type=Path)
        if name == "check":
            command.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    expected = build_manifest(args.source)
    if args.command == "build":
        emit(expected)
        return 0
    actual = json.loads(args.manifest.read_text(encoding="utf-8"))
    if actual != expected:
        print("release manifest differs from source", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"release error: {error}", file=sys.stderr)
        sys.exit(2)
