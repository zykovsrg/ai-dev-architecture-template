# Unified Assistant Foundation — implementation plan

> **For Codex:** use `superpowers:executing-plans` or
> `superpowers:subagent-driven-development` to execute this plan task by task.

## Purpose

Implement only the safe foundation for the approved unified assistant:

- canonical fields for archiprojects and tasks;
- a validated hub registry of archiproject links;
- a read-only compact project index for routing;
- updater preservation for the new hub-owned registry.

This plan does **not** implement Obsidian projection, Apple Calendar MCP,
vault migration, meeting capture, recurring reviews, or session audit.

## Global constraints

- Project/task files remain the only source of truth. No new task database.
- Agent writes nothing on the user's behalf without immediate confirmation.
- Compact index reads only card metadata, never project `ai/`, `knowledge/`,
  code, or a card's `Memory entry point`.
- Existing project cards without archiproject fields stay valid.
- Tests come first for every executable change.
- Use inexpensive workers for mechanical inspection/tests and a stronger worker
  for rule/permission review.
- Preserve unrelated user changes, especially `ai/future-tasks.md`.

## Files

Protected changes, requiring the architecture-update exact-diff confirmation:

- `hub-template/AGENTS.md`, `hub-template/CLAUDE.md`,
  `hub-template/ai/architecture.md`;
- `hub-template/ai/skills/hub-registry-check/SKILL.md` and
  `hub-template/ai/skills/hub-project-router/SKILL.md`.

Controlled changes:

- `hub-template/ai/archiprojects.md` (new canonical hub registry).

Regular code/docs:

- `scripts/check-hub-registry.sh`, `scripts/hub-smoke-test.sh`,
  `scripts/check-consistency.sh`, `scripts/install-hub.sh`,
  `scripts/update-installed-hub.sh`,
  `scripts/read-compact-project-index.sh` (new), `docs/file-roles.md`.

## Task 1 — define the canonical hub work-model files and rules

1. Add `hub-template/ai/archiprojects.md` with a short schema: `id`, `name`,
   `status`, `target`, `unit`, `due`. A concrete entry has one fenced YAML block
   under a human heading. `due` is `YYYY-MM-DD` or `none`.
2. Add the hub routing contract: project/task files remain canonical, project
   cards are metadata only, and a link never grants a project read. Waiting is
   task/subtask-only and does not place a project in Waiting when other work is
   actionable.
3. Amend hub project-card guidance with optional all-or-nothing fields:
   `Primary archiproject`, `Archiproject contribution`, `Related archiprojects`.
   Use `none` where absent. Related links never add contribution.
4. Make the same rule meaning available in hub entry documents,
   `hub-template/ai/architecture.md`, hub router/registry skills and
   `docs/file-roles.md`. The ordinary project template stays unchanged.

Tests first:

- extend the smoke-test fixtures to contain a valid registry, a project with a
  primary contribution, a project with only `none`, and a legacy project card;
- test template/canonical-list consistency using the existing consistency
  checker.

Expected result: an installed hub has one small canonical archiproject registry,
not a parallel task store.

## Task 2 — validate archiproject card metadata

1. Before modifying the validator, add failing smoke-test cases for:
   partially supplied new card fields; unknown primary ID; non-positive or
   non-numeric contribution; duplicate related IDs; related ID equal to primary;
   malformed registry entry; and a legacy card with no new fields.
2. In `scripts/check-hub-registry.sh`, parse only the hub registry and project
   cards. Preserve all existing mandatory-field validation.
3. New fields are backward compatible: if all three are absent, accept the
   card. If one occurs, require all three and validate their values against
   `ai/archiprojects.md`.
4. Add an entry-point validation that a card's primary archiproject may only be
   one known registry ID and its contribution is greater than zero. `none` means
   no contribution; related IDs are a de-duplicated list and may not equal the
   primary ID.
5. Run `bash scripts/hub-smoke-test.sh` and
   `bash scripts/check-hub-registry.sh` on the real hub.

Expected result: old cards work; new links are safe and unambiguous.

## Task 3 — add the compact, read-only project index

1. Add failing smoke assertions for a TSV output with exactly:
   `project_id`, `name`, `tags`, `status`, `purpose_brief`.
2. Create `scripts/read-compact-project-index.sh`. It first calls the registry
   validator and then reads only registry/card fields. It prints deterministic
   TSV, sorted by project ID, and exits non-zero on invalid registry data.
3. Add negative smoke fixtures: a sentinel in a project's `ai/current-task.md`
   and a sentinel in a card's `Memory entry point` must never appear in output.
4. Document this as the only pre-confirmation project discovery interface. Full
   task/knowledge reads still need project or confirmed-set approval.
5. Run the smoke test and inspect a real-index sample for the exact five
   columns, no path or task leakage.

Expected result: routing stays fast and flexible without weakening the boundary.

## Task 4 — preserve the registry in installers and updaters

1. Add tests that a fresh hub installation creates `ai/archiprojects.md`.
2. Add tests that `update-installed-hub.sh` preserves an existing file
   containing `USER_ARCHIPROJECT_MUST_SURVIVE` byte-for-byte.
3. Modify only missing-file copy logic so the file is copied when absent and
   never overwritten when present.
4. Run install/updater tests in disposable temporary fixtures; never run an
   updater against the user's active hub as a test.

Expected result: installations receive the registry and updates cannot destroy
user data.

## Task 5 — review and handoff

1. Run `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`,
   real `check-hub-registry.sh`, and shell syntax checks for changed scripts.
2. Use a review worker to compare changed protected files with the approved
   architecture and report permission/source-of-truth regressions.
3. Present exact protected-file replacements before applying them, as required
   by `architecture-update`; wait for `Replace this?` confirmation.
4. Commit only files authored for this change. Do not stage unrelated work.
5. Report test evidence, deferred work, and the next implementation slice:
   Obsidian generated view, then Calendar adapter only after its separate
   install/connection approval.

## Rollback

All code/template changes are in Git. Revert the foundation commit to remove
the feature. Do not delete an existing `ai/archiprojects.md`; restore it from a
backup or Git history only after explicit user approval. No external system is
changed by this plan.
