# File roles

This document explains which files belong to the Hub architecture and which belong to a project's working memory.

## 1. Shared Hub architecture files

Shared routing, security rules, workflows, and architecture updates belong to Personal AI Hub. In this repository, `hub-template/` is the only distributable architecture source.

Key Hub-owned architecture files include:

- `hub-template/AGENTS.md`
- `hub-template/CLAUDE.md`
- `hub-template/ai/architecture.md`
- `hub-template/ai/skills/*/SKILL.md`

They are changed only through approved architecture work. The supported model does not copy these shared files into every project.

`.claude/` and `.codex/` may still exist inside an individual project as tool configuration. They are project-specific configuration, not a second copy of the shared Hub architecture.

## 2. Controlled project memory files

These are the working memory of the specific project and the current task. They stay project-local and may be changed only through the appropriate workflow.

Files:

<!-- canon:controlled-memory -->
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
<!-- /canon:controlled-memory -->

## Optional knowledge layer

`knowledge/` is optional local reference material. It is not controlled task
memory and is not a replacement for `ai/project-context.md`: project context
contains the current stack, commands, invariants, and fragile zones that guide
normal work; knowledge contains deliberately captured research, decisions,
risks, and runbooks.

A normal Hub update does not enable knowledge in an existing project, does not
create project knowledge records, and does not change existing records.

Existing-project knowledge enablement is available only through the Hub's
`hub-knowledge-enable` workflow after the Hub has confirmed the registered project.
Legacy standalone knowledge migration is out of scope.

Knowledge records are created or changed only through `hub-knowledge-capture` or
`hub-knowledge-review`. These are central Hub-owned workflows; generic copies are
not installed into each project. They canonicalize the confirmed project and
selected path, reject absolute paths, traversal and symlink components, and
require every record to remain inside the matching project-local category.

The workflows prohibit secrets, personal data, and client data; rejected
material is omitted or redacted without echoing it. Review validates required
frontmatter, exact type and status vocabularies, record dates, source dates,
contradictions, and type/category agreement. A stale or superseded record is
retained and linked to its replacement. Proposed changes still wait for exact
confirmation.
At task finish, the agent may offer a focused knowledge review when relevant;
it must not start one or edit records without an explicit request and the
required confirmation.

## Hub-managed memory

These files belong to the Hub, not to any registered project's `ai/` directory:

- `ai/allowed-roots.md`
- `ai/active-project.md`
- `ai/project-registry.md`
- `ai/archiprojects.md`
- `ai/project-cards/*`
- `ai/cross-project-signals.md`
- `ai/archive/*`

Hub protected files are its `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`,
and `ai/skills/*/SKILL.md`. The Hub updater can replace managed Hub files under
the release contract, but preserves Hub-managed user memory and project-local
memory. A project card is metadata, not permission to read a project.
Project/task files remain canonical; project cards are metadata only and a link
never grants a project read. Cards may optionally use the all-or-nothing fields
`primary_archiproject:`, `archiproject_contribution:`, and
`related_archiprojects:`; use `none` where absent, and related archiproject links never
add contribution. Waiting is task/subtask-only: do not place a project in
Waiting while other work is actionable.

Project memory remains scoped to one project. Do not copy it into Hub memory or
use a Hub update to overwrite it.

## 3. Edit permissions matrix

| File | When it may be changed |
|---|---|
| Hub `AGENTS.md` / `CLAUDE.md` | only approved architecture work |
| Hub `ai/architecture.md` | only approved architecture work |
| Hub `ai/skills/*/SKILL.md` | only approved architecture work |
| project `.claude/` / `.codex/` | project-specific tool configuration under the project's own rules |
| `ai/current-task.md` | `hub-task-intake`, `implementation`, `hub-task-switch`, `hub-task-finish`; `hub-task-intake` may record the first task, but does not overwrite an unfinished one without `hub-task-switch` |
| `ai/paused-tasks.md` | only `hub-task-switch`; do not use as a backlog, future tasks, or a cleanup-work list |
| `ai/future-tasks.md` | `implementation` after an explicit request to save an idea, `hub-task-finish` after candidates are confirmed, `hub-task-switch` on promotion |
| `ai/project-context.md` | after confirmation, when the stack, commands, structure, data model, invariants, or fragile zones change |
| `ai/decisions.md` | `hub-task-finish` or approved architecture-related project-memory work, when an important durable decision appears |
| `ai/changelog.md` | `hub-task-finish` after confirmation; approved architecture-related project-memory work when needed |
| `knowledge/**` | only `hub-knowledge-capture` or `hub-knowledge-review`, after explicit confirmation of the exact record write or edit |

## 4. Distributable architecture source

`hub-template/` is the only supported distributable architecture source. Shared
Hub files are installed and updated from that tree through the supported Hub
install/release path.

The former standalone distribution tree and project-local shared-rule copies are
retired. Historical documents may still describe them, but they are not current
install/update instructions.

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

### Hub `AGENTS.md`

Short entry file for Codex at the Hub boundary.

Holds first-level routing, security, confirmation, context-loading, and response rules.

### Hub `CLAUDE.md`

Short entry file for Claude Code at the Hub boundary.

It should match Hub `AGENTS.md` in behavior apart from tool-specific wording.

### Hub `ai/architecture.md`

The canonical shared Hub workflow reference. In this repository its source is
`hub-template/ai/architecture.md`.

### `ai/current-task.md`

One current task for the selected project.

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
- `hub-task-finish`

Do not write free text like `spec done, planning next` into `Status`. That is what `Stage` and the handoff notes are for.

### `ai/paused-tasks.md`

A short list of tasks temporarily paused through `hub-task-switch`.

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

### `knowledge/**`

Optional project-local reference material. It is loaded only when the task
explicitly needs it and the Hub workflow permits the selected scope.

## 7. Related workflows

### `hub-environment-check`

Checks Hub/project readiness after the registered project and path are confirmed.

It is not a work mode and not a deep audit.

After the check, the agent may print a short menu of available next commands and
skills. The menu is informational: it does not launch `hub-task-switch`,
`hub-task-finish`, `architecture-update`, or other workflows automatically.

### `hub-task-intake`

Accepts a new working task.

If `ai/current-task.md` is empty, it records the new task in the current memory.

If the current task is unfinished and the user asks for a different one, it hands control to `hub-task-switch`.

If the user asks to save an idea for later, it does not make the idea the current task and uses `ai/future-tasks.md` instead.

### `hub-task-switch`

Protects `ai/current-task.md` from accidental overwriting.

Used when the current task is unfinished and the user asks to move to another one.

Also used when the user explicitly promotes an entry from `ai/future-tasks.md` to the current task.

### `hub-task-finish`

Checks whether the task can be closed.

After user confirmation, it may update `ai/changelog.md`, `ai/decisions.md`, confirmed entries in `ai/future-tasks.md`, and clear `ai/current-task.md`.

After cleanup, the result must be saved: a push to GitHub if GitHub is configured, or a local-only fallback if GitHub is unavailable.

### Hub install/update path

Supported installed-Hub updates use `scripts/update-installed-hub.sh`, which
routes release operations through `scripts/hub_release.py`. Preview and apply
must use the same immutable source revision and confirmed plan hash.

The retired project-local updater entrypoint is not the current updater.
`curl | bash` is not a supported canonical install/update path.

### Superpowers for bugs and complex tasks

Bugs, crashes, regressions, flaky behavior, debug requests, performance problems, and complex tasks may use Superpowers when it is available and appropriate.

Superpowers does not override Hub routing, project confirmation, security, memory isolation, task workflows, or architecture-update rules.
