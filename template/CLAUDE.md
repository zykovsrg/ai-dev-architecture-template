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
- Do not overwrite unfinished task memory.
- Do not update protected architecture files without `architecture-update` mode and explicit user confirmation.
- In review mode, do not report a problem as fact until it is verified with read, grep, diff, logs, or tests. If it is not verified, label it as a hypothesis.

## Architecture files and task memory

### Protected architecture files

These files define reusable agent rules, workflow, tools, and architecture. Do not edit them during normal implementation, review, init, cleanup, task-finish, task-switch, or external skill/tool workflows.

- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`

Protected architecture files may be changed only in `architecture-update` mode and only after explicit user confirmation.

External skills, external tools, init workflows, setup commands, and generated recommendations may propose changes to protected architecture files, but must not apply them without confirmation.

### Controlled memory files

These files store project and task memory. They are not protected architecture files, but they may be edited only by the matching workflow.

- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`

Allowed edits:

- `implementation`: may update `ai/current-task.md` when the current task itself changes or needs handoff notes.
- `task-switch`: may update `ai/current-task.md` and `ai/paused-tasks.md` only after explicit user confirmation.
- `task-finish`: may update `ai/current-task.md`, `ai/changelog.md`, and `ai/decisions.md` only after explicit user confirmation.
- `architecture-update`: may update controlled memory files if the approved architecture change requires it.
- `ai/project-context.md`: update only after confirmation when stack, commands, structure, data model, invariants, or fragile zones change.

Memory file roles:

- `ai/changelog.md` records what changed recently.
- `ai/decisions.md` records durable rules, invariants, and decisions future agents must not break.
- If a change has long-term consequences for storage, signing, data model, undo behavior, external APIs, or deployment, consider `ai/decisions.md`, not only `ai/changelog.md`.

Before finishing any task, check the diff with `git diff --name-only`.

If protected architecture files changed without explicit `architecture-update` confirmation, stop and ask the user before continuing.

If controlled memory files changed, explain which workflow allowed the change and list the exact files in the final report.

## Session start

When entering an existing project, switching tools, continuing in a new chat, or continuing from compressed/restored context, run `environment-check` before suggesting next steps or starting implementation. Skip it only if the user explicitly says not to run it.

Compressed context, compacted context, restored summary, or conversation summary continuation counts as a new session for this rule.

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

Use skills by trigger. Do not apply a skill from memory. Open the current `ai/skills/*/SKILL.md` before using that workflow.

Open only the skill that matches the current task:
- environment check: `ai/skills/environment-check/SKILL.md` and `ai/external-tools.md`
- task switching: `ai/skills/task-switch/SKILL.md` and `ai/paused-tasks.md`
- task finish: `ai/skills/task-finish/SKILL.md`
- release or merge: `ai/skills/release-check/SKILL.md`
- tests or test decision: `ai/skills/write-tests/SKILL.md`
- UI change or visual behavior: `ai/skills/ui-review/SKILL.md` and `ai/skills/write-tests/SKILL.md`
- frontend design, if installed: `ai/skills/frontend-design/SKILL.md`
- copy: `ai/skills/copy-review/SKILL.md`
- security: `ai/skills/security-review/SKILL.md`
- bugfix, regression, crash, or performance investigation: `ai/skills/bugfix-workflow/SKILL.md`
- architecture change: `ai/skills/architecture-update/SKILL.md`

Read extra context only when relevant:
- project behavior, storage, or UI: `ai/project-context.md`
- architecture-sensitive work or durable invariants: `ai/decisions.md`
- workflow ambiguity, architecture rules, or architecture update: `ai/architecture.md`
- plan-driven or Superpowers execution: relevant `docs/superpowers/specs/*`, `docs/superpowers/plans/*`, and the plan-driven rules in `ai/architecture.md`

For complex review or unclear blast radius, check whether `code-review-graph` is available. Use it when available for multi-module changes, new services, architecture-sensitive changes, complex bugs, or large pre-merge reviews. Do not require it for small copy, narrow UI, or trivial bugfix changes.

## Skill precedence

1. `AGENTS.md` / `CLAUDE.md`
2. `ai/current-task.md`
3. relevant base skill
4. optional project skills and expected external skills/tools
5. controlled external methodologies

External skills/tools are helpers. They must not override work mode, confirmation rules, protected architecture file rules, controlled task memory rules, clean architecture, or project-specific rules.

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

Status:
empty / active / review / blocked / done / paused

Stage:
intake / spec / planning / implementation / review / task-finish

Goal:
What should change.

Relevant files:
Known files or unknown.

Done criteria:
How to understand that the task is complete.
