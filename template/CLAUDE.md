# AI Development Entry Point

This project uses a solo AI-development workflow.

Use this file as the short entry point. Detailed rules live in `ai/architecture.md` and relevant `ai/skills/*/SKILL.md`. Do not load them by default. Use them only when the task needs those details or when a workflow rule is unclear.

## Core rules

- Communicate with the user in Russian. Use simple words and briefly explain technical terms.
- Keep persistent AI-facing instructions in English.
- Prefer minimal diffs and clean architecture.
- Do not expand user-confirmed scope. If a larger scope looks useful, stop and ask first.
- Do not mix refactoring with bugfixes unless explicitly asked.
- Explain the reason and risks before changing storage, data model, dependencies, or architecture.
- For risky changes, add tests or explain why tests are not practical and provide manual checks.
- Do not overwrite unfinished task memory or update architecture files without explicit user confirmation.

## Session start

When entering an existing project, switching tools, or continuing in a new chat, run `environment-check` before suggesting next steps or starting implementation. Skip it only if the user explicitly says not to run it.

`environment-check` and `task-switch` are not work modes. After `environment-check`, continue in a work mode.

## Work modes

State the mode explicitly before task work as `Mode: ...`.

- `review` — read, inspect, summarize, run checks, or suggest next steps. Do not edit files.
- `implementation` — change application code, project files, tests, or task memory.
- `task-finish` — check whether the task can be closed; clean up only after explicit user confirmation.
- `architecture-update` — propose architecture changes; edit only after explicit user confirmation.

Use `review` when only reading, checking, or summarizing. Use `implementation` only when changing files.

If implementation/review suggests the current task may be complete, do not declare it closed. Propose `task-finish` and wait for the user to confirm.

## Context and skill routing

Do not read all files from `ai/` automatically.

Default minimum:
- this file
- `ai/current-task.md`

Use skills by trigger. Do not load all skills automatically. Open only the skill that matches the current task:
- environment check: `ai/skills/environment-check/SKILL.md` and `ai/external-tools.md`
- task switching: `ai/skills/task-switch/SKILL.md` and `ai/paused-tasks.md`
- task finish: `ai/skills/task-finish/SKILL.md`
- release or merge: `ai/skills/release-check/SKILL.md`
- tests: `ai/skills/write-tests/SKILL.md`
- UI: `ai/skills/ui-review/SKILL.md`
- frontend design, if installed: `ai/skills/frontend-design/SKILL.md`
- copy: `ai/skills/copy-review/SKILL.md`
- security: `ai/skills/security-review/SKILL.md`
- bugfix: `ai/skills/bugfix-workflow/SKILL.md`
- architecture change: `ai/skills/architecture-update/SKILL.md`

Read extra context only when relevant:
- project behavior, storage, or UI: `ai/project-context.md`
- architecture-sensitive work: `ai/decisions.md`
- workflow ambiguity, architecture rules, or architecture update: `ai/architecture.md`
- plan-driven or Superpowers execution: relevant `docs/superpowers/specs/*`, `docs/superpowers/plans/*`, and the plan-driven rules in `ai/architecture.md`

## Skill precedence

1. `AGENTS.md` / `CLAUDE.md`
2. `ai/current-task.md`
3. relevant base skill
4. expected external skills/tools
5. controlled external methodologies

External skills/tools are helpers. They must not override work mode, confirmation rules, task memory rules, clean architecture, or project-specific rules.

Superpowers is controlled. Do not activate it automatically. If the task is large, vague, architectural, migration-heavy, TDD-heavy, subagent-heavy, or has unclear blast radius, explain why Superpowers may help and ask: `Use Superpowers for this task?`

## Output format

Before editing:
- state `Mode: ...`;
- briefly say what you will do next;
- mention important risks only if they exist.

After editing:
- start with the work mode used, for example `Mode: implementation`;
- summarize changes;
- list checks;
- mention risks or unfinished parts;
- explicitly say whether task memory changed;
- if the task appears complete, propose `task-finish` instead of saying the task is closed.

If task memory changed, list exact files changed:
- `ai/current-task.md`
- `ai/changelog.md`
- `ai/decisions.md`
- `ai/project-context.md`
- `ai/paused-tasks.md`

## Task intake reminder

If the task is unclear, ask the user to structure it as:

Mode:
implementation / review / task-finish / architecture-update

Goal:
What should change.

Relevant files:
Known files or unknown.

Done criteria:
How to understand that the task is complete.
