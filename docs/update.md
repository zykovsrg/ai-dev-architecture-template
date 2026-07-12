# Update guide

The easiest way is the [universal start prompt](../README.md#установка-в-проект-универсальный-стартовый-промт): copy it into an AI agent opened in the project folder, and it will check the version and offer an update. The instructions below are for manual updating.

## Safe way

The safest path is to download the script, review it, and only then run it.

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh -o /tmp/update-installed-architecture.sh
less /tmp/update-installed-architecture.sh
bash /tmp/update-installed-architecture.sh --check
```

The `curl | bash` form below is more convenient, but it immediately runs a script downloaded from the internet. Use it only if you trust the source and understand what the command will do.

## First — check the version

The quick command compares the architecture version in the project with the latest in the repository. If the project is behind, it prints the versions and immediately shows a dry-run (a preview of changes), **without changing anything**:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --check
```

Exit code: `0` — up to date, `1` — an update is available. If the architecture is out of date, apply the update with the commands below.

## Quick update

For projects already in use, the main update path is the automatic updater:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --dry-run
```

If the diff looks fine:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --apply --commit
```

The detailed guide is in `docs/update-installed-projects.md`.

## What the updater does

The updater updates the protected architecture files:

```text
AGENTS.md
CLAUDE.md
ai/architecture.md
ai/external-tools.md
ai/skills/*
```

Controlled memory files are not overwritten:

```text
ai/current-task.md
ai/paused-tasks.md
ai/future-tasks.md
ai/project-context.md
ai/decisions.md
ai/changelog.md
```

The lists above describe the updater's behavior. The canonical full lists of protected files and controlled memory are in [file-roles.md](file-roles.md).

If a controlled memory file is missing, the updater creates it from the template. If the file already exists, it stays as is.

## 1. Update the template repository manually

If you use a local clone of the template:

```bash
cd ~/Documents/ai-dev-architecture-template
git pull origin main
```

## 2. Run the updater from the local clone

```bash
cd /path/to/project
bash ~/Documents/ai-dev-architecture-template/scripts/update-installed-architecture.sh --source ~/Documents/ai-dev-architecture-template --dry-run
```

Apply and commit:

```bash
bash ~/Documents/ai-dev-architecture-template/scripts/update-installed-architecture.sh --source ~/Documents/ai-dev-architecture-template --apply --commit
```

## 3. If the updater is unavailable

You can manually add new template files without overwriting existing ones:

```bash
cd /path/to/project
rsync -av --ignore-existing ~/Documents/ai-dev-architecture-template/template/ ./
```

This command copies only files that do not yet exist in the project. It does not overwrite existing files.

After v6.0, check whether the new file appeared:

```bash
test -f ai/future-tasks.md || cp ~/Documents/ai-dev-architecture-template/template/ai/future-tasks.md ai/future-tasks.md
```

## 4. Do not overwrite files blindly

First compare the template with the project:

```bash
diff -ru ~/Documents/ai-dev-architecture-template/template/AGENTS.md ./AGENTS.md
diff -ru ~/Documents/ai-dev-architecture-template/template/CLAUDE.md ./CLAUDE.md
diff -ru ~/Documents/ai-dev-architecture-template/template/ai/architecture.md ./ai/architecture.md
diff -ru ~/Documents/ai-dev-architecture-template/template/ai/external-tools.md ./ai/external-tools.md
diff -ru ~/Documents/ai-dev-architecture-template/template/ai/skills ./ai/skills
```

## 5. Protected architecture files and controlled memory files

The full lists of protected files and controlled memory are in [file-roles.md](file-roles.md).

When updating an existing project, do not copy protected architecture files over the current files without a diff and review. Do not replace controlled memory files with the template.

They may be updated only as project memory:

- `ai/current-task.md` — through `task-intake`, the current task, `task-switch`, or `task-finish`;
- `ai/paused-tasks.md` — through `task-switch`;
- `ai/future-tasks.md` — for future tasks explicitly saved by the user or confirmed as future task candidates;
- `ai/project-context.md` — after confirmation, when the stack, commands, structure, data model, invariants, or fragile zones change;
- `ai/decisions.md` — when a durable decision appears that future agents must not break;
- `ai/changelog.md` — through a confirmed `task-finish` or an approved `architecture-update`.

## 7. Safe update rule

For an existing project:

1. Run the updater in `--dry-run`.
2. Compare the protected architecture files and controlled memory files.
3. Make sure project-specific additions will not be lost.
4. Apply the update only if the diff is clear.
5. Before a merge or release, run `release-check`.
6. After the update, run `environment-check` and review the final menu of available commands and skills.

The menu after `environment-check` is informational. It does not mean the agent should automatically run `task-switch`, `task-finish`, `architecture-update`, or other workflows.

## 8. When code-review-graph is useful

Suggest `code-review-graph` when:

- it is unclear which files are related to each other;
- the diff touches several modules;
- there is a risk of breaking neighboring screens or dependencies;
- you need to quickly understand the blast radius of a change;
- the update touches new services, resolvers, adapters, or architecture-sensitive logic.

If `code-review-graph` is unavailable, that is a warning, not a blocker by default.
