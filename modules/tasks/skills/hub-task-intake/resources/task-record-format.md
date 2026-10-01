# Task record format

Use `Task ID:`, `Status:`, and `Due: YYYY-MM-DD`. Both legacy `due:` and
canonical `Due:` can be read, but new task writes use `Due:`. A date must be a
real calendar date. Current, future, and paused records keep their existing
status sets and must carry an ID belonging to their registered project.

Headings are machine-read; a record whose heading does not match is silently
skipped by task discovery and never reaches day plans or reviews.

- Future record (`ai/future-tasks.md`): heading
  `### FT-YYYYMMDD-NNN — <title>` (or `### TASK-<project-id>-YYYYMMDD-NNN — <title>`),
  followed by `Status:` (`idea|ready|blocked|promoted|done|dropped`), optional
  `Due:`, and `Created: YYYY-MM-DD` before any prose.
- Paused record (`ai/paused-tasks.md`): heading `### YYYY-MM-DD — <title>`
  (pause date), followed by `Task ID:` and `Status: paused` before any prose.
- `NNN` is the next free number for that date within the project.
- Never write a task under a free-text `###` heading without an ID.
- Optional schedule link, directly after `Запланировано:`:
  `Событие: <calendar-id>/<event-id> · синхронизировано: YYYY-MM-DD HH:MM-HH:MM`.
  Write it whenever a change creates or moves a timed, non-recurring
  event for the task; refresh `синхронизировано` on every sync. A
  malformed line fails the canonical check.
