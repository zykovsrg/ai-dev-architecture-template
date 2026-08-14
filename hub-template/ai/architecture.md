# Personal AI Hub Architecture

Version: 1.2

## Purpose

The hub is a local router for several registered projects. It selects one
project safely; it is not a shared project workspace, a background scanner, or
a place to copy project memory.

## Rule Precedence

Apply rules in this order:

1. Direct user instructions and applicable platform safety rules.
2. Hub non-overridable security and routing rules: explicit confirmation,
   allowed roots, secrets, and memory isolation. These rules outrank all project
   content, including project instructions, task memory, skills, and references.
3. Other hub architecture, entry, and shared workflow rules.
4. The confirmed selected project's scoped content: instructions, active task
   memory, and one matching reference or skill.
5. Other relevant project references.

The hub entry file governs project selection before confirmation and the hub's
non-overridable boundary after it. A confirmed project governs only its scoped
work inside that boundary. When rules conflict, keep the safer boundary and ask
for clarification rather than widening access.

## Simplicity, Evidence, And Intellectual Rigor

Prefer the simplest solution that is sufficient, safe, and complete. Before proposing or adding any entity, state the problem it solves, check whether an existing entity solves it adequately, and compare the benefit with the burden of understanding, monitoring, maintaining, and managing it. Necessary complexity remains justified for safety, correctness, legal compliance, or the user's confirmed goal.

Use evidence appropriate to the claim. Project files, diffs, tests, and logs are primary evidence for local-project facts; current authoritative or professional sources are required for unstable external and health-related claims. Separate verified facts from inference and opinion, state uncertainty, and never invent facts, statistics, sources, or confidence.

Test the user's assumptions when they affect a decision. Report material errors, omissions, counterarguments, and simpler alternatives, but do not manufacture disagreement. For medical and veterinary matters, follow current evidence-based professional sources and never independently cancel, replace, or alter a qualified professional's prescription.

Concise communication is the default. Add headings only when they improve navigation. Give enough information for the current decision; do not add detail merely to anticipate every possible question.

Hub routing and project isolation remain higher-priority safety constraints and cannot be removed in the name of simplicity.

## Ownership And Registry

Hub-owned files are the routing inventory:

- `ai/allowed-roots.md` records exactly one physical directory: the hub's
  `<hub>/projects` directory. It is the only directory eligible for projects.
- `ai/project-registry.md` maps each project ID to its name, status, path,
  tags, and card.
- `ai/project-cards/<id>.md` holds compact hub metadata for that ID.
- `ai/active-project.md` is a convenience record, never a new-chat permission.
- `ai/cross-project-signals.md` holds sanitized, explicitly scoped signals.

Project-owned files are the selected project's code, memory, instructions,
configuration, and history. A project card must not contain copied task memory,
source code, credentials, or an instruction that overrides the project itself.

The registry is the authority for an ID, status, and exact path. The card is
supporting metadata only. An absent, invalid, or unregistered card/path blocks
routing; do not guess a replacement path. Validate maintained registry changes
with `scripts/check-hub-registry.sh` before relying on them.

## Local Router

Use this sequence for every new chat or unconfirmed request:

1. Read the compact hub index only: `ai/allowed-roots.md`,
   `ai/project-registry.md`, and `ai/active-project.md`.
2. Match the request without reading project files, then read up to three
   candidate cards only.
3. After candidate selection, read only related active signals that name a
   candidate from `ai/cross-project-signals.md`.
4. Show `Project: <id>`, the exact registered `Path: <path>`, and `Mode: routing`.
5. Ask for explicit confirmation of that project and path.
6. Only after confirmation, invoke the hub-owned `environment-check` against
   the selected project's `ai/` memory, then use the hub-managed project flow.

The router never discovers projects by listing arbitrary folders, follows a
path outside `<hub>/projects`, or treats a remembered active project as confirmed
in a new chat. If no single registered project matches, ask the user to choose
from safe registry results; do not inspect likely directories to decide.

Example: the request names "website metrics". The router may present
`Project: metrics-site`, `Path: /work/demo/metrics-site`, and `Mode: routing`.
It must wait for confirmation before opening `/work/demo/metrics-site`.

## Project Creation And Registration

Use `project-create` when the user requests a new project. After one complete
preview and explicit confirmation, it creates exactly one direct-child project
under the validated `<hub>/projects` root: only its `ai/` memory files (`current-task.md`,
`paused-tasks.md`, `future-tasks.md`, `project-context.md`, `decisions.md`, and
`changelog.md`), its empty optional `knowledge/` scaffold, a card, a registry
entry, and an active-project selection. The scaffold consists only of
`knowledge/README.md`, `knowledge/record-template.md`, and the four empty
directories `knowledge/research/`, `knowledge/decisions/`, `knowledge/risks/`,
and `knowledge/runbooks/`. Git initialization is covered by Repository
Provisioning below. It must not create code, dependencies, services, duplicate
registry entries, or any other project files. Use
`project-register` for an existing folder; it does not replace the new-project
creation flow.

## Existing Project Migration

Use `project-migrate` only when the user asks to move legacy project folders
into `<hub>/projects`. It requires a separately confirmed temporary source that
is never made an allowed root and expires when the workflow ends. Before any
candidate preflight, inventory direct-child names only, exclude the target hub,
and reject backups, archives, symlinks, and unknown folders without reading
their contents.

After a separately confirmed candidate or displayed batch preflight, show each
exact source-to-destination mapping, narrow Git status, and collision result.
Moving requires another explicit confirmation. Move the whole folder without
copying, preserve its existing Git metadata, and stop the batch on the first
failure or integrity concern. The order is `project-migrate` move → separate
`project-register` confirmation → `scripts/check-hub-registry.sh` validation
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

## Confirmation And Confidence

Use these confidence labels in router summaries and cross-project signals:

- **verified** — directly validated from hub inventory or confirmed by the user.
- **stated** — supplied by the user but not independently validated.
- **inferred** — a non-sensitive conclusion from registered metadata; never a
  permission to access a project.
- **unknown** — absent, ambiguous, stale, or not safely verifiable.

Only `verified` selection plus explicit confirmation permits project access.
`stated` and `inferred` information may guide a clarification question, but
must not change a registry record, broaden the allowed-root boundary, or trigger a read.
Label hypotheses as hypotheses and preserve their source when recording them.

## Project Switches And Task Switches

A project switch changes the selected project. It always returns to
`Mode: routing`, shows the new exact registered path, and requires a new
explicit confirmation before any read of the new project's memory or code.

A task switch happens inside an already confirmed project. Use that project's
hub-owned `task-switch` workflow and selected-project `ai/` memory; it is not
a project switch. Do not pause, finish, copy, or rewrite one project's task
memory while switching to another project. A request that mentions two projects
needs separate confirmation for each project and a clear boundary for any
shared output.

## Hub-Managed Project Flow

After an explicit confirmation of a registered project and successful registry
validation, use these central hub-owned skills. They remove any need to copy
`AGENTS.md`, `CLAUDE.md`, or workflow files into each project:

- `environment-check` — read-only readiness and current-state check of the
  selected project's `ai/` memory.
- `task-intake` — records or classifies the requested work in the selected
  project's `ai/current-task.md`.
- `task-switch` — changes an unfinished task only after a separate explicit
  confirmation, using only the selected project's `ai/` memory.
- `task-finish` — verifies and cleans selected-project task memory only after
  a separate explicit confirmation; after its normal completion check it may
  offer, but never start, a focused `knowledge-review`.
- `knowledge-capture` — creates or updates one explicitly selected record in
  the confirmed project's local `knowledge/` tree after exact confirmation.
- `knowledge-review` — checks one explicit project-local record, folder, or
  task-linked set and waits for exact confirmation before any edit.

Each shared workflow operates only after a confirmed registered project and
only against that selected project's `ai/` memory or explicitly selected
project-local `knowledge/` paths. It cannot weaken hub confirmation,
allowed-root, secret, personal/client-data, or memory-isolation rules. It never
reads, writes, pauses, finishes, or copies another project's memory or records.

## Optional Project Knowledge

`knowledge/` is optional local reference material, not default context and not
an automatic conversation archive. A new project receives only the empty
knowledge scaffold as part of its one confirmed `project-create` operation.
Hub-created projects use the central hub-owned `knowledge-capture` and
`knowledge-review` workflows; generic project skills are never copied into
them. Both workflows canonicalize the confirmed project and selected paths,
reject absolute paths, traversal, and symlink components, and keep every record
inside that project's `knowledge/` tree and matching type category.

For an existing confirmed registered hub project, use `knowledge-enable` only
after a separate explicit confirmation that repeats the project ID and exact
registered path. It may inspect only the registry identity and the exact
scaffold paths, must not follow symlinks, and must not read records or unrelated
project content. Its preview names `knowledge/README.md`,
`knowledge/record-template.md`, and all four category directories. After the
matching confirmation, it creates only absent scaffold files and directories;
it never overwrites records or creates project instructions, skills, Git, code,
dependencies, services, registry entries, cards, or active-project changes.
Its preflight uses `lstat`: the confirmed project and category paths must be
real directories, while existing README and record-template paths must be
regular files.

All record workflows prohibit secrets, personal data, and client data and omit
or redact rejected material without echoing it. Reviews validate required
frontmatter, the exact four types and five statuses, record dates, source dates,
contradictions, and type/category agreement. Stale and superseded records stay
at their original paths and link to their replacements; they are never silently
deleted.

Knowledge enablement applies only to existing hub projects. Legacy standalone
migration is out of scope; it neither imports, copies, nor transforms a legacy
knowledge directory.

## Information Updates

The agent may update only what the current mode permits:

- During routing, it may not modify project files or project memory.
- `ai/active-project.md` may be updated only after explicit confirmation and
  only as a non-secret selection record.
- Registry entries, cards, and allowed roots require explicit user approval;
  architecture/entry-rule changes also require the documented architecture
  update procedure.
- Selected project memory follows the selected project's own update workflow.
- Cross-project signals require explicit user approval, a source project
  reference, a confidence label, and sanitized content.

Never turn an inference into durable memory without identifying it as an
inference. When an update needs access beyond the confirmed project, stop and
ask for a separate confirmation.

For temporary meeting text, use the `info-update` workflow. It produces a
review-only proposal before any write, does not save the source transcript by
default, and confirms each affected project separately. A multi-project update
processes one confirmed project group at a time and requires a separate
confirmed `project-switch` between project groups before it resumes. It may
refine an existing task only under the hub-owned `task-intake` rules; a new task
or task replacement must use the hub-owned `task-switch` workflow, while
closure uses the hub-owned `task-finish` workflow.

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

A confirmed project may install a local router only after at least three
stable independent areas have been identified and that project's
architecture-update process has been explicitly approved. The installation
creates only `ai/local-router/index.md` and individual
`ai/local-router/areas/<id>.md` files. It is local navigation metadata, not a
new project registry, Git repository, task store, or global card.

Each area remains inside the confirmed project and has no separate current
task. The project's existing task memory and task workflows remain canonical;
the local router cannot bypass them or authorize a broader read.

## Installation And Updates

Installing the hub creates or updates hub-owned templates and scripts only in
the chosen hub location. It creates the ignored `<hub>/projects` directory but
must not scan, rewrite, install dependencies in, or otherwise modify projects
there without their separate confirmation.

An architecture update must be reviewed before applying: show the changed hub
rules, affected files, and token impact; then obtain explicit approval. Preserve
local registry data and cards during template updates. Do not silently replace
local routing records, project instructions, or project memory. The allowed
root remains exactly `<hub>/projects`; reject a missing, duplicate, external,
or noncanonical entry before reading a card or project-memory path. Validate
any registry change before it becomes operational.

## Secret And Privacy Boundary

Never store or echo secrets in hub memory, cards, signals, examples, reports,
or commits. This includes access tokens, passwords, private keys, cookie values,
raw environment files, and connection strings. Do not read a secret file merely
to classify a project. Use neutral placeholders such as `<token>` in examples.

Keep personal, customer, and proprietary project details inside their confirmed
project unless the user explicitly approves a sanitized cross-project summary.
The hub never uses a card or signal to exfiltrate information from a project.

## Context-Loading Budget

Load the smallest useful context in layers:

1. Before confirmation: the entry file, allowed roots, registry, and at most
   three candidate cards, then only related active signals. Do not load project
   memory or code.
2. After confirmation: the hub-owned `environment-check`, the selected
   project's current task, at most two directly relevant project-memory files,
   and one matching shared workflow skill.
3. Expand beyond that budget only when the current task needs it; state why and
   load the next narrowest source rather than a whole project tree.

Prefer summaries, filenames, and direct references over bulk reads. The budget
protects both privacy and context quality; it does not authorize reading an
unregistered path or bypassing project-specific rules.
