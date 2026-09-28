# How to remove the architecture

There are two cases: switch off one module, or remove the whole Hub.

## Switch off one module

Optional modules (knowledge, goals, learning, calendar, planning, obsidian) can be switched off with a normal Hub update. User data stays. See the module table in `docs/update.md`.

## Remove the whole Hub

The Hub is the `_ai-hub` folder. Your projects live inside it, in `_ai-hub/projects/`, and each one is its own Git repository with its own memory (`ai/current-task.md`, `ai/paused-tasks.md`, `ai/future-tasks.md`, `ai/project-context.md`, `ai/decisions.md`, `ai/changelog.md`, and `knowledge/` when present). Deleting `_ai-hub` deletes them too.

Safe order:

1. Move the projects you want to keep out of `_ai-hub/projects/`, or back them up.
2. Keep a copy of Hub data you may need: `ai/project-registry.md`, `ai/project-cards/`, `ai/archiprojects.md`, `ai/goals.md`, `ai/goal-log.md`, `ai/workflow-observations.md`, `ai/workflow-context.md`.
3. If the Obsidian watcher was installed, remove it from the source repository with `bash modules/obsidian/scripts/install-obsidian-task-sync.sh --hub <hub> --scope <scope-file> --vault <vault> --uninstall --confirm-launchd-uninstall`.
4. Delete the `_ai-hub` folder. The calendar server (`tools/apple-calendar-policy`, `.mcp.json`, `.local/apple-calendar/`) lives inside it and goes with it.

Ask the agent to show this plan with the exact paths and to wait for your confirmation before deleting anything.
