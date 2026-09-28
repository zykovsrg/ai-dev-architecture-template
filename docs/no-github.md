# No-GitHub mode

GitHub is convenient, but the Hub works without it.

## What changes without GitHub

GitHub is a remote place where a project's change history is usually sent.

Without GitHub, the project still keeps its context in files:

- `ai/current-task.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
- `ai/future-tasks.md`
- `ai/paused-tasks.md`

Every Hub project has its own local Git repository. Git is a change history on your computer; a commit is a save point you can return to.

## Creating a project without GitHub

`hub-project-create` always initializes local Git and commits the approved starting files. It creates a private GitHub repository only when the GitHub CLI is signed in and the project ID is unused there. Otherwise the project is created locally and reported as `pending-sync`. The workflow never attaches or overwrites an existing remote.

## Closing a task without GitHub

Ask the agent to close the task as usual. `hub-task-finish` saves the result through the project's repository and reports every write, the commit, and whether it was pushed or stayed local.

## When it is still worth connecting GitHub

GitHub is useful if:

- you work on several computers;
- you want a backup;
- you want another person to review changes.

For solo local work the Hub can start without GitHub.
