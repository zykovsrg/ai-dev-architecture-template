#!/usr/bin/env python3
"""Keep daily workflow observations pending until an explicit disposition."""

import argparse
import fcntl
import hashlib
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path


def observation_id(day, ordinal, text):
    return hashlib.sha256(f"{day}\0{ordinal}\0{text}".encode("utf-8")).hexdigest()


def _inside(path, root):
    return path == root or root in path.parents


def _cache_directory(hub, *, create=False):
    hub_root = Path(hub).resolve(strict=True)
    current = hub_root
    for part in ("ai", "tmp", "workflow-friction"):
        current = current / part
        if current.is_symlink():
            raise ValueError("workflow friction cache path must not contain symlinks")
        if current.exists():
            if not current.is_dir():
                raise ValueError("workflow friction cache path must contain directories only")
        elif create:
            current.mkdir()
    resolved = current.resolve(strict=False)
    if not _inside(resolved, hub_root):
        raise ValueError("workflow friction cache must stay inside Hub")
    return current


def _regular_cache_file(directory, name, label):
    root = directory.resolve(strict=False)
    path = directory / name
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    if not _inside(path.resolve(strict=False), root):
        raise ValueError(f"{label} must stay inside workflow friction cache")
    if path.exists() and not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f"{label} must be a regular file")
    return path


def friction_dir(hub, *, create=False):
    return _cache_directory(hub, create=create)


def source_file(hub, day):
    if not __import__("re").fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("day must be YYYY-MM-DD")
    return _regular_cache_file(friction_dir(hub), f"{day}.txt", "workflow friction source")


def read_source(hub, day):
    source = source_file(hub, day)
    text = source.read_text(encoding="utf-8") if source.exists() else ""
    return source, text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def state_file(hub, day):
    return _regular_cache_file(friction_dir(hub), f"{day}.state.json", "workflow friction state")


def load_state(hub, day):
    path = state_file(hub, day)
    if not path.exists():
        return {"format": 1, "entries": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("format") != 1 or not isinstance(state.get("entries"), dict):
        raise ValueError("invalid workflow friction state")
    return state


def list_pending(hub, day):
    _, text, source_sha = read_source(hub, day)
    state = load_state(hub, day)
    return {"day": day, "source_sha256": source_sha, "entries": _pending_entries(day, text, state)}


def _pending_entries(day, text, state):
    entries = []
    for ordinal, line in enumerate(text.splitlines(), 1):
        if not line:
            continue
        identifier = observation_id(day, ordinal, line)
        if state["entries"].get(identifier, {}).get("disposition", "pending") == "pending":
            entries.append({"id": identifier, "ordinal": ordinal, "text": line})
    return entries


@contextmanager
def _state_lock(hub):
    directory = friction_dir(hub, create=True)
    lock_path = _regular_cache_file(directory, ".resolve.lock", "workflow friction lock")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(lock_path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("workflow friction lock must be a regular file")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def resolve(hub, day, source_sha, identifier, decision):
    if decision not in {"accepted", "rejected"}:
        raise ValueError("explicit accepted or rejected disposition required")
    with _state_lock(hub):
        directory = friction_dir(hub)
        _, text, actual_sha = read_source(hub, day)
        if actual_sha != source_sha:
            raise ValueError("source changed; list pending observations again")
        state = load_state(hub, day)
        pending = {row["id"] for row in _pending_entries(day, text, state)}
        old = state["entries"].get(identifier, {}).get("disposition", "pending")
        if identifier not in pending and old == "pending":
            raise ValueError("unknown pending observation")
        if old != "pending" and old != decision:
            raise ValueError("conflicting disposition")
        state["entries"][identifier] = {"disposition": decision, "source_sha256": source_sha}
        destination = state_file(hub, day)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as output:
                json.dump(state, output, sort_keys=True, separators=(",", ":"))
                temp_name = output.name
            os.replace(temp_name, destination)
            temp_name = None
        finally:
            if temp_name is not None:
                Path(temp_name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "resolve"):
        command = commands.add_parser(name)
        command.add_argument("--day", required=True)
        if name == "resolve":
            command.add_argument("--source-sha", required=True)
            command.add_argument("--id", required=True)
            command.add_argument("--decision", required=True)
    args = parser.parse_args()
    if args.command == "list":
        print(json.dumps(list_pending(args.hub, args.day), ensure_ascii=False))
    else:
        resolve(args.hub, args.day, args.source_sha, args.id, args.decision)


if __name__ == "__main__":
    main()
