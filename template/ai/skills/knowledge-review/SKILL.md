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

## Select the review scope

Review only one explicitly selected scope:

- one record path;
- one folder path; or
- a task-linked set whose record paths are explicitly named in the active task.

If no scope is explicit, ask the user to choose one. Do not infer related
records from conversation history alone.

## Review procedure

1. Read the selected records and only the task context needed to understand a
   task-linked set.
2. For each record, report:
   - freshness from `reviewed` (and `created` when no review date exists);
   - `status`;
   - contradictions with other selected records or clearly labelled unresolved
     claims.
3. Separate verified evidence from interpretations, missing sources, and
   uncertainty.
4. Propose concrete edits with exact paths, but do not apply them.
5. Wait for explicit confirmation that names the intended record or set, for
   example: `Update knowledge/risks/deployment.md as proposed.`

After confirmation, make only the confirmed edits and report the changed paths.
