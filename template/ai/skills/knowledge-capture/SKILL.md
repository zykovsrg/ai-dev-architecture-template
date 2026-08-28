---
name: knowledge-capture
type: implementation
description: |
  Use on demand to propose a new local knowledge record or a change to one.
  Never use it to archive a conversation automatically.
---

# Knowledge Capture

Open this skill before capturing knowledge. The `knowledge/` directory is
optional local reference material, not default task context.

## Required inputs

Before proposing a write, confirm all three:

1. An active task exists in `ai/current-task.md`; otherwise use `task-intake`
   first.
2. The record type and exact project-relative target path are selected:
   - research → `knowledge/research/`
   - decision → `knowledge/decisions/`
   - risk → `knowledge/risks/`
   - runbook → `knowledge/runbooks/`
3. The user has explicitly confirmed the exact write.

Require an explicit `origin` choice: `stated`, `inferred`, or `observation`.
Capture must not default to `stated`. For `origin: observation`, require the
exact target beneath `knowledge/inbox/`; for `stated` and `inferred`, require
the category directory selected by type.

Do not infer a type, create a record, or copy chat content into `knowledge/`
without those inputs.

## Containment preflight

Complete this preflight before reading an existing target or requesting write
confirmation:

1. Resolve the canonical project root from the current selected project and
   require it and its `knowledge/` path to be real directories, not symlinks.
2. Reject absolute paths and any path containing a `..` segment. Also reject
   empty, `.` or ambiguous path segments; the supplied target must remain a
   project-relative Markdown path.
3. Inspect every existing path component with `lstat` and reject any symlink component without following it. For a new file, validate the nearest existing
   parent first and construct the unresolved leaf only after that check.
4. Canonicalize the validated existing parent and require the resulting target
   to remain inside the canonical `knowledge/` tree. The canonical target must remain beneath the directory mapped from the selected type.

Stop without reading or writing when any check fails. Explicit confirmation of
an unsafe path never overrides this boundary.

## Validate before confirmation

Knowledge records must contain no secrets, personal data or client data. Never
store credentials, passwords, tokens, private keys, or raw environment values. Reject or redact secret values before requesting write confirmation; refer to an approved secret-management
location instead of recording a secret. Omit or redact all prohibited content
without echoing the rejected value; this includes personally identifying or
client-confidential material.

Use only these status values: `draft`, `verified`, `needs-review`, `stale`, or
`superseded`. Reject any status outside this vocabulary. New records start as
`draft` unless the selected evidence supports another allowed status.

Use only these type values: `research`, `decision`, `risk`, or `runbook`, and
require the type to match the selected category directory.

Require `valid_from` to be `null` or a real `YYYY-MM-DD` date.

Never delete a stale or superseded record. Retain it at its original path and
add a link to its replacement under `Related records`; creating or changing the
replacement and adding that link require confirmation of the exact edits.

## Procedure

1. Read only the active task and the explicitly relevant existing records that
   passed the containment preflight.
2. Show the proposed type, target path, and a concise summary of the record.
3. Validate the proposed content, type, status, data boundary, and retention
   rule.
4. Ask for confirmation in a form that names the exact path, for example:
   `Write knowledge/research/cache-invalidation.md?`
5. After confirmation, rerun the containment preflight, then create or update
   the record from `knowledge/record-template.md`, preserving its required
   frontmatter and headings.
6. Report the changed path, sources or lack of sources, and any uncertainty.

If the requested content belongs in `ai/project-context.md`, `ai/decisions.md`,
or task memory instead, explain the distinction and follow that file's workflow.
