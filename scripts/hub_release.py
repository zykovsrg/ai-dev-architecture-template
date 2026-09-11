#!/usr/bin/env python3
"""Build and verify a content-addressed manifest for a hub release."""

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import uuid
from pathlib import Path


MEMORY_FILES = {
    "ai/allowed-roots.md", "ai/active-project.md", "ai/archiprojects.md",
    "ai/project-registry.md", "ai/cross-project-signals.md", "ai/goal-log.md",
    "ai/workflow-observations.md", "ai/workflow-context.md",
}
RUNTIME_SCRIPTS = (
    "scripts/check-hub-registry.sh", "scripts/read-compact-project-index.sh",
    "scripts/read-compact-task-index.py",
    "scripts/obsidian-task-sync.sh", "scripts/generate-obsidian-projects-kanban.sh",
    "scripts/count-goal-progress.sh", "scripts/snapshot-calendar.sh",
    "scripts/check-workflow-memory.sh", "scripts/check-session-review.py",
    "scripts/check-all-task-records.sh",
    "scripts/lib/calendar-date.sh", "scripts/workflow_friction.py",
    "scripts/task_records.py",
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


def preview(source, hub):
    manifest = build_manifest(source)
    hub = hub.resolve()
    installed_file = hub / ".local" / "hub-release" / "installed.json"
    installed = {}
    if installed_file.is_file() and not installed_file.is_symlink():
        installed = {entry["target"]: entry["sha256"]
                     for entry in json.loads(installed_file.read_text(encoding="utf-8")).get("files", [])}
    operations = []
    for entry in manifest["files"]:
        destination = target_path(hub, entry["target"])
        current = digest(destination) if destination.is_file() else None
        if entry["policy"] == "create-if-missing":
            action = "create" if current is None else "keep"
        else:
            action = decide(current, installed.get(entry["target"]), entry["sha256"])
        operations.append({"target": entry["target"], "action": action,
                           "current_sha256": current, "incoming_sha256": entry["sha256"]})
    payload = {"manifest": manifest, "operations": operations}
    payload["plan_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def apply(source, hub, confirmed_plan):
    hub = hub.resolve()
    plan = preview(source, hub)
    if plan["plan_sha256"] != confirmed_plan:
        raise ValueError("plan changed; preview again before applying")
    conflicts = [row["target"] for row in plan["operations"] if row["action"] == "conflict"]
    if conflicts:
        raise ValueError("conflicting local changes: " + ", ".join(conflicts))
    entries = {entry["target"]: entry for entry in plan["manifest"]["files"]}
    changed = [row for row in plan["operations"] if row["action"] in {"create", "replace"}]
    operation_id = uuid.uuid4().hex
    backup_root = hub / ".local" / "hub-release" / "backups" / operation_id
    staging = Path(tempfile.mkdtemp(prefix="hub-release-"))
    applied = []
    try:
        for row in changed:
            entry = entries[row["target"]]
            staged = staging / row["target"]
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root(source) / entry["source"], staged)
            os.chmod(staged, entry["mode"])
        for row in changed:
            target = target_path(hub, row["target"])
            backup = backup_root / row["target"]
            if target.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging / row["target"], target)
            applied.append((target, backup if backup.exists() else None))
        state = hub / ".local" / "hub-release"
        state.mkdir(parents=True, exist_ok=True)
        state.joinpath("installed.json").write_text(json.dumps(plan["manifest"], sort_keys=True, separators=(",", ":")), encoding="utf-8")
        return {"operation_id": operation_id, "changed": [row["target"] for row in changed]}
    except Exception:
        for target, backup in reversed(applied):
            if backup is None:
                target.unlink(missing_ok=True)
            else:
                os.replace(backup, target)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "check"):
        command = commands.add_parser(name)
        command.add_argument("--source", required=True, type=Path)
        if name == "check":
            command.add_argument("--manifest", required=True, type=Path)
    preview_command = commands.add_parser("preview")
    preview_command.add_argument("--source", required=True, type=Path)
    preview_command.add_argument("--hub", required=True, type=Path)
    apply_command = commands.add_parser("apply")
    apply_command.add_argument("--source", required=True, type=Path)
    apply_command.add_argument("--hub", required=True, type=Path)
    apply_command.add_argument("--confirm-plan", required=True)
    args = parser.parse_args()
    if args.command == "preview":
        emit(preview(args.source, args.hub))
        return 0
    if args.command == "apply":
        emit(apply(args.source, args.hub, args.confirm_plan))
        return 0
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