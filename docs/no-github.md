# No-GitHub mode

GitHub is convenient, but the architecture can work without it.

## What changes without GitHub

GitHub is a remote place where the project's change history is usually sent.

Without GitHub, the architecture still keeps context in files:

- `ai/current-task.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
- `ai/future-tasks.md`
- `ai/paused-tasks.md`

But the result of the work must be saved locally.

## Best option: local Git

Git is a change history on your computer.

If Git is available, closing a task must create a local commit.

A commit is a save point: you can see which files changed and return to a previous state.

The commands are usually:

```bash
git status
git add .
git commit -m "task description"
```

In this mode the agent must clearly say:

```text
Saved locally, not pushed to GitHub.
```

## If Git is also unavailable

Then use a weak but workable fallback:

- a patch file with the changes;
- a zip/archive copy of the project;
- a list of changed files with a short description.

A patch is a file listing the changes. It can be applied later, but it is less convenient than Git.

## How to close a task without GitHub

Ask the agent:

```text
Run task-finish in local-only mode.
```

The agent must:

1. Check the Done criteria.
2. Update task memory after confirmation.
3. Create a local commit if Git is available.
4. If Git is unavailable, create a patch or archive fallback.
5. Say where the result is saved.

## When it is still worth connecting GitHub

GitHub is useful if:

- you work on several computers;
- you want a backup;
- you want another person to be able to review changes;
- you want to roll back safely to previous versions.

But for solo local work the architecture can start without GitHub.
