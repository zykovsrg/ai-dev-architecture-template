# Concepts

Simple explanations of the terms used in this architecture.

## Diff

A diff is a list of changes in the code.

It shows:

- which lines were added;
- which lines were removed;
- which lines were changed;
- which files this happened in.

Example:

```diff
- Button: Save
+ Button: Save task
```

The command to view changes not yet staged for a commit:

```bash
git diff
```

The command to view changes already staged for a commit:

```bash
git diff --staged
```

## Work modes

Work modes tell the agent what exactly it should be doing.

- `implementation` — change code.
- `review` — check changes and report problems, but do not edit files.
- `hub-task-finish` — check whether the task can be closed and clean up the context after confirmation.
- `architecture-update` — update the AI development rules, not the application code.

## Confirmed Obsidian task sync

`ai/current-task.md`, `ai/future-tasks.md`, and `ai/paused-tasks.md` are the
only canonical task records. Obsidian Kanban is a local generated view.

After an approved task-memory write, the trusted architecture-to-Obsidian refresh
rebuilds the view with `--write --refresh-from-architecture`. It is
trusted only in that direction and still validates the manifest. A manual
Obsidian edit makes the refresh stop with a pending proposal; it must not
overwrite it.

The reverse direction is a confirmed Obsidian-to-architecture proposal:
scan the local board, inspect it, then apply only the shown hash.

```bash
bash scripts/obsidian-task-sync.sh scan --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault
bash scripts/obsidian-task-sync.sh status --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault
bash scripts/obsidian-task-sync.sh apply --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --confirm-proposal <sha256>
```

A board edit becomes a proposal only when the synchronizer can express it as an
exact canonical change. It supports renaming a card, changing or removing its
explicit due date, moving a future task between `Ideas`, `Ready`, `Blocked`, and
`Active`, moving the current task between `Active`, `Blocked`, and `Review`, and
creating an unchecked card that names a registered project. Everything else is a
blocked proposal to resolve through the architecture: pausing needs
`task-switch`, finishing needs `task-finish`, a paused card cannot change at all,
and a ticked checkbox or an extra card field blocks the whole board rather than
being reverted in silence by the next refresh.

Promoting a future task into `Active` replaces the project's current task. The
replaced task is written to `ai/paused-tasks.md` with its whole recorded body, so
its working state stays readable.

The optional local watcher only runs `scan`; it never applies a proposal. First
preview its user launchd plist. Installation and removal are separate explicit
actions, each with its own confirmation flag:

```bash
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --preview
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --install --confirm-launchd-install
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --status
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --uninstall --confirm-launchd-uninstall
```

`.ai-architecture-sync/` holds only local proposals, locks, and watcher logs;
Git ignores it.

## Optional local knowledge

`knowledge/` is an optional local reference layer. It is different from
`ai/project-context.md`: context stores the current project facts that guide
work, such as the stack, commands, invariants, and fragile zones. Knowledge
stores explicitly captured research, decisions, risks, and runbooks that may
be useful later.

A normal architecture update does not enable knowledge in an existing project:
it never creates `knowledge/` in a pre-knowledge project and never changes
knowledge records. Capturing knowledge is intentional. `hub-knowledge-capture`
first proposes an exact category and path, while `hub-knowledge-review` examines
only an explicitly selected record or set. Neither may create or edit a record
until the user explicitly confirms the exact write.

Existing-project knowledge enablement is available only through the hub's
`hub-knowledge-enable` workflow after the hub has confirmed the registered project.
Legacy standalone knowledge migration is out of scope.

Hub-created projects use central hub-owned `hub-knowledge-capture` and
`hub-knowledge-review` workflows; the hub does not copy generic skills into each
project. Both standalone and hub workflows reject absolute paths, traversal,
and symlink components, and keep records inside the confirmed project's
matching knowledge category. Records must contain no secrets, personal data,
or client data.

Every knowledge record has one of five statuses: `draft`, `verified`,
`needs-review`, `stale`, or `superseded`. `hub-task-finish` may offer a focused
knowledge review if it is relevant to closing the task. An offer is optional
and does not itself authorize reading, reviewing, or changing knowledge.
Review also validates the exact four record types, record and source dates,
type/category agreement, and contradictions. Stale and superseded records stay
in place and link to their replacements.

## Standalone mode and personal hub

Standalone mode is the normal architecture for one project. Its rules and
memory live in that project and it does not depend on a hub.

A personal hub is optional and has its own `_ai-hub` directory. It is a local
router for explicitly registered projects, not a shared project workspace. Its
only permanent project location is `_ai-hub/projects/<project-id>`. The hub
repository ignores `/projects/`, so every project can remain an independent Git
repository with its own history and remote.

A new hub chat shows the registered project and exact path, then waits for
confirmation before reading that project's code or memory. Installing or
updating a hub does not automatically convert projects, clean up files, move
folders, or send reminders. Existing folders are moved only through
`hub-project-migrate`: the user separately confirms a temporary source, reviews an
exact preview, and separately confirms each move or the displayed batch. The
workflow then uses independent gates: move → registration confirmation →
registry validation → optional cleanup confirmation. Cleanup is never automatic
and removes only confirmed old standalone rules; all project memory remains
unchanged.

## Minimalism

Minimalism reduces the burden of understanding, maintaining, and managing a
project. It does not remove safety measures or functionality needed for
correctness, legal compliance, or the user's confirmed goal.

## Project invariants

Project invariants are project rules that must not be broken.

They are the "load-bearing walls" of the project.

Example:

```text
Microtask must belong to a Week Task.
```

Project invariants must be stored in `ai/project-context.md`, not in `AGENTS.md` or `CLAUDE.md`.

## Skills

Skills are reusable procedures for specific tasks.

Examples:

- `ui-review` checks interface changes.
- `security-review` checks security risks.
- `write-tests` decides whether automated tests are needed.
- `hub-task-intake` accepts a new task and records it in the project's current memory.
- `hub-task-finish` safely closes a task.

Skills should be loaded only when needed.

## task-finish

`hub-task-finish` has two phases.

Phase 1 checks whether the task can be closed. No files are edited.

Phase 2 cleans up the context only after user confirmation. It updates:

- `ai/changelog.md`
- `ai/decisions.md`, if needed
- `ai/current-task.md`
- confirmed entries in `ai/future-tasks.md`, if ideas for later came up during the task

`hub-task-finish` must not change application code. After cleanup it must save the result: a push to GitHub if GitHub is connected, or a local-only fallback if GitHub is unavailable.

## architecture-update

`architecture-update` changes the development system itself.

It is not the same as `implementation`.

- `implementation` changes the application.
- `architecture-update` changes the rules by which AI agents work on the application.

Before changing architecture files, the agent must show:

```text
current rule → proposed rule → exact files
```

Then the agent must ask:

```text
Replace this?
```

## Environment check

Environment check is a quick check for the first run or a new session.

The agent checks:

- whether all base architecture files are present;
- whether all base skills are present;
- whether the expected external skills and tools are available: code-review-graph, agent-skills-for-context-engineering, Playwright MCP, and Superpowers;
- whether the local architecture version matches the latest version in the repository; when a newer version exists, the agent offers an update preview but never applies it automatically;
- whether controlled methodologies, such as Superpowers, are present.

It is not an application dependency check. For example, it does not check whether Python packages or npm dependencies are installed.

If base skills are missing, the agent says what to restore from the template. If expected external tools or skills are missing, the agent prints a warning but does not block the work. Nothing is installed without user confirmation.

After the check, the agent must show a menu of available next commands and skills. It is a reference, not a command to run everything.

Example menu:

```text
Available next commands and skills
- task-switch — switch to another task or promote a future task.
- task-finish — check whether the current task can be closed.
- task-intake — accept a new task or decide whether task-switch is needed.
- Superpowers — handle bugs, complex tasks, and tasks with an unclear blast radius.
```

## Skill precedence

The internal architecture takes priority over external skills.

The order is:

1. `AGENTS.md` or `CLAUDE.md`
2. `ai/current-task.md`
3. the relevant base skill
4. optional project skills and expected external skills/tools
5. controlled external methodologies

An external skill must not override the work mode, confirmation rules, task-finish, architecture-update, or the clean architecture principle.

If one development tool has to be chosen, `code-review-graph` takes priority.

Why:
- it is a better fit for code review;
- it computes the blast radius of changes;
- it helps the agent read only the files it needs.

## Superpowers as a controlled methodology

Superpowers is a critical plugin for this architecture: it should be installed in every project. It is used for bugs and large tasks where you first need to clarify the idea, agree on a design, make a plan, use TDD, or split the work between subagents.

Still, Superpowers does not run every small task; it stays a controlled methodology.

It is expected for:
- bugs, regressions, crashes, and performance problems;
- large, vague, or risky tasks;
- tasks that need design work, TDD, or subagents.

It is not used for:
- text edits;
- simple UI fixes;
- task-finish;
- architecture-update without an explicit request.

The main rule:

```text
Our architecture drives the process.
Superpowers strengthens the process only after permission.
```


## environment-check is not a work mode

`hub-environment-check` is a service check for the first run.

It checks:
- base architecture files;
- base skills;
- expected external tools;
- controlled methodologies.

After this check, the agent continues in one of the modes:
- `implementation`
- `review`
- `hub-task-finish`
- `architecture-update`

Before continuing, the agent shows the available next commands and skills. The menu does not launch these workflows automatically.

This keeps the work modes separate from the startup check.


## Task switching

Before a working task, the agent first uses `hub-task-intake`.

`hub-task-intake` looks at `ai/current-task.md` and decides whether to:

- record the first task;
- continue the current one;
- launch `hub-task-switch` if the user asks for a different task;
- save an idea to `ai/future-tasks.md`.

`hub-task-switch` is needed when the current task is not yet closed and the user asks to start another one.

It does not close the old task. Closing is what `hub-task-finish` is for.

What `hub-task-switch` does:

1. Shows the current unfinished task.
2. Shows the new task.
3. Warns about the risk of losing context.
4. Offers options:
   - continue the current task;
   - pause the current task and start the new one;
   - close the current task through `hub-task-finish`;
   - replace the current task.
5. Changes files only after user confirmation.

If a task is paused, a short entry goes into `ai/paused-tasks.md`.

If the user wants to save an idea for later, it goes into `ai/future-tasks.md`, not `ai/paused-tasks.md`.


### How the agent decides a task is different

The agent compares the new request with `ai/current-task.md`.

It is a different task if:
- the goal changed;
- the work mode changed;
- the main files or project area changed;
- the Done criteria changed;
- the new request does not help finish the current task;
- the new request produces a separate result.

It is a continuation of the current task if the new request clarifies, narrows, tests, reviews, or completes the current goal.
