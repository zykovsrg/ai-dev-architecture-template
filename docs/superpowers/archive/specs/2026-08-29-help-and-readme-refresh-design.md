# Help and README Refresh

## Goal

Explain the current architecture in short, simple Russian. A new user should
understand what it does, how to ask for help, and when the agent needs a
confirmation.

## Structure

`README.md` remains a short overview. It describes the two installation modes
(one project and Personal AI Hub), the project overview and separate Obsidian
boards, confirmed reverse sync, meeting-note routing, and safe updates.

`getting-started/getting-started.md` is renamed to
`getting-started/help.md`. Its visible title is `Помощь`. It is the practical
page: short phrases a user can write and the expected result.

The internal skill name `start-screen` remains for compatibility. It presents
the new Help page and also activates for `помощь`, `что умеешь`, and
`как работать`.

## Help topics

1. Choose or open a project.
2. Start, change, pause, and finish a task.
3. See all projects and open an individual Kanban board.
4. Edit a board in Obsidian: agent checks it, shows a proposal, and writes
   only after confirmation.
5. Send meeting notes: the agent separates tasks by project and asks for
   separate confirmations.
6. Create a new project after a preview and confirmation.
7. Update rules or architecture only after a shown change and confirmation.
8. Ask for an update check or help again.

## Safety

The documentation must not promise automatic writes. It must say plainly that
manual Obsidian edits, meeting notes, new projects, and architecture changes
are reviewed first and written only after the user confirms.

## Validation

- All renamed references resolve to `getting-started/help.md`.
- `start-screen` documentation names Help and its new trigger phrases.
- README and Help mention the current Obsidian and multi-project mechanics.
- Existing consistency and smoke checks pass.
