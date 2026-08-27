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

## Optional personal hub updates and migration

An existing standalone project is not converted automatically. Install the
separate hub only at a path named `_ai-hub`:

```bash
bash /path/to/ai-dev-architecture-template/scripts/install.sh --mode hub /path/to/_ai-hub
```

The installer creates `_ai-hub/projects/` and does not inspect, register, or
move a project. To relocate existing folders later, use the installed hub's
`hub-project-migrate` workflow: it requires a separately confirmed temporary
source, shows the exact source-to-destination mapping and Git status, and then
requires explicit move approval. Registration requires its own separate confirmation,
then the hub registry is validated. Only after that may the workflow offer an
optional cleanup of old standalone rules, with its own separate confirmation.
The cleanup is never automatic, preserves all project memory files, and keeps
`ai/skills/`, `.claude/`, and `.codex/` unchanged. It never copies folders or
moves them during installation or update.

For an installed hub, use its dedicated updater. Check first, then run a
dry-run; neither command changes files:

```bash
bash /path/to/ai-dev-architecture-template/scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/ai-dev-architecture-template --check
bash /path/to/ai-dev-architecture-template/scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/ai-dev-architecture-template --dry-run
```

After reviewing that dry-run and explicitly approving the update, apply it:

```bash
bash /path/to/ai-dev-architecture-template/scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/ai-dev-architecture-template --apply
```

The hub updater preserves hub-managed project memory. It does not register
projects, migrate a standalone project, clean up files, or create reminders.

## Optional confirmed Obsidian task sync

An updated hub can use the local task synchronizer only after the user reviews
its commands. The trusted architecture-to-Obsidian refresh rebuilds the
generated views from canonical `ai/` task records and still checks the manifest.
If Obsidian was edited manually, it stops with a pending proposal and does not
overwrite it. The reverse direction remains a confirmed Obsidian-to-architecture proposal:
inspect it with `status`, then use
`apply --confirm-proposal <sha256>` only for the exact reviewed change.

The watcher is optional and local. Preview its user plist after an update, then
install, check, or remove it explicitly:

```bash
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --preview
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --install --confirm-launchd-install
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --status
bash scripts/install-obsidian-task-sync.sh --hub /path/to/_ai-hub --scope /path/to/scope.txt --vault /path/to/_ai-hub/projects/ai-dev-architecture/obsidian-vault --uninstall --confirm-launchd-uninstall
```

`scan` creates only a local proposal. The separate install and uninstall flags
are not interchangeable and neither action is performed by an update.

Updating an installed hub also removes superseded paths listed by the
updater — hub skill directories that were renamed or retired upstream.
`--dry-run` (and `--check`, when it detects stale superseded paths) shows
the exact list of paths to be removed first, before anything is applied.

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

## Knowledge layer lifecycle

`knowledge/` is an optional local reference layer, not controlled memory. It
is separate from `ai/project-context.md`: project context stores the active
project facts needed for normal work, while knowledge stores explicitly
captured research, decisions, risks, and runbooks.

The normal updater never creates `knowledge/` in an existing pre-knowledge
project and never modifies existing records. It also does not turn a project
into a knowledge-enabled project merely because the newer template contains
knowledge files. This boundary applies to `--check`, `--dry-run`, `--apply`,
and `--commit`.

Existing-project knowledge enablement is available only through the hub's
`hub-knowledge-enable` workflow after the hub has confirmed the registered project.
Legacy standalone knowledge migration is out of scope.

Hub-created projects receive the quality cycle through central hub-owned
`hub-knowledge-capture` and `hub-knowledge-review` workflows. The hub does not copy
generic project skills or entry files into individual projects.

Create or edit a knowledge record only through `hub-knowledge-capture` or
`hub-knowledge-review`, after the workflow has selected the exact path and the
user has explicitly confirmed the write. Valid statuses are `draft`,
`verified`, `needs-review`, `stale`, and `superseded`. At `hub-task-finish`, an
agent may offer a focused knowledge review when it is relevant; the offer does
not authorize a review or an edit.

Capture and review canonicalize the project and selected paths, reject absolute
paths, traversal, and symlink components, and prohibit secrets, personal data,
and client data. Review validates exact types and statuses, record and source
dates, contradictions, and type/category agreement. Stale and superseded
records remain in place and link to replacements.

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

- `ai/current-task.md` — through `hub-task-intake`, the current task, `hub-task-switch`, or `hub-task-finish`;
- `ai/paused-tasks.md` — through `hub-task-switch`;
- `ai/future-tasks.md` — for future tasks explicitly saved by the user or confirmed as future task candidates;
- `ai/project-context.md` — after confirmation, when the stack, commands, structure, data model, invariants, or fragile zones change;
- `ai/decisions.md` — when a durable decision appears that future agents must not break;
- `ai/changelog.md` — through a confirmed `hub-task-finish` or an approved `architecture-update`.

## 6. Safe update rule

For an existing project:

1. Run the updater in `--dry-run`.
2. Compare the protected architecture files and controlled memory files.
3. Make sure project-specific additions will not be lost.
4. Apply the update only if the diff is clear.
5. Before a merge or release, run `release-check`.
6. After the update, run `hub-environment-check` and review the final menu of available commands and skills.

The menu after `hub-environment-check` is informational. It does not mean the agent should automatically run `hub-task-switch`, `hub-task-finish`, `architecture-update`, or other workflows.

## 7. When code-review-graph is useful

Suggest `code-review-graph` when:

- it is unclear which files are related to each other;
- the diff touches several modules;
- there is a risk of breaking neighboring screens or dependencies;
- you need to quickly understand the blast radius of a change;
- the update touches new services, resolvers, adapters, or architecture-sensitive logic.

If `code-review-graph` is unavailable, that is a warning, not a blocker by default.
