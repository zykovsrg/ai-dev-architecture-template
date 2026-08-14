# Portable Hub Projects Layout — Design

## Goal

Make one `_ai-hub` directory self-contained and portable by storing every
hub-managed project beneath its `projects/` directory while preserving every
project as an independent Git repository.

## Canonical Layout

```text
<parent>/_ai-hub/
├── .git/                  # hub repository only
├── projects/              # ignored by the hub repository
│   └── <project-id>/      # independent project, optionally with its own .git/
├── ai/
├── AGENTS.md
└── CLAUDE.md
```

The sole allowed root is `<hub>/projects/`. No external allowed roots or
externally located registered projects are supported in this mode.

## Installation

Hub installation creates `<hub>/projects/` automatically. The user supplies
only the hub directory, whose basename must remain `_ai-hub`; the installer
derives the sole allowed root as `<hub>/projects/` and records it in
`ai/allowed-roots.md`.

The hub directory must still be new or already a valid installed hub. The
installer must never overwrite a non-hub nonempty directory. It must create a
hub `.gitignore` rule for `/projects/` before initializing or using the hub Git
repository so nested project repositories and their files are never staged by
the hub.

## Project Creation And Registration

`hub-project-create` creates each new project only as a direct child of
`<hub>/projects/`. It creates the existing agreed minimal memory, card,
registry entry, and active-project selection after confirmation; it does not
create Git, code, dependencies, or duplicated entry files.

`hub-project-register` inventories and registers only direct children of this one
projects directory. A project outside it is not eligible for registration.

## Existing Projects Migration

Migration is a separate, confirmation-gated workflow. It is not part of hub
installation or project creation.

1. Require a separately confirmed temporary migration source: any existing
   directory that contains legacy projects as direct children. It is not an
   allowed root, is never written to `ai/allowed-roots.md`, and expires when
   the migration workflow ends.
2. Run a read-only inventory of direct-child folder names in that source only;
   exclude the target `_ai-hub` directory when it is a child of the source.
   Do not recurse or read project content before individual move approval.
3. Show a proposed mapping from each confirmed existing path to one new
   `<hub>/projects/<project-id>` path, including Git-repository status and
   collision risks.
4. Require explicit approval for each move or an explicitly displayed batch.
5. Move, do not copy, each approved project; preserve its `.git/` directory
   and contents.
6. Register only after the move completes and validate the registry.

The workflow must not move archives, backups, symlinks, unknown folders, or
nonempty destination paths. It must stop on a failed move, collision, or Git
integrity concern, without continuing with other projects automatically.

## Security And Portability

- Hub routing, confirmation, secrets, and memory-isolation rules remain higher
  priority than convenience.
- The hub Git repository ignores `/projects/`; each project retains its own
  Git history and remote configuration.
- Moving the parent `_ai-hub` directory moves the hub and all registered
  projects together. Absolute paths in the registry must therefore be
  rewritten only by the explicitly confirmed migration or relocation workflow;
  the hub must not silently guess paths after a move.
- Existing external roots and legacy registration remain unsupported rather
  than adding a compatibility layer that would weaken the one-folder model.
- The temporary migration source works for any user path. It is a one-time
  user-confirmed read/move scope, never a configured permanent root.

## Verification

- A new hub install creates `_ai-hub/projects/`, writes it as the only allowed
  root, and ignores `/projects/` in hub Git.
- The installer rejects custom external `--root` values in portable mode.
- `hub-project-create` and `hub-project-register` route only to the derived projects
  directory.
- A hub-installed updater preserves `projects/`, registry data, and cards.
- Migration is preview-first and never runs from installation or registration.
- `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, and
  `git diff --check` pass.
