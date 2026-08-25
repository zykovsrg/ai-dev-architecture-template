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

One generated Markdown file is the chosen mechanism. It is rendered as a board
by the already installed `obsidian-kanban` plugin; no new plugin or script gets
direct access to project data.

The board location in the permanent local vault copy is:

```text
obsidian-vault/Obsidian/Projects-Kanban.md
```

The adjacent manifest is:

```text
obsidian-vault/Obsidian/Projects-Kanban.manifest.json
```

The first write creates these two files once. A later update replaces these same
two generated files only after a new preview and explicit write confirmation.
It never creates duplicate boards. `obsidian-vault/` is local-only and ignored
by Git.

## Board columns and safe classification

The board has one card per registered project and seven columns:

1. `Incoming` — no safely chosen next work, or a legacy/unclear task record.
2. `Planned` — no active work and a canonical ready future task exists.
3. `Active` — a canonical current task or subtask is actionable.
4. `Waiting` — canonical waiting exists and no other actionable work exists.
5. `Paused` — work is intentionally paused and no active work overrides it.
6. `Completed` — only a canonical completed project status may use this column.
7. `Archived` — a registered project has status `archived`.

For a legacy or unclear task record, the card is placed in `Incoming` with the
label `нужно проверить`. It shows no guessed next action. This preserves the
meaning of the source file and prevents accidental task migration.

Adding `Archived` is a user-approved extension to the previously documented
six columns. Before implementation, the durable architecture decision that
lists the columns must be updated through the separate `architecture-update`
workflow and its confirmation gate.

## Card contents

Each card contains only derived, read-only information:

- project name and short purpose from the project card;
- computed board column and a short status;
- primary archiproject and contribution only when present and valid;
- nearest explicit due date, otherwise `нет срока`;
- blocker and waiting summary only when structurally valid;
- up to seven clearly derived next actions.
- every valid future `idea` entry in a separate nested `💡 Идеи / backlog`
  block. Ideas do not determine the project column; `blocked`, `promoted`,
  `done`, and `dropped` entries remain hidden.

If fewer than three safe actions exist, the remaining places explicitly say
`нет следующего действия`. Archived cards show only name, purpose, and status.
Neither a legacy checkbox nor an old Kanban item becomes a task.

## Preview, write, and manual-edit flow

1. The agent reads only the confirmed source scope and builds the board in
   memory.
2. It shows the preview, exact source IDs, target paths, and warnings.
3. It shows a write diff for the board and manifest.
4. The user gives a new explicit confirmation for those exact two writes.
5. The agent writes the generated files and reports verification.

The manifest stores only format version, generation time, source project IDs,
source paths, and control hashes. It does not become a global copy of task or
knowledge text.

A manual card edit is a proposal signal, not synchronization. During a later
confirmed update, the agent compares the board with the manifest, shows the
possible canonical change as a precise diff, and waits for separate approval.
Until then, the architecture stays unchanged.

## Failure handling and verification

Missing source files, a path outside the allowed roots, a symlink escape, an
unclear state, or a stale confirmation blocks writing. The preview shows the
affected card and reason instead of guessing.

Before any future write, verification must prove that:

- one source project creates one card;
- the same input rebuilds the same board without duplication;
- archived projects use only `Archived`;
- unclear records use `Incoming` with `нужно проверить`;
- generated Markdown and manifest are the only files that change;
- manual edits create proposals and never change canonical tasks automatically.

## Later migration to the original vault

The original vault is not read, moved, or changed in this phase. After the
copied-vault board is proven safe, a separate future phase may propose moving
the original vault into an approved architecture-owned path. It must first show
the exact target path, complete file list, backup, effects on links and sync,
rollback, and then receive a separate explicit confirmation.
