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
- `task-finish` — check whether the task can be closed and clean up the context after confirmation.
- `architecture-update` — update the AI development rules, not the application code.

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
- `task-intake` accepts a new task and records it in the project's current memory.
- `task-finish` safely closes a task.

Skills should be loaded only when needed.

## task-finish

`task-finish` has two phases.

Phase 1 checks whether the task can be closed. No files are edited.

Phase 2 cleans up the context only after user confirmation. It updates:

- `ai/changelog.md`
- `ai/decisions.md`, if needed
- `ai/current-task.md`
- confirmed entries in `ai/future-tasks.md`, if ideas for later came up during the task

`task-finish` must not change application code. After cleanup it must save the result: a push to GitHub if GitHub is connected, or a local-only fallback if GitHub is unavailable.

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
- whether the expected external skills and tools are available: code-review-graph, agent-skills-for-context-engineering, and Superpowers;
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

Superpowers is useful for bugs and large tasks where you first need to clarify the idea, agree on a design, make a plan, use TDD, or split the work between subagents.

But Superpowers must not become the default process.

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

`environment-check` is a service check for the first run.

It checks:
- base architecture files;
- base skills;
- expected external tools;
- controlled methodologies.

After this check, the agent continues in one of the modes:
- `implementation`
- `review`
- `task-finish`
- `architecture-update`

Before continuing, the agent shows the available next commands and skills. The menu does not launch these workflows automatically.

This keeps the work modes separate from the startup check.


## Task switching

Before a working task, the agent first uses `task-intake`.

`task-intake` looks at `ai/current-task.md` and decides whether to:

- record the first task;
- continue the current one;
- launch `task-switch` if the user asks for a different task;
- save an idea to `ai/future-tasks.md`.

`task-switch` is needed when the current task is not yet closed and the user asks to start another one.

It does not close the old task. Closing is what `task-finish` is for.

What `task-switch` does:

1. Shows the current unfinished task.
2. Shows the new task.
3. Warns about the risk of losing context.
4. Offers options:
   - continue the current task;
   - pause the current task and start the new one;
   - close the current task through `task-finish`;
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
