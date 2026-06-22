# Changelog

## v6.9 — 2026-06-21

- Added `task-intake` as the first workflow for real user tasks: empty `ai/current-task.md` is now populated before work starts, and unfinished-task conflicts route through `task-switch`.
- Removed the local `bugfix-workflow` base skill. Bugs, regressions, crashes, flaky behavior, debug requests, performance investigations, and complex tasks now route to Superpowers when available, with an explicit install/configure vs manual fallback decision when missing.
- Added a human-facing start screen in `docs/start-here.md` and a local-only usage guide in `docs/no-github.md`.
- Updated `task-finish` so closing a task includes saving the result: GitHub push when configured, local commit or patch/archive fallback when GitHub is unavailable.
- Hardened `scripts/update-installed-architecture.sh` so it requires `AGENTS.md`, `ai/architecture.md`, and `ai/current-task.md` before updating.
- Made `scripts/install.sh` portable by resolving `template/` next to the script before falling back to `~/Documents`.
- Removed `claude-seo` from the base external tools list and added `scripts/smoke-test.sh` for install/update safety checks.
- Compacted `AGENTS.md` and `CLAUDE.md` back into short entry files after adding the v6.9 task-intake and Superpowers routing rules.

## v6.8 — 2026-06-16

- Added a `--check` mode to `scripts/update-installed-architecture.sh`: it compares the architecture version installed in a project (`ai/architecture.md` `Version:`) with the source and, if the project is behind, prints both versions and shows a dry-run preview without changing anything (exit 0 = up to date, 1 = update available). Numeric major.minor comparison (6.10 > 6.9). Documented in `README.md`, `docs/update.md`, `docs/update-installed-projects.md`. Bumped `ai/architecture.md` to `6.8`.

## v6.7 — 2026-06-16

- Fixed a v6.6 bug: `architecture-update` and `release-check` told the agent to run `scripts/check-consistency.sh`, which only exists in the architecture template repository and is absent in installed projects. Both skills now guard the call with an existence check and skip it in projects. Documented the scope in `ai/architecture.md` and signposted the canonical lists from the updater docs. Bumped `ai/architecture.md` to `6.7`.

## v6.6 — 2026-06-16

- Single source of truth for the protected-files and controlled-memory lists: holders now wrap each list in `<!-- canon:... -->` markers, and `scripts/check-consistency.sh` verifies all copies match.
- Removed the duplicated lists from human docs (`README.md`, `docs/*`); they now link to `docs/file-roles.md`.
- Deduplicated the skill-precedence list to 4 canonical files; the rest link to `ai/architecture.md`.
- Wired the consistency check into `architecture-update` and `release-check`.
- Documented the system in `ai/architecture.md` and bumped it to `6.6`.

## v6.5 — 2026-06-16

- Strengthened the language rule: the agent must explain to the user as if they are new to IT — define every technical term on first use, explain the reasoning behind actions in simple steps, and use short analogies. Added a dedicated "Talking to the user (beginner-friendly)" section to `ai/architecture.md` and the short version to `AGENTS.md` / `CLAUDE.md`. Bumped `ai/architecture.md` to `6.5`.

## v6.4 — 2026-06-16

- Bumped `ai/architecture.md` to version `6.3` and synced its `environment-check` section with the v6.3 task-snapshot rule (header was stale at `6.1`).
- Unified the skill-precedence list across `README.md` and `docs/concepts.md` to the canonical 5-level form; removed the extra `optional alternatives` level.
- Added `ai/future-tasks.md` to the controlled memory list in `release-check`.
- Added `Source` URLs for `agent-skills-for-context-engineering` and `claude-seo` in `ai/external-tools.md`.
- Marked `.claude/` and `.codex/` as project-created folders absent from the template, with a short explanation in `docs/file-roles.md`.
- Added a warning in `docs/update-installed-projects.md` that `--apply` overwrites protected files wholesale.
- Differentiated `AGENTS.md` (Codex) and `CLAUDE.md` (Claude Code): tool-named titles, cross-reference, and tool-specific skill-activation note.
- Added `ai/external-tools.md` to the `environment-check` required entry files.
- Clarified the transient `paused` status in `ai/current-task.md`.
- Removed `MANIFEST.json` (unused, drifted from the file set).
- Removed a stale template-sync question in `docs/prompts.md`; translated an English row in the `docs/file-roles.md` matrix; noted that `scripts/install.sh` mirrors the rsync install in `README.md`.

## v6.3 — 2026-06-14

- Updated `environment-check` to include a short snapshot of the current task and future tasks before the final commands/skills menu.
- Clarified that the task snapshot is informational only and must not modify task memory or activate any workflow automatically.
- Synced `AGENTS.md` and `CLAUDE.md` with the new post-check task snapshot rule.

## v6.2 — 2026-06-14

- Added `scripts/update-installed-architecture.sh` for safe automated updates in projects where the architecture is already installed.
- Added `docs/update-installed-projects.md` with dry-run, apply, commit, local-source, and multi-project update workflows.
- Clarified that updater overwrites protected architecture files and base skills, but never overwrites controlled memory files.
- Updated `README.md` and `docs/update.md` to prefer the updater workflow for existing projects.
- Updated `MANIFEST.json` to include previously missing files and the new updater files.

## v6.1 — 2026-06-14

- Updated `environment-check` to end with an informational menu of available next commands and skills.
- Clarified that the menu must not activate any listed workflow automatically.
- Synced `README.md` and docs with the new post-check output rule.
- Fixed stale documentation that still allowed TEMP diagnostics cleanup work to be stored in `ai/paused-tasks.md`; paused tasks remain owned by `task-switch`.
- Removed the remaining `task-finish` cleanup wording that allowed TEMP diagnostics removal notes in `ai/paused-tasks.md`.
- Restricted `ai/changelog.md` updates in `docs/file-roles.md` to confirmed `task-finish` or approved `architecture-update` workflows.
- Updated `scripts/install.sh` next steps to run `environment-check` and treat its final menu as informational.

## v6.0 — 2026-06-14

- Added `ai/future-tasks.md` as a controlled memory file for out-of-scope ideas and future implementation tasks.
- Clarified that `ai/paused-tasks.md` is only for interrupted active work and must not be used as a backlog.
- Added future task capture and promotion rules to `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, `task-switch`, `task-finish`, and `bugfix-workflow`.
- Updated `environment-check` so `ai/future-tasks.md` is a required entry file.
- Updated README and docs to include the new file role and safe update instructions.

## v5.9 — 2026-06-14

- Fixed `bugfix-workflow` wording so mitigations are recorded in `ai/changelog.md` only during confirmed `task-finish` cleanup.
- Clarified that retained temporary diagnostics must be reported in the verification handoff and, when needed, tracked in `ai/current-task.md` rather than written directly to cleanup history.
- Clarified that `ai/paused-tasks.md` must not be updated by `bugfix-workflow`; it remains owned by `task-switch`.
- Synced README skill routing with the current bugfix triggers: flaky behavior and debug requests.

## v5.8 — 2026-06-14

- Documented the adapted diagnose-style loop inside `bugfix-workflow`.
- Clarified that there is no separate `Mode: bugfix`; bug work uses `Mode: implementation` plus `Skill: bugfix-workflow`.
- Added explicit architecture guidance for feedback loops, reproduction, minimization, hypotheses, targeted instrumentation, regression tests, and verification handoff.
- Clarified that `bugfix-workflow` must use `ai/current-task.md`, `ai/decisions.md`, and `task-finish`, not create `CONTEXT.md`, `docs/adr/`, or a parallel documentation system.
- Updated `template/ai/architecture.md` to version `5.8`.

## v5.4 — 2026-05-17

- Updated `environment-check` to check optional project skills for presence.
- Added `frontend-design` to the optional project skills check.
- Missing optional project skills are reported as `not installed, not a blocker` and must not fail `environment-check`.
- Optional project skills must not be restored, installed, or created unless the user explicitly asks.
- Added source URLs for `frontend-design` and `code-review-graph` to `ai/external-tools.md` so agents know where to get them.

## v5.3 — 2026-05-17

- Added `frontend-design` as an optional project skill.
- Added optional routing for `ai/skills/frontend-design/SKILL.md` in `AGENTS.md` and `CLAUDE.md`.
- Clarified that optional project skills are not required base skills and must not make `environment-check` fail when absent.
- Updated skill precedence wording to include optional project skills below base skills.

## v5.2 — 2026-05-17

- Added plan-driven workflow rules for Superpowers and subagent-driven development.
- `docs/superpowers/plans/<plan>.md` is now the source of truth for plan progress.
- Agents must update plan checkboxes after each completed plan task.
- Local judgment calls should be recorded as short `Note:` entries under the relevant plan task.
- Added a verifiable commit convention for plan-driven work: `Plan Task <N>: <short action>` and `Plan Cleanup: <short action>`.
- Added a decision entry documenting why plan files, plan notes, and commit conventions are used for handoff.
- Updated `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, and `ai/decisions.md`.

## v5.1 — 2026-05-17

- Strengthened the task completion handoff rule.
- If implementation or review suggests the current task may be complete, agents must not declare the task closed.
- Agents must propose `task-finish` and wait for user confirmation before checking closure or cleaning `ai/current-task.md`.
- Updated `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, and `task-finish` skill.

## v5.0 — 2026-05-16

- Compacted `AGENTS.md` and `CLAUDE.md` after review and approval.
- Added explicit rule that `ai/architecture.md` and skills are not loaded by default.
- Added explicit skill trigger routing to `AGENTS.md` and `CLAUDE.md` so skills still activate predictably.
