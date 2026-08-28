# Scoped Obsidian Sync Design

## Goal

Let an agent for one confirmed hub project import edits only from that
project's generated Obsidian board.

## Design

The central vault remains the sole source:
<hub>/projects/ai-dev-architecture/obsidian-vault. A selected project board
is always Obsidian/Projects/<project-id>/Kanban.md.

Add a required --project-id <id> selector to the Obsidian proposal workflow:

- scan validates and reads only the selected board and that project's
  canonical task records, then writes a proposal containing only that project.
- apply requires the same selector and rejects a proposal for another
  project.
- status and dismiss remain vault-level proposal operations.

The selector must be a registered ID inside the supplied scope. The
synchronizer must reject an unknown ID, a project outside scope, a missing
selected board, or a proposal whose operations or board hash mention another
project. It must not hash or parse boards belonging to other projects.

Hub task workflows state this central location explicitly. They must derive it
from the confirmed hub root and selected ID; they never ask for a per-project
vault path. A missing central hub configuration remains an error, not a reason
to guess a path.

## Safety

Manual edits remain proposals. Canonical task records change only after the
proposal's exact SHA-256 is displayed and separately confirmed. No command may
cross the selected project's task-memory boundary.

## Tests

Contract tests will prove that a selected-project scan ignores a changed second
board, that it does not hash that board, and that apply rejects a mismatched
project selector. Hub smoke tests will require the central-vault instruction in
the shared workflows.
