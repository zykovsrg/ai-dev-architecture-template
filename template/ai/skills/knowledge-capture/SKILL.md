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
2. The record type and exact target path are selected:
   - research → `knowledge/research/`
   - decision → `knowledge/decisions/`
   - risk → `knowledge/risks/`
   - runbook → `knowledge/runbooks/`
3. The user has explicitly confirmed the exact write.

Do not infer a type, create a record, or copy chat content into `knowledge/`
without those inputs.

## Procedure

1. Read only the active task and the explicitly relevant existing records.
2. Show the proposed type, target path, and a concise summary of the record.
3. Ask for confirmation in a form that names the exact path, for example:
   `Write knowledge/research/cache-invalidation.md?`
4. After confirmation, create or update the record from
   `knowledge/record-template.md`, preserving its required front matter and
   headings.
5. Report the changed path, sources or lack of sources, and any uncertainty.

If the requested content belongs in `ai/project-context.md`, `ai/decisions.md`,
or task memory instead, explain the distinction and follow that file's workflow.
