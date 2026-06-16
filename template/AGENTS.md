# AI Development Entry Point — Codex

This project uses a solo AI-development workflow.

This is the entry file for Codex. The matching entry file for Claude Code is `CLAUDE.md`. The two must stay equal in meaning; only the tool-specific notes below differ.

Use this file as the short entry point. Detailed rules live in `ai/architecture.md` and relevant `ai/skills/*/SKILL.md`. Do not load them by default. Open them only when the task needs those details or when a workflow rule is unclear.

## Core rules

- Communicate with the user in Russian, assuming they are new to IT. Do not assume prior development knowledge. Explain every technical term in plain words the first time it appears, and explain the reasoning behind your actions in simple steps. Use short analogies when they help. See `ai/architecture.md` → "Language" for the full rule.
- Keep persistent AI-facing instructions in English.
- Prefer minimal diffs and clean architecture.
- Do not expand user-confirmed scope. If a larger scope looks useful, stop and ask first.
- Capture useful out-of-scope ideas as future task candidates instead of implementing them inside the current task.
- Do not mix refactoring with bugfixes unless explicitly asked.
- Explain the reason and risks before changing storage, data model, dependencies, or architecture.
- For risky changes, add tests or explain why tests are not practical and provide manual checks.
- Do not overwrite unfinished task memory.
- Do not update protected architecture files without `architecture-update` mode and explicit user confirmation.
- In review mode, verify problems with read, grep, diff, logs, or tests before reporting them as facts. If not verified, label them as hypotheses.

## File classes

Protected architecture files define reusable workflow rules and may be changed only in `architecture-update` mode after explicit user confirmation:

<!-- canon:protected-files -->
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`
<!-- /canon:protected-files -->

Controlled memory files store project and task memory. They may be edited only by the matching workflow described in `ai/architecture.md` and relevant skills:

<!-- canon:controlled-memory -->
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
<!-- /canon:controlled-memory -->

Before finishing any task, check `git diff --name-only`. If protected architecture files changed without approval, stop and ask the user. If controlled memory files changed, explain which workflow allowed it.

## Session start

When entering an existing project, switching tools, continuing in a new chat, or continuing from compressed/restored context, run `environment-check` before suggesting next steps or starting implementation. Skip it only if the user explicitly says not to run it.

Compressed context, compacted context, restored summary, or conversation summary continuation counts as a new session.

`environment-check` and `task-switch` are not work modes. After `environment-check`, continue in a work mode.

A successful `environment-check` response must include a short snapshot of the current task and future tasks, then end with a short menu of available next commands and skills. This snapshot and menu are informational and must not automatically activate or promote any listed workflow or task.

## Work modes

State the mode explicitly before task work as `Mode: ...`.

- `review` — read, inspect, summarize, run checks, or suggest next steps. Do not edit files.
- `implementation` — change application code, project files, tests, or allowed task memory.
- `task-finish` — check whether the task can be closed; clean up only after explicit user confirmation.
- `architecture-update` — propose architecture changes; edit only after explicit user confirmation.

If implementation or review suggests the current task may be complete, do not declare it closed. Propose `task-finish` and wait for the user to confirm.

## Context and skill routing

Do not read all files from `ai/` automatically.

Default minimum:
- this file
- `ai/current-task.md`

Codex does not auto-activate skills. When a trigger matches, open the matching `ai/skills/*/SKILL.md` file manually before applying that workflow. Do not work from memory.

Common triggers:
- environment check: `ai/skills/environment-check/SKILL.md` and `ai/external-tools.md`
- task switching: `ai/skills/task-switch/SKILL.md`, `ai/current-task.md`, and `ai/paused-tasks.md`
- future task capture or promotion: `ai/future-tasks.md`; no separate skill is required
- task finish: `ai/skills/task-finish/SKILL.md`
- release or merge: `ai/skills/release-check/SKILL.md`
- tests or test decision: `ai/skills/write-tests/SKILL.md`
- UI behavior, screen state, layout logic, or interaction: `ai/skills/ui-review/SKILL.md` and `ai/skills/write-tests/SKILL.md`
- purely decorative visual UI change: `ai/skills/ui-review/SKILL.md`; use `write-tests` only if behavior, state, layout logic, or interaction can be affected
- bugfix, regression, crash, flaky behavior, debug request, or performance investigation: `ai/skills/bugfix-workflow/SKILL.md`
- architecture change: `ai/skills/architecture-update/SKILL.md`

Read extra context only when relevant:
- project behavior, storage, or UI: `ai/project-context.md`
- architecture-sensitive work or durable invariants: `ai/decisions.md`
- future task review, capture, or promotion: `ai/future-tasks.md`
- workflow ambiguity or architecture update: `ai/architecture.md`
- plan-driven or Superpowers execution: relevant `docs/superpowers/specs/*`, `docs/superpowers/plans/*`, and plan-driven rules in `ai/architecture.md`

For complex review or unclear blast radius, check whether `code-review-graph` is available. Use it when available for multi-module changes, new services, architecture-sensitive changes, complex bugs, or large pre-merge reviews.

## Skill precedence

1. `AGENTS.md` / `CLAUDE.md`
2. `ai/current-task.md`
3. relevant base skill
4. optional project skills and expected external skills/tools
5. controlled external methodologies

External skills/tools are helpers. They must not override work mode, confirmation rules, protected architecture file rules, controlled task memory rules, clean architecture, or project-specific rules.

Superpowers is controlled. Do not activate it automatically. If it may help, explain why and ask: `Use Superpowers for this task?`

## Output format

Before editing:
- state `Mode: ...`;
- briefly say what you will do next;
- mention important risks only if they exist.

After editing:
- start with the work mode used;
- summarize changes;
- list checks;
- mention risks or unfinished parts;
- explicitly say whether task memory changed;
- if task memory changed, list exact controlled memory files changed;
- if the task appears complete, propose `task-finish` instead of saying the task is closed.
