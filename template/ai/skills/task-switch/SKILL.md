---
name: task-switch
type: mixed
description: |
  Use when task-intake detects that the current task is unfinished and the user asks to start a different task, pause the current task, replace it, promote a future task, or switch focus.
  Activates when:
  - task-intake classifies the request as a different task while ai/current-task.md is unfinished
  - ai/current-task.md contains an unfinished task and the user asks for a different task
  - user says "переключимся", "давай другую задачу", "поставим на паузу", "сейчас срочно другое", or similar
  - the user wants to pause, replace, resume a task, or promote a task from ai/future-tasks.md
  Does NOT activate for:
  - finishing a task; use task-finish instead
  - normal implementation within the same task
  - review of the same task
  - architecture updates unless the task itself is switching architecture work
---

# Task Switch

Open this skill before applying task-switch. Do not rely on memory.

This skill prevents accidental loss of task context.

Use it when `task-intake` decides that `ai/current-task.md` contains an unfinished task and the user is asking for a different task.

Use it also when the user explicitly promotes an entry from `ai/future-tasks.md` into the current task.

## How to decide whether this is a different task

A new request is a different task by default.

It is the same task ONLY if it fits the recorded Done criteria of the current
task: it directly advances them, fixes or adjusts work just produced for this
task, runs tests, checks, or review of this same work, or answers the agent's
question.

If the request needs a new Done criterion, it is a different task, even if it
touches the same files or the same UI.

Small iterations stay in the same task only while they serve the recorded
Done criteria. If a request needs a new Done criterion, use the three-option
question from `task-intake` instead of deciding silently.

If unsure, do not guess. Ask the user:

"Похоже, это новая задача, а текущая ещё не закрыта. Переключаемся или продолжаем текущую?"

## Examples

Different task:

- Current task: "Add onboarding screen"; new request: "Fix login crash".
- Current task: "Review payment diff"; new request: "Create release checklist".
- Current task: "Implement settings UI"; new request: "Save this idea for later and start analytics".

Same task (fits the recorded Done criteria):

- Current task: "Add onboarding screen"; new request: "Make the first step clearer".
- Current task: "Fix login crash"; new request: "Run the failing login test again".
- Current task: "Review payment diff"; new request: "Check the same diff for security risks".

Different task even though it looks close:

- Current task: "Add onboarding screen"; new request: "Also add a settings screen" — needs a new Done criterion.
- Current task: "Fix login crash"; new request: "Improve login screen layout" — does not advance the recorded Done criteria.

Future idea, not a switch:

- Current task remains active; user says "запиши на потом". Use `ai/future-tasks.md` instead of replacing current work.

## Future task promotion

A future task becomes active only after explicit user instruction or confirmation.

When promoting a future task:

1. Read `ai/future-tasks.md`.
2. Copy the relevant entry into `ai/current-task.md` as the new task.
3. Set `Status: active`.
4. Set `Stage` to the real next stage: `intake`, `spec`, `planning`, `implementation`, or `review`.
5. Mark the original future task as `Status: promoted` and add a short promotion note.

Do not delete the original future task during promotion. It is deleted later by `task-finish` when the promoted task is closed; if the switch is abandoned, the entry stays in the backlog.

## Phase 1 — Check

Read:

- `ai/current-task.md`
- `ai/paused-tasks.md` if it exists
- `ai/future-tasks.md` only if the new task is being promoted from future tasks

Do not edit files in Phase 1.

Return:

1. Current unfinished task.
2. Current Status and Stage.
3. New requested task.
4. Why `task-intake` classified it as a different task.
5. Risk of switching.
6. Recommended option:
   - continue current task;
   - pause current task and start a new one;
   - finish current task through `task-finish`;
   - discard current task and replace it;
   - promote a future task into `ai/current-task.md`.
7. What would be written to `ai/paused-tasks.md` if the current task is paused.
8. What would be written to `ai/current-task.md` for the new task, including Status and Stage.
9. What would change in `ai/future-tasks.md` if a future task is promoted.

Ask for explicit user confirmation before editing files.

## Phase 2 — Switch

Use only after explicit user confirmation.

Allowed actions:

1. Move a short summary of the unfinished task to `ai/paused-tasks.md`.
2. Replace `ai/current-task.md` with the new task.
3. Mark a promoted future task in `ai/future-tasks.md` as `Status: promoted`.
4. Keep the new task short and structured.
5. Preserve open risks and useful handoff notes.
6. Set `Status: active` for a new active task.
7. Set `Stage` to the real next stage: `intake`, `spec`, `planning`, `implementation`, or `review`.

Do not change application code.

## Rules

- Do not overwrite an unfinished `ai/current-task.md` silently.
- Do not discard task context without explicit user confirmation.
- Do not use this skill to close a task. Use `task-finish`.
- Do not add minor implementation details to `ai/paused-tasks.md`.
- Do not use `ai/paused-tasks.md` as a backlog. Use `ai/future-tasks.md` for future ideas and tasks.
- If the old task is actually complete, recommend `task-finish` instead of task-switch.
- If the user wants a very small interruption inside the same task, keep it in `ai/current-task.md` as a subtask instead of switching.
- Do not implement future tasks during promotion unless the user explicitly asks to start implementation now.
