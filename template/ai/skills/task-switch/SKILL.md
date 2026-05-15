---
name: task-switch
type: mixed
description: |
  Use when the current task is unfinished and the user asks to start a different task, pause the current task, replace it, or switch focus.
  Activates when:
  - ai/current-task.md contains an unfinished task and the user asks for a different task
  - user says "переключимся", "давай другую задачу", "поставим на паузу", "сейчас срочно другое", or similar
  - the user wants to pause, replace, or resume a task
  Does NOT activate for:
  - finishing a task; use task-finish instead
  - normal implementation within the same task
  - review of the same task
  - architecture updates unless the task itself is switching architecture work
---

# Task Switch

This skill prevents accidental loss of task context.

Use it when `ai/current-task.md` contains an unfinished task and the user asks for a different task.

## How to decide whether this is a different task

Treat the new request as a different task if at least one of these is true:

1. The goal changes.
2. The work mode changes.
3. The main relevant files or project area change.
4. The Done criteria change.
5. The new request does not help complete the current task.
6. The new request creates a separate deliverable.
7. The current task would remain unfinished after doing the new request.

Treat the new request as the same task if it clarifies, narrows, tests, reviews, or completes the current goal.

If unsure, do not guess. Ask the user:

"Похоже, это новая задача, а текущая ещё не закрыта. Переключаемся или продолжаем текущую?"

## Phase 1 — Check

Read:

- `ai/current-task.md`
- `ai/paused-tasks.md` if it exists

Do not edit files in Phase 1.

Return:

1. Current unfinished task.
2. New requested task.
3. Risk of switching.
4. Recommended option:
   - continue current task;
   - pause current task and start a new one;
   - finish current task through `task-finish`;
   - discard current task and replace it.
5. What would be written to `ai/paused-tasks.md` if the current task is paused.
6. What would be written to `ai/current-task.md` for the new task.

Ask for explicit user confirmation before editing files.

## Phase 2 — Switch

Use only after explicit user confirmation.

Allowed actions:

1. Move a short summary of the unfinished task to `ai/paused-tasks.md`.
2. Replace `ai/current-task.md` with the new task.
3. Keep the new task short and structured.
4. Preserve open risks and useful handoff notes.

Do not change application code.

## Rules

- Do not overwrite an unfinished `ai/current-task.md` silently.
- Do not discard task context without explicit user confirmation.
- Do not use this skill to close a task. Use `task-finish`.
- Do not add minor implementation details to `ai/paused-tasks.md`.
- If the old task is actually complete, recommend `task-finish` instead of task-switch.
- If the user wants a very small interruption inside the same task, keep it in `ai/current-task.md` as a subtask instead of switching.
