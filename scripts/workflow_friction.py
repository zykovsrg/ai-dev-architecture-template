#!/usr/bin/env python3
"""Keep daily workflow observations pending until an explicit disposition."""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path


def observation_id(day, ordinal, text):
    return hashlib.sha256(f"{day}\0{ordinal}\0{text}".encode("utf-8")).hexdigest()


def friction_dir(hub):
    path = Path(hub) / "ai" / "tmp" / "workflow-friction"
    if path.is_symlink():
        raise ValueError("workflow-friction directory must not be a symlink")
    return path


def source_file(hub, day):
    if not __import__("re").fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("day must be YYYY-MM-DD")
    return friction_dir(hub) / f"{day}.txt"


def read_source(hub, day):
    source = source_file(hub, day)
    text = source.read_text(encoding="utf-8") if source.exists() else ""
    return source, text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def state_file(hub, day):
    return friction_dir(hub) / f"{day}.state.json"


def load_state(hub, day):
    path = state_file(hub, day)
    if not path.exists():
        return {"format": 1, "entries": {}}
    if path.is_symlink():
        raise ValueError("workflow friction state must not be a symlink")
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("format") != 1 or not isinstance(state.get("entries"), dict):
        raise ValueError("invalid workflow friction state")
    return state


def list_pending(hub, day):
    _, text, source_sha = read_source(hub, day)
    state = load_state(hub, day)
    entries = []
    for ordinal, line in enumerate(text.splitlines(), 1):
        if not line:
            continue
        identifier = observation_id(day, ordinal, line)
        if state["entries"].get(identifier, {}).get("disposition", "pending") == "pending":
            entries.append({"id": identifier, "ordinal": ordinal, "text": line})
    return {"day": day, "source_sha256": source_sha, "entries": entries}


def resolve(hub, day, source_sha, identifier, decision):
    if decision not in {"accepted", "rejected"}:
        raise ValueError("explicit accepted or rejected disposition required")
    directory = friction_dir(hub)
    directory.mkdir(parents=True, exist_ok=True)
    _, _, actual_sha = read_source(hub, day)
    if actual_sha != source_sha:
        raise ValueError("source changed; list pending observations again")
    pending = {row["id"] for row in list_pending(hub, day)["entries"]}
    state = load_state(hub, day)
    old = state["entries"].get(identifier, {}).get("disposition", "pending")
    if identifier not in pending and old == "pending":
        raise ValueError("unknown pending observation")
    if old != "pending" and old != decision:
        raise ValueError("conflicting disposition")
    state["entries"][identifier] = {"disposition": decision, "source_sha256": source_sha}
    destination = state_file(hub, day)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as output:
        json.dump(state, output, sort_keys=True, separators=(",", ":"))
        temp_name = output.name
    os.replace(temp_name, destination)


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
