# Legacy Standalone Cleanup — Design

## Goal

After a project has been moved into `<hub>/projects` and registered, offer a
separate, confirmation-only cleanup of its obsolete standalone architecture
files. This prevents old local rules from competing with the hub's current
rules when an agent is opened directly in the project folder.

## Scope

The cleanup is an optional final phase of `project-migrate`, not part of the
move approval or registration approval. A successful migration remains valid
if the user declines cleanup or stops before it.

The workflow may run only for a project that:

1. was moved successfully by the current `project-migrate` run;
2. is a direct child of `<canonical-hub>/projects`;
3. has passed registration and `scripts/check-hub-registry.sh`.

## Candidate Files

The workflow may inspect and propose deletion only for these exact legacy
standalone architecture files inside that confirmed project:

- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`

It must preserve `ai/skills/`, `.claude/`, and `.codex/` unchanged. They can
contain user-created skills, permissions, hooks, or tool configuration and are
not part of the standalone template's removable entry/rule set. It must never
propose deletion of project source files, content, Git metadata, dependencies,
configuration unrelated to the architecture, or the project-memory files
listed below.

## Protected Project Memory

Cleanup must preserve these paths unchanged:

- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`

No cleanup action may delete `ai/` as a directory. It may delete only the four
named legacy files above, after their exact paths have been shown and
confirmed.

## Confirmation Flow

1. After successful registration and validation, state that the hub is now the
   authoritative source of rules and skills for the project.
2. Inventory only the candidate paths that exist in the confirmed project. Do
   not inspect their contents and do not follow symlinks.
3. Show an exact deletion preview and the preserved-memory list. Recommend
   deletion as the default because retaining both rule systems creates a risk
   of divergence.
4. Require a separate explicit confirmation that names the displayed project
   and the displayed candidate path list. A previous move, preflight, or
   registration confirmation never authorizes cleanup.
5. Immediately before deletion, revalidate the project path, direct-child
   relationship, registry validation, candidate paths, and absence of
   symlinks. If any item differs, stop without deleting anything.
6. Delete only the confirmed existing candidates. Do not archive, back up,
   copy, replace, recursively clean unrelated paths, or create new Git
   history. Report each removed path, the preserved memory files, and that
   `ai/skills/`, `.claude/`, and `.codex/` were intentionally retained.

If no candidate exists, report that no cleanup is needed. If the user declines
or does not explicitly confirm, leave every file unchanged.

## Hub Entry Behavior

The hub entry files and architecture overview must make the order explicit:

`project-migrate` move → separate `project-register` confirmation → validator
→ optional separate legacy cleanup confirmation.

The project remains usable through the hub before cleanup. Cleanup only
removes the ambiguity of opening an agent directly in the migrated folder.

## Verification

Smoke tests must assert that the workflow:

- is present in the installed hub and referenced consistently;
- does not make cleanup part of move or registration approval;
- names only the allowed candidate paths;
- rejects an added candidate path, broad directory deletion, or wording that
  permits cleanup without the separate exact confirmation;
- preserves every memory path;
- preserves `ai/skills/`, `.claude/`, and `.codex/`;
- requires an exact, separate confirmation;
- requires repeated project-path, registry, candidate-list, and symlink
  validation before deletion;
- does not propose archive or backup creation.
