<!-- Superseded by the implemented format-4 contract in [2026-08-28-projects-overview-and-project-boards-design.md](2026-08-28-projects-overview-and-project-boards-design.md). This historical design is preserved unchanged below. -->

# Obsidian projection — phase 2 design

## Status and scope

This is the approved design for the next narrow phase of Obsidian integration.
It does not create or change an Obsidian file, a vault, a task, a deadline, or
a Calendar event.

The AI architecture remains the only source of truth for projects, tasks,
subtasks, waiting, and deadlines. Obsidian is a local human-facing projection.
It is not a second writable task database.

## Confirmed source scope

The board is designed for all 35 registered projects. The confirmed read scope
for its future preview is limited to each registered project card and exactly
these files in each registered project path:

- `ai/current-task.md`
- `ai/future-tasks.md`
- `ai/paused-tasks.md`

It excludes project code, `knowledge/`, existing vault notes, chat records, and
secrets. Two registered projects are archived: `hadassah-content` and
`hadassah-seo-tech`.

The read-only format check found that all agreed files exist. Some legacy task
files use blank or non-standard values such as `complete` or `none`. These
values are not automatically converted or treated as a canonical task state.

## Chosen mechanism

Two generated Markdown views are the chosen mechanism. `Tasks-Kanban.md` is
rendered by the already installed `obsidian-kanban` plugin; `Projects-Overview.md`
is a Markdown table. No new plugin or script gets direct access to project data.

The paths in the permanent local vault copy are:

```text
obsidian-vault/Obsidian/Tasks-Kanban.md
obsidian-vault/Obsidian/Projects-Overview.md
obsidian-vault/Obsidian/AI-Architecture.manifest.json
```

The first write creates these three files once. A later update replaces the same
three generated files only after a new preview and explicit write confirmation.
`obsidian-vault/` is local-only and ignored by Git.

## Task board columns and safe classification

The task board has one card per safely parsed canonical task. Its columns are:

1. `Ideas` — a future entry with status `idea`.
2. `Ready` — a future or current task marked ready.
3. `Active` — the current actionable task.
4. `Waiting` — a task awaiting an external event.
5. `Blocked` — a task with a recorded blocker.
6. `Review` — a task awaiting review.
7. `Paused` — an open paused-task record.
8. `Done` — a canonical completed task.

Legacy or unclear records create no guessed card. `promoted`, `done`, and
`dropped` future entries also do not appear as open task cards.

## Card and project-overview contents

Each task card contains only derived, read-only information: task title,
parent project, status and explicit due date when present. Neither a legacy
checkbox nor an old Kanban item becomes a task.

The project overview has one row per registered project: project name, project
status, current task, ready count, waiting count and nearest explicit due date.
It is a table rather than a second Kanban because project status and task
status are different dimensions.

## Preview, write, and manual-edit flow

1. The agent reads only the confirmed source scope and builds both views in
   memory.
2. It shows the preview, exact source IDs, target paths, and warnings.
3. It shows a write diff for both views and the shared manifest.
4. The user gives a new explicit confirmation for those exact three writes.
5. The agent writes the generated files and reports verification.

The manifest stores only format version, generation time, source project IDs,
source paths, and control hashes. It does not become a global copy of task or
knowledge text.

A manual card or table edit is a proposal signal, not synchronization. During a
later confirmed update, the agent compares both views with the manifest, shows the
possible canonical change as a precise diff, and waits for separate approval.
Until then, the architecture stays unchanged.

## Failure handling and verification

Missing source files, a path outside the allowed roots, a symlink escape, an
unclear state, or a stale confirmation blocks writing. The preview shows the
affected card and reason instead of guessing.

Before any future write, verification must prove that:

- one safe source task creates one card;
- the same input rebuilds both views without duplication;
- every registered project creates one overview row;
- unclear records create no guessed task card;
- the two generated Markdown files and manifest are the only files that change;
- manual edits create proposals and never change canonical tasks automatically.

## Later migration to the original vault

The original vault is not read, moved, or changed in this phase. After the
copied-vault board is proven safe, a separate future phase may propose moving
the original vault into an approved architecture-owned path. It must first show
the exact target path, complete file list, backup, effects on links and sync,
rollback, and then receive a separate explicit confirmation.
