---
name: environment-check
type: knowledge
description: |
  Use at the start of a new project session to check whether required base skills, optional project skills, expected external skills/tools, current task state, and future task state are available.
  Activates when:
  - starting work in a project after installing the architecture
  - entering an existing project
  - switching tools or agents
  - continuing in a new chat
  - continuing from compressed, compacted, restored, or summarized context
  - user asks "проверь окружение", "всё ли установлено", "первый запуск", or similar
  - before the first real implementation task in a project
  Does NOT activate for:
  - every normal task inside the same uninterrupted session
  - small follow-up questions
  - checking application dependencies
---

# Environment Check

This skill checks whether the AI-development architecture is installed correctly.

It does not check application dependencies.

## Session boundary rule

Run this check before suggesting next steps or starting implementation when the agent enters a new session.

The following count as a new session:

- new chat;
- switching from one AI tool to another;
- context compaction;
- compressed context resume;
- restored summary;
- conversation summary continuation.

Skip only if the user explicitly says not to run `environment-check`.

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
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
- `ai/external-tools.md`

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

## Current and future task snapshot

Read:

- `ai/current-task.md`
- `ai/future-tasks.md`

Include a short task snapshot in the response before the final commands/skills menu.

Use the title:

```text
Текущая и будущие задачи
```

For `ai/current-task.md`, report only the operational summary:

- current task title or short goal, if present;
- `Status`;
- `Stage`;
- next step or open blocker, if obvious from the file.

If there is no active task, say that no active current task is recorded.

For `ai/future-tasks.md`, report only a compact summary:

- total number of future task entries, if easy to count;
- count by status, if statuses are present;
- up to 5 active useful entries, prioritizing `ready`, `idea`, and `blocked`.

If `ai/future-tasks.md` is empty, say that no future tasks are recorded.

Do not paste the full files. Do not rewrite task wording unless summarizing for readability.

This snapshot is informational. It must not:

- edit `ai/current-task.md`;
- edit `ai/future-tasks.md`;
- promote a future task;
- mark a task as done, dropped, or paused;
- start `task-switch` or `task-finish` automatically.

## Output

Return:

1. Required files present.
2. Required files missing.
3. Optional project skills present or not installed.
4. Expected external tools present.
5. Expected external tools missing or not confirmed.
6. Controlled external methodologies present, missing, or not confirmed.
7. Current task snapshot.
8. Future tasks snapshot.
9. Whether the architecture is ready for the first task or resumed task.
10. What to restore from the template if something required is missing.
11. Available next commands and skills.

Explain in Russian with simple words.

## Available next commands and skills block

Always end the environment-check response with a short block titled:

```text
Доступные следующие команды и skills
```

This block is a menu, not an instruction to run all workflows.
Do not activate any listed skill automatically unless the user asks or the next task clearly triggers it.

Include these base options:

- `environment-check` — повторно проверить архитектуру после смены агента, нового чата или восстановления контекста.
- `task-switch` — переключиться на другую задачу, поставить текущую на паузу или продвинуть future task в текущую задачу.
- `task-finish` — проверить, можно ли закрыть текущую задачу, и выполнить cleanup после подтверждения.
- `architecture-update` — изменить правила архитектуры, workflow, skills или защищённые architecture files.
- `bugfix-workflow` — разбирать баги, регрессии, flaky behavior, debug requests и performance-проблемы.
- `ui-review` — проверить UI, layout, визуальные состояния и поведение интерфейса.
- `write-tests` — решить, нужны ли тесты, и добавить тесты для рискованных изменений.
- `release-check` — проверить diff перед commit, merge или релизом.
- `security-review` — проверить изменения на риски безопасности.
- `copy-review` — проверить пользовательские тексты.
- `future-tasks` — сохранить идею на потом в `ai/future-tasks.md`; отдельного skill нет.

If optional project skills are present, add them under:

```text
Опционально доступно
```

Example:

- `frontend-design` — UI/frontend/design задачи, если `ai/skills/frontend-design/SKILL.md` установлен.

If expected external tools are present or not confirmed, mention them separately under:

```text
Внешние tools и methodologies
```

For Superpowers, always say that it is controlled and must not be activated automatically.

## Rules

- Do not read every skill file in full unless a file looks broken or the user asks for a deeper check.
- Do not treat missing optional project skills as blockers.
- Do not treat missing external tools as blockers, but report them clearly.
- Do not install missing tools without explicit user confirmation.
- Do not change application code.
- Do not edit controlled memory files during environment-check.
- Do not promote, pause, finish, drop, or start tasks during environment-check.
- Do not activate Superpowers during environment check. Only report whether it is present, missing, or not confirmed.
- Superpowers is a controlled methodology, not the default workflow.
