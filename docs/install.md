# Installation guide

The easiest way is the [universal start prompt](../README.md#установка-в-проект-универсальный-стартовый-промт): copy it into an AI agent opened in the project folder, and it will perform the installation itself. The instructions below are for manual installation.

## 1. Clone the template repository

```bash
cd ~/Documents
git clone git@github.com:zykovsrg/ai-dev-architecture-template.git
```

## 2. Go to your project

```bash
cd /path/to/project
```

Example:

```bash
cd /Users/zykovsrg/Desktop/goal-planner-macos
```

## 3. Safely copy the template

```bash
rsync -av --ignore-existing ~/Documents/ai-dev-architecture-template/template/ ./
```

This command:

- copies new files into the project;
- does not overwrite existing files;
- reduces the risk of losing project data.

## 4. Verify the installed files

```bash
ls AGENTS.md CLAUDE.md
find ai -maxdepth 4 -type f | sort
```

Expected files:

```text
AGENTS.md
CLAUDE.md
ai/architecture.md
ai/changelog.md
ai/external-tools.md
ai/current-task.md
ai/paused-tasks.md
ai/future-tasks.md
ai/decisions.md
ai/project-context.md
ai/skills/task-intake/SKILL.md
ai/skills/start-screen/SKILL.md
ai/skills/architecture-update/SKILL.md
ai/skills/environment-check/SKILL.md
ai/skills/copy-review/SKILL.md
ai/skills/release-check/SKILL.md
ai/skills/security-review/SKILL.md
ai/skills/task-finish/SKILL.md
ai/skills/task-switch/SKILL.md
ai/skills/ui-review/SKILL.md
ai/skills/write-tests/SKILL.md
```

## 5. Fill in the project files

After installation, be sure to fill in:

- `ai/project-context.md`
- `ai/current-task.md`

These can stay as empty templates until real decisions, changes, pauses, or future tasks appear:

- `ai/decisions.md`
- `ai/changelog.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`

`ai/external-tools.md` usually does not need changes after installation. Update it only when the list of expected external skills, tools, or controlled methodologies changes.

## 6. Run environment-check

After installation, ask the agent to run `environment-check`.

The check should report:

- which required files and skills are in place;
- what is missing;
- which optional skills or external tools are not confirmed;
- whether the architecture is ready for the first task;
- which next commands and skills are available.

The final list of commands and skills is a menu, not an instruction to run everything.

The start screen is in `getting-started/getting-started.md`.
Ready-made prompts are in `docs/prompts.md` and `docs/start-prompts.md`.
