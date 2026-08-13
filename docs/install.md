# Installation guide

The easiest way is the [universal start prompt](../README.md#установка-в-проект-универсальный-стартовый-промт): copy it into an AI agent opened in the project folder, and it will perform the installation itself. The instructions below are for manual installation.

## Installation modes

The template has two modes:

- **Standalone** is the normal, self-contained architecture for one project.
- **Personal hub** is optional. It is a separate local router for registered
  projects and always starts in a directory named `_ai-hub`. Its projects live
  only in `_ai-hub/projects/<project-id>`.

During a first interactive installation, `scripts/install.sh` asks whether to
install the optional hub. A non-interactive invocation defaults to standalone.
The hub never selects, registers, or reads a project before the user confirms
that project.

Install standalone mode explicitly:

```bash
bash /path/to/ai-dev-architecture-template/scripts/install.sh --mode standalone /path/to/project
```

Install a hub explicitly. The installer creates its only project root,
`_ai-hub/projects/`, itself:

```bash
bash /path/to/ai-dev-architecture-template/scripts/install.sh --mode hub /path/to/_ai-hub
```

The hub repository ignores `/projects/`. Each project can therefore retain its
own `.git/` directory, history, and remote repository without becoming part of
the hub repository.

Do not use hub installation to convert or move an existing standalone project.
From the installed hub, use `project-migrate`: it inventories only direct-child
names in a separately confirmed temporary source, shows an exact move preview,
and waits for explicit move confirmation. After a successful move, registration
has its own confirmation and is followed by `scripts/check-hub-registry.sh`.
Only after validation may the workflow offer a separately confirmed cleanup of
old standalone rules. The cleanup is optional and never automatic; all project
memory files are preserved. It never runs during installation.

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
ai/skills/impeccable/SKILL.md
ai/skills/theme-factory/SKILL.md
ai/skills/animate/SKILL.md
ai/skills/design-motion-principles/SKILL.md
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
