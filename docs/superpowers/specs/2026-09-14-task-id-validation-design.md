# Task ID validation

## Goal

Prevent a task record with an ID that the project parser accepts but the
Obsidian board generator rejects.

## Evidence

The task ID `TASK-zdorove-babushki-2026-09-14-001` was accepted by
`scripts/task_records.py`. The board generator accepts project-scoped task IDs
only when their date uses `YYYYMMDD`, so its full refresh failed.

## Chosen design

Use one strict project-scoped task-ID format everywhere:
`TASK-<project-id>-YYYYMMDD-NNN`.

Update the shared task-record parser to reject dates containing hyphens. Add
regression coverage that proves the valid compact date is accepted and the
hyphenated date is rejected. The existing board validation remains unchanged.

## Alternatives rejected

1. Automatically rewrite malformed IDs during board generation. This silently
   changes canonical task records and can mask data-entry mistakes.
2. Accept both formats in the board generator. This preserves inconsistent
   records and leaves every other consumer to choose its own rule.

## Acceptance criteria

- Every project-scoped task ID uses an eight-digit date.
- The parser rejects a hyphenated date before a board refresh starts.
- Existing valid task-record checks still pass.
