# File roles

This document explains which files belong to the Hub architecture and which belong to a project's working memory. Terms (modules, events, boundary check) are explained in `docs/concepts.md`.

## 1. Repository layout

`modules/` is the only distributable architecture source. Each module folder has a passport `module.md`; the release manifest is built from the passports' `Installs` lines.

| Path | Module | What it holds | Installed into the Hub as |
|---|---|---|---|
| `modules/core/` | core | Hub entry files, core rules, allowed roots, active project, project router, registry check, compact project index | `AGENTS.md`, `CLAUDE.md`, `.gitignore`, `ai/architecture.md`, `ai/allowed-roots.md`, `ai/active-project.md`, `ai/skills/hub-project-router/`, `scripts/check-hub-registry.sh`, `scripts/read-compact-project-index.sh` |
| `modules/projects/` | projects | registry, cards, archiproject groups, cross-project signals, project skills | `ai/rules/projects.md`, `ai/project-registry.md`, `ai/project-cards/`, `ai/archiprojects.md`, `ai/cross-project-signals.md`, `scripts/archiprojects.py`, six `hub-project-*`/`hub-registry-check`/`hub-local-router-install` skills |
| `modules/tasks/` | tasks | task skills and task-record scripts | `ai/rules/tasks.md`, `hub-task-intake`, `hub-task-switch`, `hub-task-finish`, `hub-environment-check`, `hub-task-overview`, `scripts/task_records.py`, `scripts/read-compact-task-index.py`, `scripts/check-all-task-records.sh`, `scripts/lib/calendar-date.sh` |
| `modules/knowledge/` | knowledge | knowledge skills | `ai/rules/knowledge.md`, `hub-knowledge-enable`, `hub-knowledge-capture`, `hub-knowledge-review`, `hub-info-update` |
| `modules/goals/` | goals | goal registry, goal log, progress counter | `ai/rules/goals.md`, `ai/goals.md`, `ai/goal-log.md`, `hub-goal-progress`, `scripts/count-goal-progress.sh` |
| `modules/learning/` | learning | session review, workflow observations, learning checks | `ai/rules/learning.md`, `ai/workflow-observations.md`, `hub-session-review`, `scripts/workflow_friction.py`, `scripts/check-session-review.py`, `scripts/check-workflow-memory.sh` |
| `modules/calendar/` | calendar | calendar skill; repository-only calendar server source `policy/`, its setup scripts, and tests | `ai/rules/calendar.md`, `hub-calendar`; the server goes to `tools/apple-calendar-policy` through `modules/calendar/scripts/sync-calendar-policy.sh`, not through the manifest |
| `modules/planning/` | planning | day plan and reviews, calendar snapshot and context scripts, tests | `ai/rules/planning.md`, `ai/workflow-context.md`, `hub-workflows`, `scripts/snapshot-calendar.sh`, `scripts/calendar-context.py`, `scripts/calendar_task_sync.py`, `scripts/validate-day-plan-output.py` |
| `modules/obsidian/` | obsidian | board generator and sync; repository-only watcher and tests | `ai/rules/obsidian.md`, `scripts/generate-obsidian-projects-kanban.sh`, `scripts/obsidian-task-sync.sh` |
| `modules/release/` | release | passport only | nothing |
| `scripts/` | release | installer, updater, release engine, passport reader, boundary and consistency checks, smoke tests | nothing |
| `tests/` | release | architecture unit tests | nothing |
| `.github/workflows/` | — | CI | nothing |

The installer also generates `ai/modules.md` from the passports. `ai/`, `knowledge/`, and `CHANGELOG.md` at the repository root are this repository's own project memory and history, not Hub source.

## 2. Hub files

Hub-owned architecture files are `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, `ai/rules/*.md`, `ai/modules.md`, and `ai/skills/*/`. They change only through approved architecture work and the Hub updater. They are never copied into projects.

Hub-managed memory belongs to the Hub, not to any project. The updater creates these files only when they are missing and never replaces or removes an existing one, even when their module is switched off:

- `ai/allowed-roots.md`
- `ai/active-project.md`
- `ai/project-registry.md`
- `ai/project-cards/*`
- `ai/archiprojects.md`
- `ai/cross-project-signals.md`
- `ai/archive/*`
- `ai/goals.md`, `ai/goal-log.md` (goals)
- `ai/workflow-observations.md` (learning)
- `ai/workflow-context.md` (planning)

A project card is metadata, not permission to read a project. A card declares only one archiproject field: `primary_archiproject: <group-id|none>`. A project belongs to exactly one, most specific group and is also a member of every ancestor group.

## 3. Project memory files

These are the working memory of one project. They stay inside the project and change only through the matching workflow. `hub-project-create` writes their starting versions.

<!-- canon:controlled-memory -->
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
<!-- /canon:controlled-memory -->

Optional project files:

- `knowledge/**` — reference records (knowledge module); see `docs/concepts.md`.
- `ai/session-reviews/` — session reviews (learning module).
- `ai/local-router/` — a project-local area index made by `hub-local-router-install`.

`.claude/` and `.codex/` may exist inside a project as tool configuration. They are project-specific, not a copy of the Hub architecture.

## 4. Edit permissions

| File | When it may be changed |
|---|---|
| Hub `AGENTS.md` / `CLAUDE.md` / `ai/architecture.md` / `ai/rules/*` / `ai/skills/*` | only approved architecture work through the Hub updater |
| Hub `ai/modules.md` | never by hand; the installer regenerates it |
| `ai/current-task.md` | `hub-task-intake` records a task only when the file is empty; `hub-task-switch` replaces an unfinished task after confirmation; `hub-task-finish` clears it on close |
| `ai/paused-tasks.md` | `hub-task-switch`; not a backlog or idea list |
| `ai/future-tasks.md` | after the user approves saving an idea; `hub-task-finish` for confirmed candidates; `hub-task-switch` on promotion |
| `ai/project-context.md` | after confirmation, when the project's facts change |
| `ai/decisions.md` | `hub-task-finish` or approved project-memory work, for a durable decision |
| `ai/changelog.md` | `hub-task-finish`; approved project-memory work when needed |
| `knowledge/**` | only `hub-knowledge-capture` or `hub-knowledge-review` (or `hub-knowledge-enable` for the empty scaffold), after exact confirmation |

## 5. Roles of the main files

### Hub `AGENTS.md` and `CLAUDE.md`

Short entry files at the Hub boundary: `AGENTS.md` for Codex, `CLAUDE.md` for Claude Code. They hold first-level routing, safety, and response rules and must match apart from tool names (`check-consistency.sh` checks this).

### Hub `ai/architecture.md`

Core rules only: rule precedence, simplicity and evidence, confirmation and confidence labels, how module rules load, information updates, installation and updates, secrets, and the context-loading budget. Each module's own rules are in `ai/rules/<id>.md`.

### `ai/current-task.md`

One current task for the project. The empty file contains:

```text
Status: empty
Stage: intake
```

`Status` is one word that the task scripts read. Do not write free text like `spec done, planning next` into it; use the handoff notes instead.

### `ai/paused-tasks.md`

Tasks paused through `hub-task-switch`. It is not a backlog and not an idea list.

### `ai/future-tasks.md`

Ideas and later tasks outside the current scope. Do not use it for an unfinished active task (that is `ai/paused-tasks.md`), for past changes (`ai/changelog.md`), or for durable decisions (`ai/decisions.md`).

### `ai/project-context.md`

The project's lasting facts: what it is and its invariants, plus whatever else guides the work (stack, commands, important folders, fragile zones).

### `ai/decisions.md`

Important active decisions that future agents must not accidentally break — for example, a data-model invariant, a storage or migration rule, or an architecture boundary. Not for minor fixes or ordinary change history.

### `ai/changelog.md`

Notable project changes: what changed. `decisions` answers what must not be broken; `future-tasks` answers what can be done later.

## 6. Hub install and update path

Installed Hubs are updated with `scripts/update-installed-hub.sh`, which routes every operation through `scripts/hub_release.py`. Preview and apply must use the same source revision and the confirmed plan hash. See `docs/update.md`. `curl | bash` is not a supported install or update path.
