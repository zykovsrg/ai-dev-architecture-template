---
name: project-migrate
description: Use when existing project folders must be moved from a user-named legacy directory into the portable hub projects root.
---

# Project Migrate

Use this workflow only for a user-requested relocation of existing projects
into `<canonical-hub>/projects`. Stay in `Mode: routing` until the relevant
confirmation gate is complete. Migration approval never authorizes project
registration or project-content reads. Every approval below is an explicit confirmation of its displayed scope only.

## Temporary source gate

1. Validate that `ai/allowed-roots.md` contains exactly the canonical
   `<canonical-hub>/projects` root.
2. Ask the user to name and separately confirm a temporary migration source
   and its canonical path. It must be an existing directory whose direct
   children may contain legacy projects.
3. Reject `/`, the canonical home directory, the hub directory, and
   `<canonical-hub>/projects`. Reject a source or path component that is a
   symlink. Do not create the source or accept a remembered path.
4. The separately confirmed temporary migration source is read/move scope for
   this workflow only: never write it to `ai/allowed-roots.md`, the registry,
   cards, or durable memory. It expires when this workflow ends.

## Name-only inventory

After source confirmation, inventory direct-child directory names only and
exclude the target `_ai-hub` when it is a child of the source. Classify names
as possible project, likely backup/archive, or unknown. Never move backups,
archives, symlinks, unknown folders, or unsafe candidates. Do not recurse or
read candidate content, `.git`, project memory, source code, configuration, or
secrets during inventory.

Show candidate names and ask the user to supply or confirm each destination
project ID, then require a separate per-candidate or explicitly listed batch
preflight confirmation. The source name may differ from the ID. Each ID must
be safe lowercase kebab-case with no separator, `.`, `..`, whitespace, control
character, glob, or shell expansion.

## Confirmed preflight and move preview

For only the preflight-confirmed candidates:

1. Revalidate the temporary source, canonical projects root, direct-child
   source and destination paths, candidate type, and absence of symlinks.
2. Read only narrow Git metadata needed to report whether each candidate is a
   repository and whether its status is clean, dirty, unreadable, or otherwise
   concerning. Treat symlinked Git metadata or an external worktree pointer as
   an integrity concern. Do not read application or memory content.
3. Reject an existing destination of any kind. Treat unreadable Git metadata,
   an unsafe name, path change, symlink, or collision as a blocker.
4. Display every source-to-destination mapping, Git metadata, collision state,
   and the exact candidates included in any batch. State that the whole folder
   will move and preserve the existing `.git/` directory unchanged.
5. Require explicit move confirmation for each mapping or for the exact
   displayed batch. Preflight confirmation is not move confirmation.

## Approved move and verification

Immediately before each approved move, repeat the path, symlink, candidate,
Git-integrity, and collision checks. Move, never copy, the whole confirmed
folder to the displayed direct-child destination. Do not create backups,
archives, staging copies, replacement Git repositories, or destination merges.
Preserve the existing `.git/` directory and its contents unchanged.

After each move, verify that the source is absent, the destination is present,
and the recorded Git metadata still identifies the same repository when Git
was present. Stop on the first failure, collision, or integrity concern; do not
continue automatically with the remaining batch and do not attempt an
unapproved rollback.

## Separate registration gate

A successful move changes no hub metadata by itself. Show the moved project at
its canonical destination and ask separately whether to prepare registration.
Use `project-register` for its narrow confirmed context read and draft. Write a
card and registry entry only after separate card and registry confirmation,
then run `scripts/check-hub-registry.sh`. On validator failure, stop and report
the unchanged project location; do not register another project automatically.

## Optional legacy standalone cleanup

Offer this final phase only when the current `project-migrate` run moved the
project successfully, the project is a direct child of `<canonical-hub>/projects`,
its separate `project-register` confirmation completed, and
`scripts/check-hub-registry.sh` passed. The project remains usable through the
hub when this phase is skipped.

Cleanup confirmation is separate from move, preflight, and registration confirmation.
A previous move, preflight, or registration confirmation never authorizes cleanup.

Inventory only the existence and type of these exact candidate paths in the
confirmed project. Never inspect their contents. Reject a candidate or any of
its path components if it is a symlink.

Candidate allowlist:

- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`

Preserve `ai/skills/`, `.claude/`, and `.codex/` unchanged. They may contain
user-created skills, permissions, hooks, or tool configuration and are never
cleanup candidates.

Preserve these project-memory paths unchanged:

- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`

Do not delete `ai/` as a directory. Do not delete `ai/skills/`, `.claude/`,
or `.codex/`. Do not delete project source, `.git`, dependencies, unrelated
configuration, or any preserved memory path.

Show only the existing candidates in this preview. Recommend deletion because
retaining two rule systems can make their instructions diverge.

```text
Режим: routing
Проект: <canonical-hub>/projects/<project-id>

Старые standalone-правила, предложенные к удалению:
- <exact existing candidate path>

Будут сохранены без изменений: ai/current-task.md, ai/paused-tasks.md,
ai/future-tasks.md, ai/project-context.md, ai/decisions.md, ai/changelog.md.
_ai-hub уже является источником актуальных правил и skills для этого проекта.

Рекомендация: удалить перечисленные старые правила, чтобы они не расходились с
правилами хаба. Архив и резервная копия не создаются.

Подтвердите удаление только перечисленных путей для <project-id>.
```

The cleanup confirmation must name the displayed project ID and the exact
displayed candidate path list. If no candidates exist, report that no cleanup
is needed. If the user declines or does not give that exact confirmation, leave
every path unchanged.

Immediately before removal, revalidate the canonical direct-child project location, the current registry validation result, the unchanged allowlisted candidate list, and the absence of symlinks. Stop without deletion on any mismatch. Remove only confirmed existing candidates from the four-file allowlist. Do not archive, back up, copy, replace, or follow symlinks. Report every removed path, every preserved memory path, and that `ai/skills/`, `.claude/`, and `.codex/` were intentionally retained.

## Russian preview template

```text
Режим: routing
Временный источник: <canonical-source>

Предлагаемое перемещение:
- <source>/<source-name> → <canonical-hub>/projects/<project-id>
  Git: <нет|чисто|есть изменения|ошибка проверки>
  Коллизия: <нет|описание блокера>

Будет перемещена вся папка с существующей историей Git. Копия и резервная
копия не создаются. Регистрация потребует отдельного подтверждения.

Подтвердите перемещение указанного проекта или точно перечисленной группы.
```
