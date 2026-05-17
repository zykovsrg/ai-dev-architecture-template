---
name: environment-check
type: knowledge
description: |
  Use at the start of a new project session to check whether required base skills, optional project skills, and expected external skills/tools are available.
  Activates when:
  - starting work in a project after installing the architecture
  - user asks "проверь окружение", "всё ли установлено", "первый запуск", or similar
  - before the first real implementation task in a project
  Does NOT activate for:
  - every normal task
  - small follow-up questions
  - checking application dependencies
---

# Environment Check

This skill checks whether the AI-development architecture is installed correctly.

It does not check application dependencies.

## Required base skills

Check that these files exist:

- `ai/skills/bugfix-workflow/SKILL.md`
- `ai/skills/ui-review/SKILL.md`
- `ai/skills/security-review/SKILL.md`
- `ai/skills/release-check/SKILL.md`
- `ai/skills/copy-review/SKILL.md`
- `ai/skills/write-tests/SKILL.md`
- `ai/skills/task-finish/SKILL.md`
- `ai/skills/task-switch/SKILL.md`
- `ai/skills/architecture-update/SKILL.md`
- `ai/skills/environment-check/SKILL.md`

## Required entry files

Check that these files exist:

- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`

## Optional project skills

Check optional project skills only for presence.

Currently known optional project skills:

- `ai/skills/frontend-design/SKILL.md`

Missing optional project skills are not blockers.
Report optional project skills as:

- `present`
- `not installed, not a blocker`

Do not restore, install, or create optional project skills unless the user explicitly asks.

## Expected external skills/tools

Read:

- `ai/external-tools.md`

Check whether expected external skills and tools are available:

- code-review-graph
- agent-skills-for-context-engineering
- claude-seo

Controlled external methodologies:
- Superpowers

Do not install missing external tools automatically.
If a tool cannot be verified, report it as `not confirmed`.

## Output

Return:

1. Required files present.
2. Required files missing.
3. Optional project skills present or not installed.
4. Expected external tools present.
5. Expected external tools missing or not confirmed.
6. Controlled external methodologies present, missing, or not confirmed.
7. Whether the architecture is ready for the first task.
8. What to restore from the template if something required is missing.

Explain in Russian with simple words.

## Rules

- Do not read every skill file in full unless a file looks broken or the user asks for a deeper check.
- Do not treat missing optional project skills as blockers.
- Do not treat missing external tools as blockers, but report them clearly.
- Do not install missing tools without explicit user confirmation.
- Do not change application code.

- Do not activate Superpowers during environment check. Only report whether it is present, missing, or not confirmed.
- Superpowers is a controlled methodology, not the default workflow.
