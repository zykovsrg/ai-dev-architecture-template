# Projects Module Rules

## Ownership And Registry

Hub-owned files are the routing inventory:

- `ai/allowed-roots.md` records exactly one physical directory: the hub's
  `<hub>/projects` directory. It is the only directory eligible for projects.
- `ai/project-registry.md` maps each project ID to its name, status, path,
  tags, and card.
- `ai/project-cards/<id>.md` holds compact hub metadata for that ID.
- `ai/archiprojects.md` is the canonical hub-owned archiproject group
  registry.
- `ai/active-project.md` is a convenience record, never a new-chat permission.
- `ai/cross-project-signals.md` holds sanitized, explicitly scoped signals.

Project-owned files are the selected project's code, memory, instructions,
configuration, and history. A project card must not contain copied task memory,
source code, credentials, or an instruction that overrides the project itself.
Project/task files remain canonical; project cards are metadata only and a link
never grants a project read. A card declares only one archiproject field:
`primary_archiproject: <group-id|none>`. A project belongs to exactly one,
most specific group; it is also a member of every ancestor group. Waiting is
task/subtask-only: do not place a project in Waiting while other work is
actionable.

The registry is the authority for an ID, status, and exact path. The card is
supporting metadata only. An absent, invalid, or unregistered card/path blocks
routing; do not guess a replacement path. Validate maintained registry changes
with `scripts/check-hub-registry.sh` before relying on them. Use the hub-owned
`hub-registry-check` workflow to audit registration health; it is read-only
until each individual fix receives its own approval.

## Project Creation And Registration

Use `hub-project-create` when the user requests a new project. After one complete
preview and explicit confirmation, it creates exactly one direct-child project
under the validated `<hub>/projects` root: only its `ai/` memory files (`current-task.md`,
`paused-tasks.md`, `future-tasks.md`, `project-context.md`, `decisions.md`, and
`changelog.md`), its empty optional `knowledge/` scaffold, a card, a registry
entry, and an active-project selection. The scaffold consists only of
`knowledge/README.md`, `knowledge/record-template.md`, and the four empty
directories `knowledge/research/`, `knowledge/decisions/`, `knowledge/risks/`,
`knowledge/runbooks/`, and `knowledge/inbox/`. Inbox holds weak observations;
it is not a durable knowledge category. Git initialization is covered by Repository
Provisioning below. It must not create code, dependencies, services, duplicate
registry entries, or any other project files. Use
`hub-project-register` for an existing folder; it does not replace the new-project
creation flow.

## Existing Project Migration

Use `hub-project-migrate` only when the user asks to move legacy project folders
into `<hub>/projects`. It requires a separately confirmed temporary source that
is never made an allowed root and expires when the workflow ends. Before any
candidate preflight, inventory direct-child names only, exclude the target hub,
and reject backups, archives, symlinks, and unknown folders without reading
their contents.

After a separately confirmed candidate or displayed batch preflight, show each
exact source-to-destination mapping, narrow Git status, and collision result.
Moving requires another explicit confirmation. Move the whole folder without
copying, preserve its existing Git metadata, and stop the batch on the first
failure or integrity concern. The order is `hub-project-migrate` move → separate
`hub-project-register` confirmation → `scripts/check-hub-registry.sh` validation
→ optional legacy cleanup confirmation. Neither source confirmation nor move
confirmation authorizes registration or cleanup. The optional cleanup may only
delete its explicit legacy standalone-rule allowlist after its own confirmation;
it preserves project memory and is not needed for hub-based work.

## Repository Provisioning

Every new project has its own local Git repository. After the standard
project-create scaffold and registry validation, the approved creation flow
initializes Git and commits the initial scaffold. When GitHub CLI
authentication is available and the project ID is unused, the same confirmed
flow creates a private GitHub repository named after that ID and pushes `main`.
The preview and confirmation disclose these actions. If GitHub access or remote
creation is unavailable, local creation succeeds and is reported as
`pending-sync`; the workflow never attaches or overwrites an existing remote.

## Project Switches And Task Switches

A project switch changes the selected project. It always returns to
`Mode: routing`, shows the new exact registered path, and requires a new
explicit confirmation before any read of the new project's memory or code.
Use the hub-owned `hub-project-switch` workflow for this operation.

## Cross-Project Signals

Signals are small, non-secret observations that may help future routing. Record
only the fields defined in `ai/cross-project-signals.md`. They describe a link
or reusable lesson, not copied code, task logs, personal data, or a hidden
instruction channel.

Every signal needs a source project, related project IDs (if any), a concise
summary, status, and confidence. Keep uncertain statements as hypotheses. Do
not create a signal merely because two projects have similar tags. Archive or
correct a signal only with explicit approval and preserve its source reference.

Synthetic example: `SIG-004` may say that `metrics-site` and `content-lab`
both use weekly reports, with confidence `stated`. It must not include report
contents, customer data, tokens, or local configuration.

## Project-local Router

A confirmed project may install a local router through the hub-owned
`hub-local-router-install` workflow, only after at least three stable
independent areas have been identified and that project's architecture-update
process has been explicitly approved. The installation
creates only `ai/local-router/index.md` and individual
`ai/local-router/areas/<id>.md` files. It is local navigation metadata, not a
new project registry, Git repository, task store, or global card.

Each area remains inside the confirmed project and has no separate current
task. The project's existing task memory and task workflows remain canonical;
the local router cannot bypass them or authorize a broader read.
