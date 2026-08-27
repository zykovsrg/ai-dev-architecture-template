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

## Optional confirmed Obsidian task sync

For a hub whose `ai-dev-architecture` project has a local `obsidian-vault/`,
the trusted architecture-to-Obsidian refresh creates the generated Kanban
only from canonical `ai/` task records. It keeps manifest validation: a manual
Obsidian edit creates a pending proposal and the refresh does not overwrite it.
The reverse path is a confirmed Obsidian-to-architecture proposal and never
writes canonical records until its exact SHA-256 is confirmed.

Preview the optional local watcher first. It only scans and stores a local
proposal; it never applies one:

```bash
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --preview
```

Install it only after reviewing the preview. The user launchd job scans every
10 seconds and needs a separate `--confirm-launchd-install` flag:

```bash
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --install --confirm-launchd-install
```

Check or remove it with separate commands. Removal has its own
`--confirm-launchd-uninstall` flag:

```bash
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --status
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --uninstall --confirm-launchd-uninstall
```

To inspect or deliberately apply a manual board edit, use `scan`, `status`, and
then `apply --confirm-proposal <sha256>` from `scripts/obsidian-task-sync.sh`.

Do not use hub installation to convert or move an existing standalone project.
From the installed hub, use `hub-project-migrate`: it inventories only direct-child
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
ai/skills/hub-task-intake/SKILL.md
ai/skills/start-screen/SKILL.md
ai/skills/architecture-update/SKILL.md
ai/skills/hub-environment-check/SKILL.md
ai/skills/impeccable/SKILL.md
ai/skills/theme-factory/SKILL.md
ai/skills/animate/SKILL.md
ai/skills/design-motion-principles/SKILL.md
ai/skills/copy-review/SKILL.md
ai/skills/release-check/SKILL.md
ai/skills/security-review/SKILL.md
ai/skills/hub-task-finish/SKILL.md
ai/skills/hub-task-switch/SKILL.md
ai/skills/ui-review/SKILL.md
ai/skills/write-tests/SKILL.md
```

## Optional local knowledge

A new standalone installation also includes the optional `knowledge/` layer:
its README, record template, and `research`, `decisions`, `risks`, and
`runbooks` categories. It is separate from `ai/project-context.md`: context
holds the project facts needed for ordinary work, while knowledge stores
explicitly captured reference records.

Use `hub-knowledge-capture` to propose a record and `hub-knowledge-review` to assess a
selected record or set. Both workflows require an exact path and explicit user
confirmation before creating or changing content. Record statuses are limited
to `draft`, `verified`, `needs-review`, `stale`, and `superseded`.
They reject absolute paths, traversal, and symlink components, and prohibit
secrets, personal data, and client data.

The normal architecture updater never enables this layer for an existing
pre-knowledge project and never changes its records. `hub-task-finish` may offer a
focused knowledge review when relevant, but it never starts that review or
edits knowledge without a request and confirmation.

Existing-project knowledge enablement is available only through the hub's
`hub-knowledge-enable` workflow after the hub has confirmed the registered project.
Legacy standalone knowledge migration is out of scope.

Hub-created projects use the hub's central `hub-knowledge-capture` and
`hub-knowledge-review` workflows. Generic project skills are not copied into each
project. The hub `hub-task-finish` workflow may offer the same focused review after
its normal completion check, but never starts it automatically.

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

After installation, ask the agent to run `hub-environment-check`.

The check should report:

- which required files and skills are in place;
- what is missing;
- which optional skills or external tools are not confirmed;
- whether the architecture is ready for the first task;
- which next commands and skills are available.

The final list of commands and skills is a menu, not an instruction to run everything.

The start screen is in `getting-started/getting-started.md`.
Ready-made prompts are in `docs/prompts.md` and `docs/start-prompts.md`.
