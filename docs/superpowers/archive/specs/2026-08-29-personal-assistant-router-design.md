# Personal Assistant Router

## Goal

Make the hub feel like a personal AI assistant. It must answer cross-project
requests such as a day plan or meeting capture without first forcing the user
to select one project. It must preserve explicit approval before any write or
external action.

## Verified problem

The hub already has `hub-workflows` for `day-plan` and `capture`, but the entry
rules route every real request through single-project confirmation first. A
request such as "show my tasks today" is therefore treated as ambiguous project
routing instead of a cross-project day-plan request.

## Chosen design

Keep the existing small workflows. Extend the existing `hub-project-router` so
that it first classifies the user's intent:

1. Personal-assistant request: day plan, overdue or blocked work, weekly or
   evening review, capture of a supplied task or meeting text, or cross-project
   knowledge search.
2. Project request: implementation, review, debugging, or another request
   explicitly scoped to one project.
3. Architecture request: route to the confirmed architecture project.
4. Ambiguous request: ask one concise clarification question.

Personal-assistant requests use `hub-workflows`. They may read the canonical
task memory (`ai/current-task.md`, `ai/future-tasks.md`, and
`ai/paused-tasks.md`) of every active registered project. The answer separates
personal and work items and cites the source project and record. The assistant
does not read project code, full knowledge records, credentials, or arbitrary
files through this path.

Project requests retain the existing exact-project confirmation boundary before
they read project-local memory or code.

## Approval model

Read-only personal-assistant results need no project-by-project confirmation.
Any proposed write, deletion, move, task-state change, calendar operation, or
external operation remains opt-in.

For one capture result, the assistant renders a single package containing
independent named proposals. The user may confirm the package once or remove
individual proposals. Each remaining proposal keeps its exact target and diff;
a changed diff requires a new confirmation.

## Scenarios

### Day plan

"Show my tasks today" is classified as a personal-assistant request. The
assistant reads the canonical task records of all active projects, ranks the
work with the existing `day-plan` rules, separates personal and work, and makes
no change.

### Meeting capture

The user supplies a transcript or summary. The assistant classifies tasks,
decisions, likely projects, deadlines, waiting items, and uncertainty; it then
reads only the canonical task records of the active projects needed to ground
the result. It renders one package of exact proposals and writes only the
selected proposals after one confirmation.

### Work in one project

"Fix the Goal Planner bug" is a project request. Existing routing shows the
registered path and obtains the normal explicit project confirmation before
project-local reads.

## Files and tests

Change the short entry rules in `hub-template/AGENTS.md` and
`hub-template/CLAUDE.md`, detailed policy in `hub-template/ai/architecture.md`,
and the procedures in `hub-template/ai/skills/hub-project-router/SKILL.md` and
`hub-template/ai/skills/hub-workflows/SKILL.md`.

Extend `scripts/hub-smoke-test.sh` with contract checks for intent-first
routing, read-only active-project day plans, the retained project confirmation
boundary, and package confirmation semantics. Refresh user documentation and
the installed hub only after template checks pass.

## Non-goals

Do not build one large replacement workflow, introduce a global persistent
read grant, add a new task source of truth, automatically apply proposals, or
change Calendar permissions. A separate simplification audit is deferred until
the new route is used in real sessions.

## Acceptance criteria

- A day-plan request no longer asks the user to choose a project.
- The response uses canonical records from all active projects and separates
  personal from work.
- A project-specific request still requires normal project confirmation.
- A meeting capture produces one selectable proposal package and no automatic
  write.
- The smoke test covers the boundaries above and passes.
