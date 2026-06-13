# Промты

## Проверить синхронизацию шаблона

```text
Mode: review

Goal:
Check whether the AI development architecture template is synchronized correctly.

Read:
- AGENTS.md
- CLAUDE.md
- ai/architecture.md
- ai/current-task.md
- ai/paused-tasks.md
- ai/project-context.md
- ai/decisions.md
- ai/changelog.md
- ai/external-tools.md
- all ai/skills/*/SKILL.md files

Do not edit files.

Check:
1. Are all required files present?
2. Are AGENTS.md and CLAUDE.md short enough?
3. Are all 10 base skills present, including task-switch and environment-check?
4. Does task-finish replace old task-completion-check and task-cleanup?
5. Are permanent AI-facing instruction files in English?
6. Are project-specific files still templates and not filled with data from another project?
7. Is there duplicated or conflicting guidance?

Return:
1. What is correct.
2. What is missing.
3. What should be fixed before using the template.

Explain in Russian with simple words.
```

## Собрать `project-context.md`

```text
Mode: review

Goal:
Collect information for ai/project-context.md for this specific project.

Read:
- README if present
- package.json, pyproject.toml, requirements.txt, or other dependency files
- main source folders
- app entry points
- build scripts
- test scripts
- storage and data model files if present

Do not edit files.

Return a draft for ai/project-context.md.

Include:
1. What this project is.
2. Tech stack.
3. How to run locally.
4. How to build.
5. How to run tests.
6. Main folders and files.
7. Main screens or modules.
8. Data model or core entities.
9. Project invariants: what must not be broken.
10. Known fragile areas.

Write in Russian or English. Use simple wording. Briefly explain technical terms.
```

## Собрать `decisions.md`

```text
Mode: review

Goal:
Collect initial important architecture and product decisions for ai/decisions.md.

Read:
- README
- ai/project-context.md
- data model files
- storage files
- important frontend/backend modules
- recent git history if available

Do not edit files.

Return a draft for ai/decisions.md.

Include only important active decisions:
1. Data model decisions.
2. Product rules.
3. Architecture constraints.
4. Known temporary workarounds.
5. Decisions that future agents must not accidentally break.

Use format:

## YYYY-MM-DD — Decision title

Status: active / superseded / resolved

Decision:
...

Why:
...

Impact:
...

Do not include minor bugfixes, colors, spacing, or ordinary changelog entries.
```

## Собрать `changelog.md`

```text
Mode: review

Goal:
Collect initial changelog for ai/changelog.md.

Read:
- git log for the last 2–4 weeks
- recent commits
- README
- ai/project-context.md

Do not edit files.

Return a concise draft for ai/changelog.md.

Include:
1. Only notable product, architecture, data model, UI, build, or testing changes.
2. No tiny implementation details.
3. No cosmetic-only changes unless they affected user experience.

Use format:

# Changelog

## YYYY-MM-DD

- Change:
- Impact:
- Manual checks:
```

## Проверить установку в проекте

```text
Mode: review

Goal:
Check whether AI development architecture is installed correctly in this project.

Use:
- ai/skills/environment-check/SKILL.md

Read:
- AGENTS.md
- CLAUDE.md
- ai/architecture.md
- ai/current-task.md
- ai/paused-tasks.md
- ai/project-context.md
- ai/decisions.md
- ai/changelog.md
- ai/external-tools.md
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

Do not edit files.

Return:
1. What is installed correctly.
2. What is missing.
3. What may waste tokens.
4. What must be filled with project-specific information.
5. Whether the architecture is ready for the first task.

Explain in Russian with simple words.
```

## Безопасно обновить существующий проект

```text
Mode: review

Goal:
Compare the current project AI architecture with the updated template and propose a safe update plan.

Compare protected architecture files:
- ~/Documents/ai-dev-architecture-template/template/AGENTS.md with ./AGENTS.md
- ~/Documents/ai-dev-architecture-template/template/CLAUDE.md with ./CLAUDE.md
- ~/Documents/ai-dev-architecture-template/template/ai/architecture.md with ./ai/architecture.md
- ~/Documents/ai-dev-architecture-template/template/ai/external-tools.md with ./ai/external-tools.md
- ~/Documents/ai-dev-architecture-template/template/ai/skills/*/SKILL.md with ./ai/skills/*/SKILL.md

Do not overwrite controlled memory files:
- ai/current-task.md
- ai/paused-tasks.md
- ai/project-context.md
- ai/decisions.md
- ai/changelog.md

Do not edit files.

Important:
- Protected architecture files may be updated only after explicit approval.
- Controlled memory files must not be replaced from the template.
- Preserve project-specific additions unless they are outdated or duplicated.
- If the update has unclear blast radius, recommend code-review-graph.

Return:
1. Which template files changed.
2. Which protected architecture files should be updated.
3. Which controlled memory files must be preserved.
4. What project-specific content must be preserved.
5. What exact changes you recommend.
6. Whether it is safe to apply the update.

Explain in Russian with simple words.
```

## First session environment check

```text
Mode: review

Goal:
Check whether the AI development architecture has all required base skills and expected external skills/tools available.

Use:
- ai/skills/environment-check/SKILL.md

Check required files:
- AGENTS.md
- CLAUDE.md
- ai/architecture.md
- ai/current-task.md
- ai/paused-tasks.md
- ai/project-context.md
- ai/decisions.md
- ai/changelog.md
- ai/external-tools.md
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

Check expected external skills and tools:
- code-review-graph
- agent-skills-for-context-engineering
- claude-seo

Check controlled external methodologies:
- Superpowers

Check optional external alternatives only if relevant.

Do not edit files.
Do not install missing tools.

Return:
1. Required files present.
2. Required files missing.
3. Optional tools present.
4. Expected external tools missing or not confirmed. Controlled external methodologies and optional alternatives are not blockers.
5. Whether the architecture is ready for the first task.
6. What to restore from the template if something is missing.

Explain in Russian with simple words.
```

## Switch to another task safely

```text
Mode: review

Goal:
Check whether the current unfinished task can be paused or replaced safely.

Use:
- ai/skills/task-switch/SKILL.md

Read:
- ai/current-task.md
- ai/paused-tasks.md

Do not edit files.

First:
Decide whether this is a different task. A task is different if the new request changes the goal, work mode, main files, Done criteria, or creates a separate deliverable.

Return:
1. Current unfinished task.
2. New requested task.
3. Risk of switching.
4. Recommended option:
   - continue current task;
   - pause current task and start a new one;
   - finish current task through task-finish;
   - discard current task and replace it.
5. What would be written to ai/paused-tasks.md.
6. What would be written to ai/current-task.md.

Ask for explicit confirmation before editing files.

Explain in Russian with simple words.
```
