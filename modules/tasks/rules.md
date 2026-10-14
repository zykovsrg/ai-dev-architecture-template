# Tasks Module Rules

## Project Switches And Task Switches

A task switch happens inside an already confirmed project. Use that project's
hub-owned `hub-task-switch` workflow and selected-project `ai/` memory; it is not
a project switch. Do not pause, finish, copy, or rewrite one project's task
memory while switching to another project. A request that mentions two projects
needs separate confirmation for each project and a clear boundary for any
shared output.

## Hub-Managed Project Flow

After an explicit confirmation of a registered project and successful registry
validation, use these central hub-owned skills. They remove any need to copy
`AGENTS.md`, `CLAUDE.md`, or workflow files into each project:

- `hub-environment-check` — read-only readiness and current-state check of the
  selected project's `ai/` memory.
- `hub-task-intake` — records or classifies the requested work in the selected
  project's `ai/current-task.md`.
- `hub-task-switch` — changes an unfinished task directly and reports it, using only the selected project's `ai/` memory.
- `hub-task-finish` — verifies the selected project's task and, when its check
  finds no blocker, first runs the `before-task-close` subscribers listed in
  `ai/modules.md`, then cleans task memory and saves the result. A task with a
  schedule also updates its calendar entry in the same step.

Each shared workflow operates only after a confirmed registered project and
only against that selected project's `ai/` memory or explicitly selected
project-local `knowledge/` paths. It cannot weaken hub routing,
allowed-root, secret, personal/client-data, or memory-isolation rules. It never
reads, writes, pauses, finishes, or copies another project's memory or records.

## Closing Finished Work

When a session finishes and verifies a confirmed project's task (every Done
criterion is met and checked), the agent closes it itself through
`hub-task-finish` before ending its work, without waiting for the user to say
the task is done (user decision 2026-10-07). If any criterion remains, the
task stays open and the agent says in one line what remains.

## Morning Task Check

The session scan (`hub-session-scan`) also checks open current tasks of active
registered projects against their Done criteria. A task closes only when
every criterion has cited session evidence; otherwise it is paused. Paused
tasks stay in work: they keep `Due:` and schedule lines, appear in day plans
and overdue lists, and take part in calendar synchronization.

## Information Updates

For a cross-project meeting or other supplied capture, use `hub-task-overview`
with `capture`: it produces a selectable package of independent proposals
before any write and does not save the source transcript by default. A
project-local info update may refine an existing task only under the
hub-owned `hub-task-intake` rules; a new task or task replacement must use the
hub-owned `hub-task-switch` workflow, while closure uses the hub-owned
`hub-task-finish` workflow.
