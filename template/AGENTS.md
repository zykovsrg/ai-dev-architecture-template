# AI Development Entry Point

This project uses a solo AI-development workflow.

## Always follow

- Make a short plan before editing code.
- Prefer minimal diffs.
- Do not expand user-confirmed scope during implementation. If a larger scope looks useful, stop and ask first.
- Do not accumulate technical debt or temporary solutions. Keep the application architecture clean.
- Do not rewrite large files unless necessary.
- Do not mix refactoring with bugfixes unless explicitly asked.
- Do not change storage or data model without migration.
- Do not add dependencies without explaining why.
- For risky changes, add automated tests or explicitly explain why tests are not practical and provide manual checks.
- Do not clean ai/current-task.md without explicit user confirmation.
- Do not overwrite an unfinished ai/current-task.md when switching tasks without explicit user confirmation.
- Do not update architecture files without explicit user confirmation.
- Communicate with the user in Russian. Use simple words and briefly explain technical terms.
- Keep AI-facing instructions in English.

## Session start check

At the start of a new project session, use `environment-check` to check whether required base skills and expected external skills/tools are available.

When entering an existing project, switching tools, or continuing in a new chat, run `environment-check` before suggesting next steps or starting implementation. Do not skip it unless the user explicitly says not to run it.

`environment-check` is not a work mode. `task-switch` is also not a work mode; it is a safety workflow for switching between unfinished tasks. After the session check, continue in one of the work modes below.

Required base skills:
- ai/skills/bugfix-workflow/SKILL.md
- ai/skills/ui-review/SKILL.md
- ai/skills/security-review/SKILL.md
- ai/skills/release-check/SKILL.md
- ai/skills/copy-review/SKILL.md
- ai/skills/write-tests/SKILL.md
- ai/skills/task-finish/SKILL.md
- ai/skills/task-switch/SKILL.md
- ai/skills/architecture-update/SKILL.md
- ai/skills/environment-check/SKILL.md

Expected external skills/tools:
- code-review-graph
- agent-skills-for-context-engineering
- claude-seo

Controlled external methodologies:
- Superpowers

External skills and tools are expected when available. Do not install missing tools automatically. Report what is present, what is missing, and what is not confirmed.

## Work modes

Before starting, identify the current mode and state it explicitly as `Mode: ...`.

- implementation — make code changes.
- review — read files, inspect state or diff, summarize context, or report issues; do not edit files.
- task-finish — check whether the task can be closed; clean up only after explicit user confirmation; do not change application code.
- architecture-update — propose updates to development architecture. Before editing, show: current rule → proposed rule → exact files. Ask: “Replace this?” Do not edit files without confirmation.

Do not assume the mode. Follow the user request. If the mode is unclear, ask or infer the most likely mode and state the assumption before acting.

Use `review` when you only read files, summarize context, inspect project state, run environment-check, or suggest the next step without editing.
Use `implementation` only when you are going to change application code, project files, tests, or task memory.

## Skill precedence

Project architecture files define workflow priority:

1. `AGENTS.md` / `CLAUDE.md`
2. `ai/current-task.md`
3. relevant base skill
4. expected external skills/tools
5. controlled external methodologies

External skills and tools are helpers. They must not override work mode, user confirmation rules, task-finish rules, architecture-update rules, clean architecture principle, or project-specific rules.

Superpowers is a controlled external methodology. It may be installed and checked, but do not use it unless the user explicitly asks for it or `ai/current-task.md` says `Use Superpowers: yes`.

If a task matches Superpowers triggers, do not activate Superpowers automatically. First explain why it may help and ask the user: `Use Superpowers for this task?`

Superpowers triggers include large or vague tasks, architecture design, choosing between technical options, data model changes, migrations, TDD, subagents, major refactoring, or unclear blast radius.

If an external skill suggests a heavier workflow, use it only when it fits the current task or the user explicitly asks for it.

## Project context

Project-specific rules, invariants, commands, screens, data model, and fragile areas live in:
- ai/project-context.md

Read it only when the task touches project-specific behavior, architecture, storage, screens, or ai/current-task.md asks for it.

## Context routing

Do not read all files from ai automatically.

Use only relevant files:
- current task: ai/current-task.md
- architecture-sensitive work: ai/project-context.md, ai/decisions.md
- UI: ai/skills/ui-review/SKILL.md
- security: ai/skills/security-review/SKILL.md
- release or merge: ai/skills/release-check/SKILL.md
- tests: ai/skills/write-tests/SKILL.md
- copy: ai/skills/copy-review/SKILL.md
- finish task: ai/skills/task-finish/SKILL.md
- task switching: ai/skills/task-switch/SKILL.md, ai/paused-tasks.md
- architecture rule change: ai/skills/architecture-update/SKILL.md
- session start check: ai/skills/environment-check/SKILL.md
- external tools: ai/external-tools.md

## Output style

Use Russian and simple words. Briefly explain technical terms.

Before editing:
- state the current work mode explicitly;
- briefly explain what you will do next in simple words;
- mention important risks only if they exist.

Do not list technical files before editing unless it helps the user understand the change or the user asks for it.

After editing:
- start with the work mode used, for example `Mode: implementation`;
- summarize changes;
- list manual checks;
- mention risks or unfinished parts;
- explicitly say whether task memory changed.

If task memory changed, list exactly which files changed:
- ai/current-task.md
- ai/changelog.md
- ai/decisions.md
- ai/project-context.md
- ai/paused-tasks.md

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
