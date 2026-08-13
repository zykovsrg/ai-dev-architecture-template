---
name: knowledge-review
type: review
description: |
  Use on demand to review an explicit knowledge scope inside the currently
  confirmed registered hub project; edits require separate exact confirmation.
---

# Hub Knowledge Review

This is a central hub-owned workflow. Do not copy it or any other generic
workflow into a project. It may act only on the currently confirmed registered
project and cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules.

Every record edit requires explicit confirmation naming the exact path or set.

## Scope and containment

1. Revalidate the confirmed project ID and registered path against the registry
   and require the path to remain a canonical direct child of the sole allowed projects root.
2. Review only one explicit project-relative record, folder, or task-linked set
   whose paths are named in the selected project `ai/` memory. If no scope is
   explicit, ask; do not infer one from conversation history.
3. Resolve the canonical registered project root and require it and
   `knowledge/` to be real directories, not symlinks.
4. Reject absolute paths and any path containing a `..` segment. Also reject
   empty, `.` or ambiguous path segments.
5. Inspect every existing path component with `lstat` and reject any symlink component without following it. Canonicalize only validated components and
   require each selected path to remain in this project's canonical `knowledge/` tree. Do not follow symlink entries in a selected folder.

Stop without reading or writing on any mismatch. Confirmation never authorizes
path traversal, symlink access, another project, or an unregistered path.

## Review contract

For every selected record:

1. Validate the required frontmatter keys: `type`, `status`, `created`, `reviewed`, and `sources`.
2. Require `type` to be exactly `research`, `decision`, `risk`, or `runbook`;
   the type must match its category directory. Require `status` to be exactly `draft`, `verified`, `needs-review`, `stale`, or `superseded`.
3. Validate `created` and `reviewed` as real `YYYY-MM-DD` dates. Report record
   freshness from `reviewed`, using `created` only if review date is absent and
   flagging the missing field.
4. Inspect and report the publication or update date of each cited source separately from record metadata when available. Report missing, malformed,
   unavailable, or unverifiable source dates without inferring them.
5. Report explicit contradictions among selected records and distinguish
   verified evidence from interpretations, unresolved claims, and uncertainty.
6. Flag secrets, personal data or client data. Recommend omission or redaction
   without echoing the rejected value and refer to an approved secure location
   when one exists.
7. Never delete a stale or superseded record. Require it to remain at its
   original path with a link to its replacement under `Related records`; a
   missing replacement link is a review defect.

## Edit gate

Propose exact changes and paths, but make no edit until a separate explicit
confirmation names the intended record or set. After confirmation, repeat all
registry, containment, and symlink checks and make only the confirmed edits.

Do not change hub metadata, another project, project instructions, generic
skills, Git, application code, or unrelated task memory.
