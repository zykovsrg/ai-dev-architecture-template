#!/usr/bin/env python3
"""Validate the small, deliberately flat session-review document format."""

import argparse
import re
import sys
from pathlib import Path


ENUMS = {
    "Trigger": {"task-close", "user-request"},
    "Coverage": {"complete", "partial"},
    "Result": {"no-issue-observed", "issues-found", "insufficient-evidence"},
}
REQUIRED_HEADERS = (
    "Review ID", "Project ID", "Task ID", "Session ID", "Trigger", "Coverage",
    "Evidence range", "Missing evidence", "Result", "Supplements",
)
REQUIRED_SECTIONS = ("Goal and result", "Findings", "Improvement proposals", "Follow-up")


def fail(message):
    print(f"invalid session review: {message}", file=sys.stderr)
    return 1


def resolve_real(path):
    if path.is_symlink():
        raise ValueError(f"symlink is not allowed: {path}")
    return path.resolve(strict=True)


def parse_headers(text):
    headers = {}
    for line in text.splitlines():
        match = re.fullmatch(r"([A-Za-z ][A-Za-z ]+): (.*)", line)
        if match and match.group(1) in REQUIRED_HEADERS:
            headers[match.group(1)] = match.group(2).strip()
    return headers


def section(text, title):
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else None


def blocks(body, prefix):
    return re.findall(rf"^### ({prefix}\d+)\n(.*?)(?=^### |\Z)", body, re.M | re.S)


def fields(body):
    return {key: value.strip() for key, value in re.findall(r"^([A-Za-z ]+): (.+)$", body, re.M)}


def validate(project_arg, file_arg):
    try:
        project = resolve_real(project_arg)
        review = resolve_real(file_arg)
    except (FileNotFoundError, ValueError) as error:
        return fail(str(error))

    review_dir = project / "ai" / "session-reviews"
    try:
        review.relative_to(review_dir)
    except ValueError:
        return fail("file must be inside project ai/session-reviews")

    text = review.read_text(encoding="utf-8")
    headers = parse_headers(text)
    missing = [key for key in REQUIRED_HEADERS if not headers.get(key)]
    if missing:
        return fail("missing header: " + ", ".join(missing))
    for key, allowed in ENUMS.items():
        if headers[key] not in allowed:
            return fail(f"unsupported {key}: {headers[key]}")
    if headers["Project ID"] != project.name:
        return fail("Project ID must match project directory name")
    if headers["Session ID"] != "unavailable" and not headers["Session ID"]:
        return fail("Session ID must be an actual ID or unavailable")
    if headers["Coverage"] == "complete" and headers["Missing evidence"] != "none":
        return fail("complete coverage requires Missing evidence: none")
    if headers["Coverage"] == "partial" and headers["Missing evidence"] == "none":
        return fail("partial coverage requires a missing evidence description")

    sections = {name: section(text, name) for name in REQUIRED_SECTIONS}
    absent = [name for name, content in sections.items() if content is None]
    if absent:
        return fail("missing section: " + ", ".join(absent))
    if not sections["Goal and result"]:
        return fail("Goal and result must not be empty")

    finding_blocks = blocks(sections["Findings"], "F")
    proposal_blocks = blocks(sections["Improvement proposals"], "P")
    if sections["Findings"] != "none" and not finding_blocks:
        return fail("Findings must be none or F-numbered blocks")
    if sections["Improvement proposals"] != "none" and not proposal_blocks:
        return fail("Improvement proposals must be none or P-numbered blocks")
    if headers["Result"] == "no-issue-observed" and (finding_blocks or proposal_blocks):
        return fail("clean review cannot contain findings or proposals")
    if headers["Result"] == "issues-found" and not finding_blocks:
        return fail("issues-found requires at least one finding")

    finding_ids = set()
    for identifier, body in finding_blocks:
        finding_ids.add(identifier)
        data = fields(body)
        required = ("Observation", "Evidence", "Cause", "Impact")
        if any(not data.get(key) or data[key] == "none" for key in required):
            return fail(f"{identifier} requires observation, evidence, cause and impact")
        if data["Cause"] not in {"observed", "inferred"}:
            return fail(f"{identifier} Cause must be observed or inferred")

    for identifier, body in proposal_blocks:
        data = fields(body)
        required = ("Finding", "Scope", "Change", "Rationale", "Acceptance test", "Recovery", "Disposition")
        if any(not data.get(key) for key in required):
            return fail(f"{identifier} is incomplete")
        if data["Finding"] not in finding_ids:
            return fail(f"{identifier} references an unknown finding")
        if data["Disposition"] not in {"proposed", "accepted", "rejected", "implemented", "effect-verified", "implementation-failed"}:
            return fail(f"{identifier} has unsupported disposition")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--file", required=True, type=Path)
    args = parser.parse_args()
    return validate(args.project, args.file)


if __name__ == "__main__":
    sys.exit(main())
