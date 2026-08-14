---
name: hub-knowledge-capture
type: implementation
description: |
  Use on demand to create or update one knowledge record inside the currently
  confirmed registered hub project after exact write confirmation.
---

# Hub Knowledge Capture

This is a central hub-owned workflow. Do not copy it or any other generic
workflow into a project. It may act only on the currently confirmed registered
project and cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules.

## Preconditions and scope

1. Revalidate the confirmed project ID and registered path against the registry
   and require the path to remain a canonical direct child of the sole allowed projects root.
2. Require an active task in the selected project `ai/` memory. Read only its
   `ai/current-task.md` and explicitly relevant records.
3. Require the user to select one type and exact project-relative target path:
   - research → `knowledge/research/`
   - decision → `knowledge/decisions/`
   - risk → `knowledge/risks/`
   - runbook → `knowledge/runbooks/`
4. Require explicit confirmation naming the exact write path before any write.

## Containment preflight

Perform these checks before reading an existing target and again after
confirmation:

1. Resolve the canonical registered project root and require it and
   `knowledge/` to be real directories, not symlinks.
2. Reject absolute paths and any path containing a `..` segment. Also reject
   empty, `.` or ambiguous path segments.
3. Inspect every existing path component with `lstat` and reject any symlink component without following it. For a new file, validate the nearest existing
   parent before constructing the unresolved leaf.
4. Canonicalize only validated components and require the result to remain in
   this selected project's canonical `knowledge/` tree. The canonical target must remain beneath the directory mapped from the selected type.

Stop without reading or writing on any mismatch. Confirmation never authorizes
path traversal, symlink access, another project, or an unregistered path.

## Content contract

Knowledge records must contain no secrets, personal data or client data. Never
store credentials, passwords, tokens, private keys, raw environment values,
personally identifying material, or client-confidential material. Reject,
omit, or redact prohibited content without echoing the rejected value; refer to
an approved secure location when one exists.

The type must be exactly `research`, `decision`, `risk`, or `runbook` and match
the category directory. The status must be exactly `draft`, `verified`,
`needs-review`, `stale`, or `superseded`. New records start as `draft` unless
the selected evidence supports another allowed status.

Never delete a stale or superseded record. Retain it at its original path and
add a link to its replacement under `Related records`; each exact write still
requires confirmation.

## Procedure

1. Show the selected project ID, canonical path, type, exact record path, and a
   concise proposed summary.
2. Validate containment, required frontmatter, data safety, type, status, and
   retention before asking to write.
3. Ask for explicit confirmation naming the exact project-relative record path.
4. After confirmation and repeated validation, create or update only that
   record from `knowledge/record-template.md`.
5. Report the exact changed path, sources or lack of sources, and uncertainty.

Do not change hub metadata, another project, project instructions, generic
skills, Git, application code, or unrelated task memory.
