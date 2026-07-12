# File roles

This document explains which files belong to the architecture rules and which belong to the project's working memory.

## 1. Protected architecture files

These are the rules of the game for AI agents. They must not be changed in a normal task.

Files:

<!-- canon:protected-files -->
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/` (created by the project when needed; absent from the template)
- `.codex/` (created by the project when needed; absent from the template)
<!-- /canon:protected-files -->

`.claude/` and `.codex/` are settings folders of the tools themselves (Claude Code and Codex): permissions, custom commands, hooks. They are program configuration, not instructions for the AI. The template does not include them; they become protected only if you create them.

When they may be changed:

- only in `architecture-update` mode;
- only after explicit user confirmation;
- only when a workflow, a base rule, a skill, the tools list, or the agent's way of working changes.

External skills, init commands, and setup tools may propose changes to these files but must not apply them without confirmation.

## 2. Controlled memory files

These are the working memory of the specific project and the current task. They may be changed, but only through the appropriate workflow.

Files:

<!-- canon:controlled-memory -->
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
<!-- /canon:controlled-memory -->

## 3. Edit permissions matrix

| File | When it may be changed |
|---|---|
| `AGENTS.md` | only `architecture-update` after confirmation |
| `CLAUDE.md` | only `architecture-update` after confirmation |
| `ai/architecture.md` | only `architecture-update` after confirmation |
| `ai/external-tools.md` | only `architecture-update` or after a confirmed change to the tools list |
| `ai/skills/*/SKILL.md` | only `architecture-update` after confirmation |
| `.claude/` | only `architecture-update` after confirmation |
| `.codex/` | only `architecture-update` after confirmation |
| `ai/current-task.md` | `task-intake`, `implementation`, `task-switch`, `task-finish`; `task-intake` may record the first task, but does not overwrite an unfinished one without `task-switch` |
| `ai/paused-tasks.md` | only `task-switch`; do not use as a backlog, future tasks, or a cleanup-work list |
| `ai/future-tasks.md` | `implementation` after an explicit request to save an idea, `task-finish` after candidates are confirmed, `task-switch` on promotion |
| `ai/project-context.md` | after confirmation, when the stack, commands, structure, data model, invariants, or fragile zones change |
| `ai/decisions.md` | `task-finish` or `architecture-update`, when an important durable decision appears |
| `ai/changelog.md` | `task-finish` after confirmation; `architecture-update` when an approved architecture change requires it |

## 4. Template files

These files are usually identical across projects:

- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`

## 5. Project files

These files must be filled in for the specific project:

- `ai/project-context.md`
- `ai/current-task.md`

These files may stay as empty templates until real data appears:

- `ai/decisions.md`
- `ai/changelog.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`

## 6. Roles of the main files

### `AGENTS.md`

Short entry file for Codex.

Holds only first-level rules: work modes, context routing, file protection, and the response format.

### `CLAUDE.md`

Short entry file for Claude Code.

It should match `AGENTS.md` in meaning.

### `ai/architecture.md`

The main workflow reference.

It is read when a task concerns the development architecture, rule conflicts, or `architecture-update` mode.

### `ai/current-task.md`

One current task.

The empty template must contain:

```text
Status: empty
Stage: intake
```

`Status` shows the task state:

- `empty`
- `active`
- `review`
- `blocked`
- `done`
- `paused`

`Stage` shows the work stage:

- `intake`
- `spec`
- `planning`
- `implementation`
- `review`
- `task-finish`

Do not write free text like `spec done, planning next` into `Status`. That is what `Stage` and the handoff notes are for.

### `ai/paused-tasks.md`

A short list of tasks temporarily paused through `task-switch`.

It is not a backlog, not an idea list, and not a place for cleanup work.

### `ai/future-tasks.md`

A list of ideas and future tasks outside the current scope.

It is a backlog, but not active work.

Use it for:

- ideas that came up during implementation or review;
- non-blocking follow-up investigations;
- missing test seams, if they are useful but not part of the current task;
- large improvements or refactorings for later;
- explicit user requests: "save it for later", "add it to future tasks", "we should do this later".

Do not use it for:

- an unfinished active task — that is what `ai/paused-tasks.md` is for;
- the history of changes already made — that is what `ai/changelog.md` is for;
- durable decisions — that is what `ai/decisions.md` is for;
- blocking cleanup without which the current task cannot be closed.

### `ai/project-context.md`

The project's persistent context:

- stack;
- run, build, and test commands;
- important folders;
- screens or modules;
- data model;
- invariants;
- fragile zones.

If the agent finds the project context stale, it must propose a separate update after confirmation, not just mention it in the changelog.

### `ai/decisions.md`

Only important active decisions.

Use it for decisions that future agents must not accidentally break.

Examples:

- data model invariant;
- storage path or migration rule;
- signing, sandboxing, entitlements, deployment, or local setup requirement;
- undo or redo invariant;
- sync behavior;
- recurrence, scheduling, or time logic;
- architecture boundary;
- agent workflow rule that must persist across sessions.

Do not use it for minor bugfixes, colors, spacing, or ordinary change history.

### `ai/changelog.md`

Recent notable project changes.

The guideline is to keep the last 2–4 weeks. Move older entries to `ai/archive/`.

`changelog` answers: what changed.

`decisions` answers: what must not be forgotten or broken in the future.

`future-tasks` answers: what can be done later but should not be mixed into the current task.

### `ai/external-tools.md`

The list of expected external skills, tools, and controlled methodologies.

Needed by `environment-check`.

Missing optional tools are a warning, not a blocker.

### `ai/skills/*/SKILL.md`

Reusable procedures.

There is no need to load all skills at once. Open only the skill needed for the current task.

If a task matches a skill's trigger, the agent must open the current skill file. Do not work from memory.

## 7. Related workflows

### `environment-check`

Checks the architecture installation, base skills, expected external tools, and controlled methodologies.

It is not a work mode and not a deep audit.

It runs on a new session, a new chat, a tool/agent switch, and after compressed context or a restored summary.

After the check, the agent must print a short menu of available next commands and skills. The menu is informational: it does not launch `task-switch`, `task-finish`, `architecture-update`, or other workflows automatically.

### `task-intake`

Accepts a new working task.

Used before real work, after `environment-check`.

If `ai/current-task.md` is empty, it records the new task in the current memory.

If the current task is unfinished and the user asks for a different one, it hands control to `task-switch`.

If the user asks to save an idea for later, it does not make the idea the current task and uses `ai/future-tasks.md` instead.

### `task-switch`

Protects `ai/current-task.md` from accidental overwriting.

Used when the current task is unfinished and the user asks to move to another one.

Also used when the user explicitly promotes an entry from `ai/future-tasks.md` to the current task.

### `task-finish`

Checks whether the task can be closed.

After user confirmation, it may update `ai/changelog.md`, `ai/decisions.md`, confirmed entries in `ai/future-tasks.md`, and clear `ai/current-task.md`.

After cleanup, the result must be saved: a push to GitHub if GitHub is configured, or a local-only fallback if GitHub is unavailable.

### `release-check`

Checks readiness for a commit, merge, build, or release.

For complex changes it must check whether `code-review-graph` is needed.

### Superpowers for bugs and complex tasks

The local `bugfix-workflow` is no longer used.

Bugs, crashes, regressions, flaky behavior, debug requests, performance problems, and complex tasks should go through Superpowers when it is available.

If Superpowers is missing, the agent must say so and ask whether to install/configure it or continue manually.
