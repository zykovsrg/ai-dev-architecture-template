---
name: task-finish
type: mixed
description: |
  Use when checking whether a task can be closed and, after explicit user confirmation, cleaning up task context.
  Activates when:
  - the user asks whether the task is complete
  - the user says "проверь, можно ли закрыть задачу", "можно ставить done", or similar
  - implementation and review are finished and closure decision remains
  - implementation or review suggests the current task may be complete
  - the user explicitly confirms that the task is completed and asks to clean up
  Does NOT activate for:
  - writing code
  - starting a new task
  - cleanup before explicit user confirmation
  - tasks with unresolved blocking risks
---

# Task Finish

Open this skill before applying task-finish. Do not rely on memory.

This skill has two phases.

## Phase 1 — Check

Read:

- `ai/current-task.md`
- current diff
- `ai/decisions.md` if the task touched architecture, data model, storage, signing, sandboxing, undo behavior, sync, new services, or durable invariants
- `ai/future-tasks.md` only if the task produced out-of-scope follow-up ideas or the user asked to save future tasks

Do not edit files without user confirmation.

Answer:

1. Are Done criteria completed?
2. What checks are still needed?
3. Can Status be changed to done?
4. What should be moved to `ai/changelog.md`?
5. Should anything be added to `ai/decisions.md`?
6. Are there TEMP diagnostics or workarounds that need a removal task?
7. Which out-of-scope ideas, missing test seams, follow-up investigations, or non-blocking improvements should be proposed for `ai/future-tasks.md`?
8. Can `ai/current-task.md` be cleaned after user confirmation?

## Changelog vs decisions vs future tasks

Use `ai/changelog.md` for what changed recently.

Use `ai/decisions.md` for durable rules future agents must not break.

Use `ai/future-tasks.md` for ideas and future implementation tasks that were not part of the completed task scope.

Add or propose a decision when the task introduced or exposed a long-term rule about:

- data model;
- storage location or migration;
- signing, sandboxing, entitlements, deployment, or environment setup;
- undo or redo behavior;
- sync behavior;
- recurrence or scheduling behavior;
- external APIs;
- project architecture;
- agent workflow that must persist across sessions.

Do not add minor implementation details to `ai/decisions.md`.

Do not add new scope to the completed task just because a future task was discovered.

## Rules

- If implementation or review suggests the task is complete, propose this check instead of declaring the task closed.
- Do not mark the task as done if manual UI checks are still required.
- Do not mark the task as done if required automated tests were not added, not run, or not explicitly replaced with a justified manual checklist.
- Do not clean `ai/current-task.md` without user confirmation.
- If there are open risks, keep Status as review or blocked.
- If the task created a durable architecture, product, workflow, data model, storage, signing, sandboxing, sync, or undo rule, suggest adding it to `ai/decisions.md`.
- If an issue was only mitigated and root cause is unproven, record that clearly in `ai/changelog.md`.
- If an idea is useful but outside the current task, propose adding it to `ai/future-tasks.md` instead of implementing it during cleanup.

## Phase 2 — Cleanup

Use only after explicit user confirmation.

Do not change application code.

Steps:

1. Add a short summary to `ai/changelog.md`.
2. If the task introduced an important architecture, product, data model, workflow, storage, signing, sandboxing, sync, undo, or agent-process decision, add it to `ai/decisions.md`.
3. If the user confirmed future task candidates, append them to `ai/future-tasks.md`.
4. If temporary diagnostics remain, keep removal criteria in `ai/current-task.md` Done criteria or handoff notes. Record retained diagnostics in `ai/changelog.md` only during confirmed cleanup if the retention is notable. Do not write TEMP diagnostics cleanup work to `ai/paused-tasks.md`.
5. Clean `ai/current-task.md`.
6. Leave a blank template for the next task in `ai/current-task.md` with `Status: empty` and `Stage: intake`.

Rules:

- Do not edit application files.
- Do not change code.
- Do not remove important unresolved risks.
- If there are unresolved risks, move them to changelog, future-tasks, or leave them in the new task template depending on whether they are completed history, future ideas, or blocking current context. Use `ai/paused-tasks.md` only for paused active work created through `task-switch`.
- Do not add minor implementation details to `ai/decisions.md`.
