# Knowledge Layer and Quality Cycle Design

## Goal

Add a local, file-based knowledge library to every new AI Development Architecture project. It preserves the existing task-memory model and adds an explicit, user-controlled quality review for durable project knowledge.

## Scope

Every newly installed standalone project and every new hub-created project has:

```text
knowledge/
  research/
  decisions/
  risks/
  runbooks/
```

The folders are present by default but their content is never automatically loaded, indexed, generated, or inferred from a conversation.

Existing hub projects remain unchanged until the user confirms a project-scoped `hub-knowledge-enable` workflow. Hub routing and per-project confirmation remain mandatory for every such migration. Legacy standalone-project migration is explicitly out of scope.

## Record Format

Each record is one Markdown file. Its frontmatter includes `type`, `status`, `created`, `reviewed`, and `sources`. The type is one of `research`, `decision`, `risk`, or `runbook`; the status is `draft`, `verified`, `needs-review`, `stale`, or `superseded`.

The body records the statement, supporting evidence, scope, and links to related records. `project-context.md` remains the short start-of-session map; it may link to a knowledge record but must not duplicate its evidence.

## Workflows

`hub-knowledge-capture` creates or updates a record only when the user explicitly asks or confirms it during a current task. It uses the project-local `knowledge/` directory only.

`hub-knowledge-review` examines an explicitly selected record, folder, or the records linked from the just-finished task. It checks source dates, statuses, and explicit contradictions. It proposes a review result but does not edit any record until the user confirms the exact changes.

`hub-task-finish` may offer, but never start, `hub-knowledge-review` after the normal completion check. Declining has no effect on task closure.

`hub-knowledge-enable` is a hub-managed, read-minimal workflow for an existing confirmed project. It first shows the exact project and the four directories to be created, then requires confirmation before creating empty scaffold files.

## Boundaries and Safety

- No background scans, auto-capture, semantic index, MCP service, or cloud provider is part of this change.
- A knowledge record never crosses project boundaries.
- Secrets and personal or client data remain prohibited from records.
- Status is evidence-based; uncertain statements remain `draft` or `needs-review`.
- A stale or superseded record is retained with a link to its replacement; it is not silently deleted.

## Files and Verification

The change updates the standalone and hub templates, corresponding entry rules and workflow skills, installer/updater documentation, and smoke tests.

Tests verify that fresh installs and hub-created projects contain the scaffold, while normal updates do not create or mutate knowledge data in existing projects. They also verify that `hub-task-finish` only offers review and that a knowledge review requires explicit confirmation before a write.

## Token Impact

Entry files receive only a short routing rule. Knowledge folders, records, and skills load on demand, so normal task-start context does not grow. Review work uses only a selected record set rather than a whole-project scan.
