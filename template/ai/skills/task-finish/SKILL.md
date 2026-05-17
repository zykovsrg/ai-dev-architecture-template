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

This skill has two phases.

## Phase 1 — Check

Read:

- `ai/current-task.md`
- current diff

Do not edit files without user confirmation.

Answer:

1. Are Done criteria completed?
2. What checks are still needed?
3. Can Status be changed to done?
4. What should be moved to `ai/changelog.md`?
5. Should anything be added to `ai/decisions.md`?
6. Can `ai/current-task.md` be cleaned after user confirmation?

Rules:

- If implementation or review suggests the task is complete, propose this check instead of declaring the task closed.
- Do not mark the task as done if manual UI checks are still required.
- Do not mark the task as done if required automated tests were not added, not run, or not explicitly replaced with a justified manual checklist.
- Do not clean `ai/current-task.md` without user confirmation.
- If there are open risks, keep Status as review or blocked.
- If the task created a new architecture or product rule, suggest adding it to `ai/decisions.md`.

## Phase 2 — Cleanup

Use only after explicit user confirmation.

Do not change application code.

Steps:

1. Add a short summary to `ai/changelog.md`.
2. If the task introduced an important architecture, product, data model, workflow, or agent-process decision, add it to `ai/decisions.md`.
3. Clean `ai/current-task.md`.
4. Leave a blank template for the next task in `ai/current-task.md`.

Rules:

- Do not edit application files.
- Do not change code.
- Do not remove important unresolved risks.
- If there are unresolved risks, move them to changelog or leave them in the new task template.
- Do not add minor implementation details to `ai/decisions.md`.
