# Updating the architecture in projects already using it

This guide is for projects where the architecture is already installed.

The goal of the update: quickly pull the current rules and base skills from `zykovsrg/ai-dev-architecture-template` without wiping the working memory of the specific project.

## What is updated automatically

The updater updates the protected architecture files:

```text
AGENTS.md
CLAUDE.md
ai/architecture.md
ai/external-tools.md
ai/skills/*
```

If `.claude/` or `.codex/` appear in the template, the updater will also be able to pull files from those directories.

## What is not overwritten

The updater does not wipe the project's controlled memory files:

```text
ai/project-context.md
ai/current-task.md
ai/decisions.md
ai/changelog.md
ai/paused-tasks.md
ai/future-tasks.md
```

If a memory file is missing, the updater creates it from the template. If the file already exists, it stays as is.

The lists above describe the updater's behavior. The canonical full lists of protected files and controlled memory are in [file-roles.md](file-roles.md).

## Check the version

To find out whether the architecture in the project is behind, run the version check. It compares the project's version with the latest in the repository and, if the project is behind, shows a dry-run without changing anything:

Safe way:

```bash
cd /path/to/project
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh -o /tmp/update-installed-architecture.sh
less /tmp/update-installed-architecture.sh
bash /tmp/update-installed-architecture.sh --check
```

Quick way:

```bash
cd /path/to/project
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --check
```

Exit code `0` — up to date, `1` — an update is available. Locally from a clone: `bash scripts/update-installed-architecture.sh --source /path/to/ai-dev-architecture-template --check`.

## Quick safe run

Go to the project:

```bash
cd /path/to/project
```

Run a dry run first:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --dry-run
```

The dry run changes nothing. It only shows the diff.

If you do not want to run the downloaded script right away, download it to `/tmp`, review it with `less`, then run `bash /tmp/update-installed-architecture.sh --dry-run`.

If the diff looks fine, apply the update and commit right away:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --apply --commit
```

The commit will be named:

```text
chore: update AI development architecture
```

## If the project is not in a clean state

By default the updater does not apply changes if the project already has uncommitted changes.

It is better to save the current work first:

```bash
git status
git add .
git commit -m "wip: save current work"
```

If you deliberately want to apply the update on top of uncommitted changes, add the flag:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --apply --commit --allow-dirty
```

Use `--allow-dirty` only if you understand which changes already exist in the project.

## Local update from a clone of the architecture

If the architecture repository is already downloaded locally:

```bash
cd /path/to/project
bash /path/to/ai-dev-architecture-template/scripts/update-installed-architecture.sh --source /path/to/ai-dev-architecture-template --dry-run
```

Apply and commit:

```bash
bash /path/to/ai-dev-architecture-template/scripts/update-installed-architecture.sh --source /path/to/ai-dev-architecture-template --apply --commit
```

## Updating several projects

Create a list of projects:

```bash
cat > ~/ai-projects.txt <<'EOF'
/Users/zykovsrg/projects/project-a
/Users/zykovsrg/projects/project-b
/Users/zykovsrg/projects/project-c
EOF
```

First check the dry run for each project:

```bash
while read project; do
  echo "=== $project ==="
  cd "$project" && curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --dry-run
done < ~/ai-projects.txt
```

If everything is fine, apply:

```bash
while read project; do
  echo "=== $project ==="
  cd "$project" && curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --apply --commit
done < ~/ai-projects.txt
```

## After the update

After the update, open the project in Codex or Claude Code and ask the agent:

```text
Run environment-check.
```

The final menu after `environment-check` is informational. It does not mean the agent should automatically run `task-switch`, `task-finish`, `architecture-update`, or other workflows.

Before the next working task, the agent must use `task-intake`.

## Warning: --apply overwrites protected files wholesale

`--apply` copies fresh versions of the protected files (`AGENTS.md`, `CLAUDE.md`, skills) over the current ones. If you manually customized these files for your project and committed the changes, your edits will be wiped. The clean-tree check only catches uncommitted changes, not committed ones.

So always run `--dry-run` first and read the diff. The project's controlled memory (`ai/current-task.md`, `ai/decisions.md`, etc.) is not touched.

## When not to use the updater

Do not use the updater instead of a full review if:

- the project has heavily customized its own `AGENTS.md` or `CLAUDE.md`;
- there are local changes to base skills in `ai/skills/`;
- you are not sure which project rules were changed manually;
- the project is in the middle of a risky refactor.

In those cases, run `--dry-run` first, then ask the agent to do an `architecture-update` review of the diff.
