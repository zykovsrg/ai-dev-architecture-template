# Legacy Project Obsidian Bridge

## Purpose

Projects installed with AI Development Architecture 7.3 are standalone. When
opened directly inside the personal hub, their local instructions do not know
about the hub's central Obsidian vault. As a result, a request to import a
manual board change asks the user for a vault path instead of checking the
project board.

This change makes direct opening of a registered legacy project inside the hub
behave like hub-routed work for the narrow Obsidian reverse-sync workflow.

## Decision

Add a small, conditional hub bridge to every registered project still on
architecture version 7.3.

- The bridge activates only when the project's parent layout resolves to a hub
  root containing a valid registry entry for that project.
- It derives the vault as
  `<hub>/projects/ai-dev-architecture/obsidian-vault` and selects only
  `Obsidian/Projects/<project-id>/Kanban.md`.
- It invokes the existing central `obsidian-task-sync` implementation with the
  mandatory `--project-id` selector.
- The scan remains review-only; it shows a proposal and does not write project
  memory until the user confirms the proposal hash.
- Outside a valid hub layout, the project remains standalone and may request a
  source path as before.

The bridge is a short trigger and path-discovery rule, not a copied sync skill
or copied vault configuration. The central architecture project remains the
only owner of sync code and detailed workflow rules.

## Scope

Apply the bridge to the 33 registered projects whose local architecture file
declares version 7.3. Do not alter the central architecture project (7.4),
project tasks, boards, or canonical task records as part of this migration.

The change updates each legacy project's matching `AGENTS.md` and `CLAUDE.md`,
and any shared template or migration helper needed to make the rollout
repeatable. Each project receives its own small Git commit, preserving clear
history and rollback.

## Data flow

1. User opens a legacy project inside `_ai-hub` and asks to import changes from
   Obsidian.
2. The entry rule verifies the enclosing hub and project registry mapping.
3. The agent runs a scoped scan against that project's central Kanban board.
4. The agent presents the proposed canonical-record changes and proposal hash.
5. Only an explicit confirmation runs the scoped apply command.

If the layout or registry check fails, the agent must state that it is in
standalone mode and must not guess a vault path.

## Validation

- An automated contract test enumerates all 7.3 registered projects and checks
  that both entry files contain the same bridge rule.
- The test confirms the central project is excluded.
- A focused test verifies that the generated command includes exactly one
  project ID and the central vault derived from the hub root.
- Existing Obsidian sync, watcher, hub-registry, consistency, and smoke tests
  must remain passing.

## Risks and limits

Directly opened legacy projects can now discover the central vault only when
they are inside the validated hub layout. This deliberately does not make a
standalone clone depend on the hub, and it never accepts an arbitrary vault
path. The bridge cannot apply a change automatically: the existing proposal and
confirmation gates remain required.
