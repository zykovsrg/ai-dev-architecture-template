---
name: task-intake
type: mixed
description: |
  Use before starting any real user task to decide whether to record a new current task, continue the existing task, or invoke task-switch.
  Activates when:
  - the user gives a new implementation, review, architecture, bug, or investigation request
  - ai/current-task.md is empty and work is about to begin
  - ai/current-task.md is active/review/blocked and the user's request might be a different task
  - the user asks to set, start, capture, or clarify the current task
  Does NOT activate for:
  - environment-check itself
  - task-finish cleanup after the user has already confirmed closure
  - small follow-up questions that do not start or change work
---

# Task Intake

Open this skill before starting a real task. Do not rely on memory.

This skill makes sure the architecture actually captures the user's work in
`ai/current-task.md`.

## Core rule

Before implementation or review work starts, classify the user's request:

1. New task with empty task memory.
2. Continuation of the current task.
3. Different task while current task is unfinished.
4. Future idea, not current work.
5. Bug or complex task that should use Superpowers.

Do not start work until the classification is clear.

## Read

- `ai/current-task.md`
- `ai/paused-tasks.md` only if the current task may need to be paused
- `ai/future-tasks.md` only if the user mentions a future task or backlog item
- `ai/external-tools.md` only if the task is a bug or complex task and Superpowers availability is unclear

## Empty current task

If `ai/current-task.md` has `Status: empty`, create a concise current task before
starting work.

Use this structure:

```markdown
# Current Task

Status: active

Allowed statuses: empty / active / review / blocked / done / paused

Stage: intake

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

implementation / review / task-finish / architecture-update

## Goal

<one short paragraph describing the user's task>

## Use Superpowers

yes / no

## Relevant files

unknown

## Done criteria

- <observable result>

## Agent handoff

Last agent:

What changed:

Open risks:

Next agent should check:
```

Set `Use Superpowers: yes` for bugs, complex tasks, large/vague tasks, data model
changes, migrations, major refactors, TDD-heavy work, or unclear blast radius.

After recording the task, continue in the correct work mode.

## Existing unfinished current task

A new request is a different task by default.

Treat it as a continuation ONLY if it fits the recorded Done criteria of the
current task, meaning at least one of:

1. It directly advances the recorded Done criteria.
2. It fixes or adjusts work just produced for this task.
3. It runs tests, checks, or review of this same work.
4. It answers a question the agent asked.

Everything else is a different task, even if it touches the same files or the
same screen. Do not start work. Ask one question with three options and wait:

```text
Этот запрос выходит за Done criteria текущей задачи. Как поступим?
1. Расширить текущую задачу — я обновлю Goal и Done criteria в ai/current-task.md.
2. Переключиться на новую задачу через task-switch.
3. Записать в ai/future-tasks.md и продолжить текущую задачу.
```

If the user chooses to extend, update `Goal` and `Done criteria` in
`ai/current-task.md` before starting the work. Never grow scope silently.

If the user chooses to switch, stop and invoke `task-switch`. Do not overwrite
`ai/current-task.md` directly.

If the user chooses future-tasks, append the request to `ai/future-tasks.md`
and continue the current task.

## Bugs and complex tasks

This architecture no longer includes a local `bugfix-workflow` skill.

For bugs, regressions, crashes, flaky behavior, performance investigations, or
complex tasks, use Superpowers when it is available.

If Superpowers is missing or not confirmed:

1. Tell the user that this task should normally use Superpowers.
2. Recommend installing/configuring Superpowers as the preferred option; continue with a manual fallback only if the user declines.
3. Do not pretend the local architecture still has a dedicated bugfix workflow.

## Future ideas

If the user only wants to save an idea for later, append it to
`ai/future-tasks.md` when explicitly asked. Do not turn it into current work.

If the idea appears during another task, propose it as a future-task candidate
and wait for confirmation before editing.

## Rules

- Do not start implementation while `ai/current-task.md` is empty.
- Do not silently overwrite an active, review, blocked, or paused task.
- Do not extend the current task without updating Goal and Done criteria first.
- Do not use `ai/paused-tasks.md` as a backlog.
- Do not implement a future task unless the user promotes it to current work.
- Keep the current task short enough to read quickly in a new chat.
- If task memory changed, list the exact controlled memory files in the final report.
