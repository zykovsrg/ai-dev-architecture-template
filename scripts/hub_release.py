#!/usr/bin/env python3
"""Build and verify a content-addressed manifest for a hub release."""

import argparse
import hashlib
import json
import os
import re
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


def normalize_source_sha(value):
    if value is None:
        return None
    if not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        raise ValueError("invalid source commit SHA")
    return value.lower()


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


def load_installed_manifest(installed_file):
    if installed_file.is_symlink():
        raise ValueError("unsafe installed release metadata")
    if not installed_file.is_file():
        return {"files": []}
    manifest = json.loads(installed_file.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("files", []), list):
        raise ValueError("invalid installed release metadata")
    return manifest


def preview(source, hub, source_sha=None):
    source_sha = normalize_source_sha(source_sha)
    manifest = build_manifest(source)
    hub = hub.resolve()
    installed_file = hub / ".local" / "hub-release" / "installed.json"
    installed_manifest = load_installed_manifest(installed_file)
    installed_entries = {entry["target"]: entry for entry in installed_manifest.get("files", [])}
    incoming_targets = {entry["target"] for entry in manifest["files"]}
    operations = []

    for entry in manifest["files"]:
        destination = target_path(hub, entry["target"])
        current = digest(destination) if destination.is_file() else None
        previous = installed_entries.get(entry["target"])
        previous_sha = previous.get("sha256") if previous else None
        if entry["policy"] == "create-if-missing":
            action = "create" if current is None else "keep"
        else:
            action = decide(current, previous_sha, entry["sha256"])
        operations.append({"target": entry["target"], "action": action,
                           "current_sha256": current, "incoming_sha256": entry["sha256"]})

    for target, previous in installed_entries.items():
        if target in incoming_targets or previous.get("policy") != "managed":
            continue
        destination = target_path(hub, target)
        current = digest(destination) if destination.is_file() else None
        action = decide(current, previous.get("sha256"), None)
        operations.append({"target": target, "action": action,
                           "current_sha256": current, "incoming_sha256": None})

    operations.sort(key=lambda row: row["target"])
    payload = {"manifest": manifest, "operations": operations, "source_sha": source_sha}
    payload["plan_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def apply(source, hub, confirmed_plan, source_sha=None, confirmed_source_sha=None):
    source_sha = normalize_source_sha(source_sha)
    confirmed_source_sha = normalize_source_sha(confirmed_source_sha)
    if source_sha != confirmed_source_sha:
        raise ValueError("source revision changed; apply the reviewed source SHA")
    hub = hub.resolve()
    plan = preview(source, hub, source_sha=source_sha)
    if plan["plan_sha256"] != confirmed_plan:
        raise ValueError("plan changed; preview again before applying")
    conflicts = [row["target"] for row in plan["operations"] if row["action"] == "conflict"]
    if conflicts:
        raise ValueError("conflicting local changes: " + ", ".join(conflicts))

    entries = {entry["target"]: entry for entry in plan["manifest"]["files"]}
    mutations = [row for row in plan["operations"] if row["action"] in {"create", "replace", "remove"}]
    staged_changes = [row for row in mutations if row["action"] in {"create", "replace"}]
    operation_id = uuid.uuid4().hex
    state = hub / ".local" / "hub-release"
    installed_file = state / "installed.json"
    backup_root = state / "backups" / operation_id
    staging = Path(tempfile.mkdtemp(prefix="hub-release-"))
    applied = []
    metadata_backup = None
    metadata_stage = None
    metadata_replaced = False
    try:
        for row in staged_changes:
            entry = entries[row["target"]]
            staged = staging / row["target"]
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root(source) / entry["source"], staged)
            os.chmod(staged, entry["mode"])

        if installed_file.exists():
            backup_root.mkdir(parents=True, exist_ok=True)
            metadata_backup = backup_root / ".installed.json.before"
            shutil.copy2(installed_file, metadata_backup)

        for row in mutations:
            target = target_path(hub, row["target"])
            backup = backup_root / row["target"]
            if target.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            if row["action"] == "remove":
                target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staging / row["target"], target)
            applied.append((target, backup if backup.exists() else None))

        state.mkdir(parents=True, exist_ok=True)
        fd, metadata_name = tempfile.mkstemp(prefix=".installed.", suffix=".tmp", dir=state)
        metadata_stage = Path(metadata_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(plan["manifest"], sort_keys=True, separators=(",", ":")))
            handle.flush()
        os.replace(metadata_stage, installed_file)
        metadata_replaced = True
        metadata_stage = None
        return {"operation_id": operation_id, "changed": [row["target"] for row in mutations]}
    except Exception:
        if metadata_replaced:
            if metadata_backup is None:
                installed_file.unlink(missing_ok=True)
            else:
                os.replace(metadata_backup, installed_file)
                metadata_backup = None
        for target, backup in reversed(applied):
            if backup is None:
                target.unlink(missing_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(backup, target)
        shutil.rmtree(backup_root, ignore_errors=True)
        raise
    finally:
        if metadata_stage is not None:
            metadata_stage.unlink(missing_ok=True)
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
    preview_command.add_argument("--source-sha")
    apply_command = commands.add_parser("apply")
    apply_command.add_argument("--source", required=True, type=Path)
    apply_command.add_argument("--hub", required=True, type=Path)
    apply_command.add_argument("--confirm-plan", required=True)
    apply_command.add_argument("--source-sha")
    apply_command.add_argument("--confirm-source-sha")
    args = parser.parse_args()
    if args.command == "preview":
        emit(preview(args.source, args.hub, source_sha=args.source_sha))
        return 0
    if args.command == "apply":
        emit(apply(args.source, args.hub, args.confirm_plan,
                   source_sha=args.source_sha, confirmed_source_sha=args.confirm_source_sha))
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
