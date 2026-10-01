# Personal AI Hub Architecture

Version: 2.0

## Purpose

The hub is a local router and personal-assistant entrypoint for registered
projects. It selects one project safely for project work and can read a bounded
set of canonical task records across active projects for assistant requests;
it is not a shared project workspace, a background scanner, or a place to copy
project memory.

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

When a task admits both a structurally clean option and a cheaper one that leaves something unresolved, present both, state what the clean option costs, and let the user choose. Do not settle that trade-off silently in either direction. Whatever is deferred must be recorded where it will be read again — a future-task entry or the changelog — naming what was deferred and why. Silent deferral is not allowed.

Use evidence appropriate to the claim. Project files, diffs, tests, and logs are primary evidence for local-project facts; current authoritative or professional sources are required for unstable external and health-related claims. Separate verified facts from inference and opinion, state uncertainty, and never invent facts, statistics, sources, or confidence.

Test the user's assumptions when they affect a decision. Report material errors, omissions, counterarguments, and simpler alternatives, but do not manufacture disagreement. For medical and veterinary matters, follow current evidence-based professional sources and never independently cancel, replace, or alter a qualified professional's prescription.

Concise communication is the default. Add headings only when they improve navigation. Give enough information for the current decision; do not add detail merely to anticipate every possible question.

Hub routing and project isolation remain higher-priority safety constraints and cannot be removed in the name of simplicity.

## Write Confirmation Policy

User decision (2026-09-28): writes need no confirmation; only deletion does.
This overrides every write-confirmation gate in hub rules, skills, workflows,
and resources (task records, calendar create/update, knowledge, goals, project
files, registry, memory). Perform the write directly, then briefly report what
was written and where. Deletion of any data (files, records, calendar events,
tasks, projects) still requires explicit confirmation in chat first.

The calendar tool's preview/apply pair is a technical step: create the preview
and apply it in the same turn without asking. For a calendar delete, show the
preview and wait for the user's yes.

This policy does not remove confirmation of which project to open before
reading it (routing), allowed roots, secret rules, or memory isolation.

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

## Module Rules

Optional modules install their rules as `ai/rules/<id>.md`. The installer
lists installed modules and event subscribers in the generated
`ai/modules.md`. A module's rules are read only when one of its commands or
subscriptions runs; a module that is not installed is never called.

Project routing (route first, then confirm) is defined only in
`hub-project-router`.

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

1. For a personal-assistant request: the entry file, active registry identity,
   and only `ai/current-task.md`, `ai/future-tasks.md`, and
   `ai/paused-tasks.md` for each active project. Do not load cards, knowledge,
   code, Git, credentials, or arbitrary project files.
2. For an unconfirmed project-specific request: follow `hub-project-router`.
3. After project confirmation: the hub-owned `hub-environment-check`, the
   selected project's current task, at most two directly relevant
   project-memory files, and one matching shared workflow skill.
4. Expand beyond that budget only when the current task needs it; state why and
   load the next narrowest source rather than a whole project tree.

Prefer summaries, filenames, and direct references over bulk reads. The budget
protects both privacy and context quality; it does not authorize reading an
unregistered path or bypassing project-specific rules.
