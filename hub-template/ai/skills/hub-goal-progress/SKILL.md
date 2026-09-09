---
name: hub-goal-progress
type: worker
description: Show progress toward numeric hub goals and append one confirmed progress entry to the canonical goal log.
---

# Hub Goal Progress

Use this skill to show progress toward the numeric goals registered in
`ai/archiprojects.md`, or to record one progress entry. It is the only writer
of `ai/goal-log.md`.

## Scope

Read only `ai/archiprojects.md`, `ai/goal-log.md`, and the output of
`scripts/count-goal-progress.sh`. Do not read project code, project memory,
knowledge records, or Git history. Write only `ai/goal-log.md`.

This skill never closes a task, never edits a project task record, and never
touches the calendar.

## Show

Run the counter and render its output unchanged:

```text
bash scripts/count-goal-progress.sh --hub <hub> [--goal <goal-id>] [--as-of <YYYY-MM-DD>]
```

## Record

1. Establish date, `goal_id`, amount, optional project and note from the user.
   Never infer an amount from a task, calendar event or summary.
2. Verify `goal_id` exists and has `kind: goal`. Do not create a goal here.
3. Show the exact prospective log row and append it only after confirmation.
4. Re-run the counter and show updated figures.
5. Commit and report the write.

Entries are append-only. Correcting one requires an explicitly confirmed diff.
