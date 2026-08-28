---
name: knowledge-review
type: review
description: |
  Use on demand to assess explicitly selected local knowledge records without
  changing them until the user confirms the exact edits.
---

# Knowledge Review

Open this skill before reviewing knowledge. `knowledge/` is optional local
reference material; never review or load the whole directory by default.

## Select and contain the review scope

Review only one explicitly selected scope:

- one project-relative record path;
- one project-relative folder path; or
- a task-linked set whose project-relative record paths are explicitly named
  in the active task.

If no scope is explicit, ask the user to choose one. Do not infer related
records from conversation history alone.

Before any selected record is read, resolve the canonical project root and
require it and `knowledge/` to be real directories, not symlinks. Reject absolute paths and any path containing a `..` segment. Also reject empty, `.` or ambiguous path segments.
Inspect every existing path component with `lstat` and reject any symlink component without following it. Canonicalize only validated components and
require every record or selected folder to remain inside the canonical `knowledge/` tree. For a folder scope, do not follow symlink entries while enumerating it.

Stop without reading or writing when any path fails. Explicit selection or edit
confirmation never overrides this boundary.

## Review procedure

1. Read only selected records that passed the containment checks and only the
   task context needed to understand a task-linked set.
2. Validate the required frontmatter keys: `type`, `status`, `origin`, `valid_from`, `created`, `reviewed`, and `sources`.
3. Require `type` to be exactly `research`, `decision`, `risk`, or `runbook`;
   the type must match its category directory. Require `status` to be exactly `draft`, `verified`, `needs-review`, `stale`, or `superseded`.
4. Validate `created` and `reviewed` as real `YYYY-MM-DD` dates. Report record
   freshness from `reviewed`, using `created` only when a review date is absent
   and reporting that missing field as a defect.
   Validate `valid_from` as `null` or a real `YYYY-MM-DD` date.
   Report `origin: inferred` separately from `origin: stated`; flag an
   observation outside the inbox as a defect.
5. For `sources`, distinguish missing or malformed citations from dated
   evidence. Inspect and report the publication or update date of each cited source separately from the record dates when that date is available; label an
   unavailable or unverifiable source date as unknown rather than inferring it.
6. Report explicit contradictions among selected records and clearly label
   unresolved claims, interpretations, and uncertainty.
7. Flag secrets, personal data or client data. Recommend omission or redaction
   without echoing the rejected value, and refer to an approved secure location
   when one exists. Flag secret content and an invalid status.
8. Never delete a stale or superseded record. Require it to be retained at its
   original path with a link to its replacement under `Related records`; flag a
   missing replacement link as a review defect.
9. Propose concrete edits with exact paths, but do not apply them. Wait for
   explicit confirmation that names the intended record or set, for example:
   `Update knowledge/risks/deployment.md as proposed.`

For an explicitly selected inbox scope, propose only: promote it into one
selected durable category, retain it, or delete it. Each result still needs
exact confirmation before a mutation.

After confirmation, rerun containment checks, make only the confirmed edits,
and report the changed paths. Redaction, retention links, and review-result
edits all require that exact confirmation.
