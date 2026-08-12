# Personal AI Hub Architecture

Version: 1.0

## Purpose

The hub is a local router for several registered projects. It selects one
project safely; it is not a shared project workspace, a background scanner, or
a place to copy project memory.

## Rule Precedence

Apply rules in this order:

1. Direct user instructions and applicable platform safety rules.
2. The selected project's confirmed entry instructions.
3. This hub architecture and the hub entry file.
4. The selected project's active task memory and one matching skill.
5. Other relevant project references.

The hub entry file governs project selection until confirmation. After that,
the selected project's rules govern project work. When rules conflict, keep
the safer boundary and ask for clarification rather than widening access.

## Ownership And Registry

Hub-owned files are the routing inventory:

- `ai/allowed-roots.md` lists the only directory roots eligible for projects.
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

1. Read only the hub entry file and hub-owned routing inventory.
2. Match the request to registered IDs, tags, and card metadata without reading
   project files.
3. Show `Project: <id>`, the exact registered `Path: <path>`, and `Mode: routing`.
4. Ask for explicit confirmation of that project and path.
5. Only after confirmation, enter the project, read its entry instructions and
   the smallest needed project memory, then select one matching skill.

The router never discovers projects by listing arbitrary folders, follows a
path outside allowed roots, or treats a remembered active project as confirmed
in a new chat. If no single registered project matches, ask the user to choose
from safe registry results; do not inspect likely directories to decide.

Example: the request names "website metrics". The router may present
`Project: metrics-site`, `Path: /work/demo/metrics-site`, and `Mode: routing`.
It must wait for confirmation before opening `/work/demo/metrics-site`.

## Confirmation And Confidence

Use these confidence labels in router summaries and cross-project signals:

- **verified** — directly validated from hub inventory or confirmed by the user.
- **stated** — supplied by the user but not independently validated.
- **inferred** — a non-sensitive conclusion from registered metadata; never a
  permission to access a project.
- **unknown** — absent, ambiguous, stale, or not safely verifiable.

Only `verified` selection plus explicit confirmation permits project access.
`stated` and `inferred` information may guide a clarification question, but
must not change a registry record, broaden allowed roots, or trigger a read.
Label hypotheses as hypotheses and preserve their source when recording them.

## Project Switches And Task Switches

A project switch changes the selected project. It always returns to
`Mode: routing`, shows the new exact registered path, and requires a new
explicit confirmation before any read of the new project's memory or code.

A task switch happens inside an already confirmed project. Use that project's
task-switch process and memory; it is not a project switch. Do not pause,
finish, copy, or rewrite one project's task memory while switching to another
project. A request that mentions two projects needs separate confirmation for
each project and a clear boundary for any shared output.

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

## Installation And Updates

Installing the hub creates or updates hub-owned templates and scripts only in
the chosen hub location. It must not scan, rewrite, install dependencies in,
or otherwise modify registered projects without their separate confirmation.

An architecture update must be reviewed before applying: show the changed hub
rules, affected files, and token impact; then obtain explicit approval. Preserve
local registry data and cards during template updates. Do not silently replace
local routing records, project instructions, or project memory. Validate any
registry/allowed-root change before it becomes operational.

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
   one matching hub card. Do not load project memory or code.
2. After confirmation: the selected project entry file, current task, at most
   two directly relevant memory/reference files, and one matching skill.
3. Expand beyond that budget only when the current task needs it; state why and
   load the next narrowest source rather than a whole project tree.

Prefer summaries, filenames, and direct references over bulk reads. The budget
protects both privacy and context quality; it does not authorize reading an
unregistered path or bypassing project-specific rules.
