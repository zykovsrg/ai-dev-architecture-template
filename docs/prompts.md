# Prompts

These prompts assume the supported Personal AI Hub architecture. Shared rules and workflows live in Hub; project repositories keep their own canonical memory and optional knowledge.

## Install Personal AI Hub

```text
Install Personal AI Hub from my local ai-dev-architecture-template checkout.
Show the exact target path first. The target folder must be `_ai-hub`.
Run the supported Hub installer only after I confirm the path.
Do not scan, register, move, or edit any project automatically.
```

Supported local command after confirmation:

```bash
bash scripts/install.sh /path/to/_ai-hub
```

## Create a project

```text
Use `hub-project-create`.
Collect the project name/type, validate the allowed Hub projects root, and show the exact project ID, direct-child target path, scaffold, registry/card changes, Git initialization, and any remote action before writing.
Wait for the workflow's explicit confirmation. Do not create application code, dependencies, services, or shared rule copies.
```

## Register an existing project

```text
Use `hub-project-register` for an existing direct child under the allowed Hub projects root.
Before confirmation, use only the permitted routing inventory. Show the exact project ID and registered path, then wait for explicit confirmation before reading project memory or changing the registry/card.
```

## Migrate an existing project

```text
Use `hub-project-migrate`.
Ask me to name and separately confirm the temporary source directory. Inventory only direct-child candidate names before candidate confirmation. Show exact source-to-destination mappings, narrow Git status, collisions, and preservation rules.
Moving, registration, validation, and optional legacy-rule cleanup are separate confirmation gates. Preserve project memory, knowledge, Git metadata, and project-specific rules.
```

## Switch project

```text
Use `hub-project-switch`.
Show the candidate project ID and exact registered path using Hub routing metadata only. Wait for explicit project/path confirmation before reading its memory, code, knowledge, Git, or linked targets.
```

## Cross-project task overview

```text
Treat this as a personal-assistant request.
For discovery across active registered projects, start with `scripts/read-compact-task-index.py`. Open a canonical current/future/paused task record only when a selected row requires a detail absent from the compact index. Final factual output must cite the canonical source path. Do not read project code, credentials, arbitrary files, or inactive projects.
```

## Day plan

```text
Use `hub-workflows` with the `day-plan` scenario. Follow core scope/security/proposal rules, then load only `resources/day-plan.md` plus its required calendar-context resource. Read Calendar only through the guarded Hub Calendar interface. Render the complete required day-plan format and keep all proposed task/calendar writes confirmation-gated.
```

## Evening review

```text
Use `hub-workflows` with the `evening-review` scenario. Follow core scope/security/proposal rules, then load only `resources/evening-review.md`. For a calendar-only review start with `prepare_evening_review`. Pending friction stays pending when a proposal is merely shown; resolve it only after explicit accepted/rejected disposition through the learning lifecycle.
```

## Weekly review

```text
Use `hub-workflows` with the `weekly-review` scenario. Start personal-assistant task discovery from the compact task index, use canonical task sources for facts, and load only `resources/weekly-review.md` for scenario formatting. Learning rule promotion/retirement remains proposal-only and confirmation-gated.
```

## Capture a meeting or task

```text
Use `hub-workflows` with the `capture` scenario for the one source I explicitly provide. Do not discover other transcripts/files. Follow the source/scope gates, perform semantic analysis, then return exact independent proposal envelopes and diffs. Do not apply them automatically.
```

## Capture project knowledge

```text
Use `hub-knowledge-capture` only for the already confirmed project and explicitly selected material. Knowledge is optional/on-demand, not default context. Show the exact target record/path and proposed content before confirmation; do not copy raw sensitive source material unnecessarily.
```

## Review project knowledge

```text
Use `hub-knowledge-review` for one explicitly selected project-local knowledge record, folder, or task-linked set. Check freshness and conflicts against the permitted source evidence. Show exact proposed edits and wait for confirmation before changing anything.
```

## Update an installed Hub

```text
Use the supported content-addressed Hub update flow from a local source checkout. Resolve any requested remote branch/tag to one commit SHA once, use that same revision for preview and apply, show the plan/hash first, preserve local modified managed files as conflicts, and keep existing create-if-missing memory untouched.
```

Do not use pipe-to-shell installation/update commands. Download or clone first, inspect the local source/revision, then run the repository scripts locally.
