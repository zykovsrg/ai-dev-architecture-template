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
- `hub-task-switch` — changes an unfinished task only after a separate explicit
  confirmation, using only the selected project's `ai/` memory.
- `hub-task-finish` — verifies the selected project's task and, when its check
  finds no blocker, first runs the `before-task-close` subscribers listed in
  `ai/modules.md`, then cleans task memory and saves the result. Only a task with a
  schedule keeps the joint confirmation with its scheduled entry.

Each shared workflow operates only after a confirmed registered project and
only against that selected project's `ai/` memory or explicitly selected
project-local `knowledge/` paths. It cannot weaken hub confirmation,
allowed-root, secret, personal/client-data, or memory-isolation rules. It never
reads, writes, pauses, finishes, or copies another project's memory or records.

## Information Updates

For a cross-project meeting or other supplied capture, use `hub-task-overview`
with `capture`: it produces a selectable package of independent proposals
before any write and does not save the source transcript by default. A
project-local info update may refine an existing task only under the
hub-owned `hub-task-intake` rules; a new task or task replacement must use the
hub-owned `hub-task-switch` workflow, while closure uses the hub-owned
`hub-task-finish` workflow.
