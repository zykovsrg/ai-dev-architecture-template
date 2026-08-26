# Obsidian confirmed two-way task sync — design

## Goal

Keep `ai/` as the single canonical task store while making the local Obsidian
Kanban convenient in both directions:

- a task change made by an architecture workflow refreshes the generated
  Obsidian views automatically;
- a task change made in Obsidian becomes a precise proposal and changes `ai/`
  only after an explicit user confirmation.

This replaces the current one-way, manually refreshed projection. It does not
turn Obsidian into a second source of truth and does not send data anywhere.

## Stable task identity

Every canonical task must have one immutable `Task ID`.

- Structured future tasks retain their existing `FT-YYYYMMDD-NNN` identifier.
- Current and paused tasks gain an explicit `Task ID: TASK-...` field.
- The ID never changes when the user renames a card, moves it between columns,
  changes its due date, or changes its project display name.

The generated card carries the ID as non-rendered card metadata. The exact
Markdown representation is selected only after a small compatibility test with
the installed `obsidian-kanban` plugin proves that moving and editing a card
preserves it. If the plugin cannot preserve hidden metadata, the fallback is a
compact visible ID field; title-based matching is never allowed.

Each generated card continues to include its parent project and explicit due
date. A newly created Obsidian card has no ID, but must include a valid
`project: <registered project name>` field before it can become a proposal.

## Components

1. **Architecture refresh command** reads the canonical task files, validates
   the existing generated manifest, and regenerates the Kanban, project
   overview, and manifest.
2. **Architecture workflow hook** calls that command only after a successful
   task write made through a supported architecture workflow.
3. **Local Obsidian watcher** watches only the three generated files in the
   local vault, ignores writes made while the refresh command holds its lock,
   and debounces editor saves.
4. **Proposal store** is a local ignored runtime file. It contains a structured
   diff and no source change. A status command or a confirmed architecture
   workflow reads it and shows the exact proposal.
5. **Proposal apply command** validates that the source records and the board
   are still the versions used to create the proposal, applies only the
   confirmed canonical diff, then invokes the architecture refresh command.

The watcher is a local macOS background job, not a cloud service. Its lifecycle
is explicit: install, status, and uninstall commands. It is not installed or
enabled without a separate user confirmation.

## Directional behaviour

### Change through the architecture

After an architecture workflow changes `ai/current-task.md`,
`ai/future-tasks.md`, or `ai/paused-tasks.md`, it runs the refresh command.
The command writes only the three generated vault files.

Before writing, it verifies that the existing board still matches its manifest.
If Obsidian was edited since the previous build, it does not overwrite that
edit: it creates a pending Obsidian proposal instead. This protects a manual
edit even when an architecture task change happens later.

### Change through Obsidian

When the watcher detects a user-originated board change, it compares the board
with the last manifest and canonical records. It creates a proposal with the
old and proposed canonical values. It does not write `ai/`, regenerate the
board, or discard the edited card.

The user sees the exact diff and confirms it. Application is refused if either
the board or relevant `ai/` task changed after the proposal was created. In
that case a fresh proposal is required.

## Supported edits and explicit handling

The first implementation supports these safe card edits:

- rename a known-ID card;
- move a known-ID card to a supported status column;
- change or remove its explicit due date;
- create a card with a valid parent project, title, and supported column.

The synchronizer maps a move to the corresponding canonical task state. A
promotion into `Active` is an explicit canonical transition: the promoted task
becomes the current task and any open previous current task is paused in the
same confirmed proposal.

Deleting a card, removing its ID, duplicating an ID, using an unknown column,
or omitting/using an ambiguous project name creates a blocked proposal. No
canonical deletion or inferred project assignment is performed. The proposal
must instead be resolved deliberately through the architecture.

## Safety and conflicts

- The manifest remains the trusted snapshot of the last successful build.
- A refresh lock and writer marker prevent the watcher from treating generated
  writes as manual Obsidian edits.
- There can be at most one pending proposal. A subsequent manual board edit
  updates it only after the prior proposal is dismissed; it never merges two
  unknown edits.
- Source paths, registered projects, task IDs, and accepted statuses are
  validated before every preview and apply.
- The board is never parsed by title alone, and unstructured legacy records
  are never guessed into tasks.
- Runtime state, locks, and proposals stay outside `ai/` and are ignored by
  Git; they contain only the minimum diff metadata needed for confirmation.

## Verification

Contract tests must prove all of the following:

1. An architecture-originated source change rebuilds the three generated views
   without an extra confirmation when the board matches its manifest.
2. A user rename, move, due-date edit, or valid new Obsidian card creates a
   proposal and changes no canonical record.
3. Applying a confirmed proposal changes only its named canonical files, then
   rebuilds the three generated views.
4. A changed source or board makes a proposal stale and blocks its application.
5. Missing, duplicated, or modified task IDs and unsupported edits cannot
   change canonical records.
6. Generator writes are ignored by the watcher, so no feedback loop occurs.
7. The background job watches only the local generated view paths and never
   reads project code, knowledge, secrets, or unrelated vault notes.

## Non-goals

This phase does not sync arbitrary Obsidian notes, infer a task from prose,
write to Calendar, change remote services, or automatically delete a canonical
task.
