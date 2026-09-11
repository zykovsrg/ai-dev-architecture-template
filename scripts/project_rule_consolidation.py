#!/usr/bin/env python3
"""Preview or apply safe cleanup of exact known legacy project-rule copies."""

import argparse
import hashlib
import re
from pathlib import Path


RULE_FILES = ("AGENTS.md", "CLAUDE.md", "ai/architecture.md")
# Git blob IDs of exact generic project-rule files that were distributed before
# the Hub-only migration. Keeping fingerprints instead of source copies lets the
# migration recognize old files without retaining a second distributable tree.
LEGACY_RULE_BLOBS = {
    "AGENTS.md": {
        "becbbbf18ad656f5fff70e578ae458d548b493db",  # retired template copy
        "418a30f6e45a537734584df1cb8695ef5bc4e7b5",  # pre-retirement repo copy
    },
    "CLAUDE.md": {
        "a83c9f790a7ad1b4f572b9553b89cbaaccb97adb",  # retired template copy
        "0afeb0e77311247edc27225a55a5cb766f6a9d16",  # pre-retirement repo copy
    },
    "ai/architecture.md": {
        "46d8cd64721ad7de61b6108ec56341dca20ac9d9",  # retired template copy
        "793fe11e98a3668d1d4d9a4915b2295422fe82fb",  # pre-retirement repo copy
    },
}
# Additional exact architecture payloads observed in older installations before
# blob IDs were recorded. These are content SHA-256 fingerprints only.
OLD_ARCHITECTURE_HASHES = {
    "d62b4e706f2b95a90339af0ddd2b42349f1e64057ddf6a457f71d395c7d996b3",
    "dd4769e912fc34efcad7bffe34baae8689de44e3474e939dc28cc79b6f61b255",
}


def git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def render_entry():
    return (Path(__file__).resolve().parents[1] / "hub-template" / "ai" / "skills"
            / "hub-project-register" / "resources" / "registered-project-entry.md").read_text(encoding="utf-8")


def render_architecture_entry():
    return (Path(__file__).resolve().parents[1] / "hub-template" / "ai" / "skills"
            / "hub-project-register" / "resources" / "registered-project-architecture.md").read_text(encoding="utf-8")


def eligible_files(_source_root, project):
    eligible = []
    for relative in RULE_FILES:
        current = project / relative
        if not current.is_file() or current.is_symlink():
            continue
        data = current.read_bytes()
        if git_blob_id(data) in LEGACY_RULE_BLOBS[relative]:
            eligible.append(relative)
            continue
        if relative == "ai/architecture.md" and hashlib.sha256(data).hexdigest() in OLD_ARCHITECTURE_HASHES:
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
    changed = 0
    for project_id, project in registered_projects(args.hub):
        files = eligible_files(source_root, project)
        if not files:
            continue
        print(f"{project_id}: {', '.join(files)}")
        if args.apply:
            for relative in files:
                entry = render_architecture_entry() if relative == "ai/architecture.md" else render_entry()
                (project / relative).write_text(entry, encoding="utf-8")
                changed += 1
    if args.apply:
        print(f"updated {changed} files")


if __name__ == "__main__":
    main()
