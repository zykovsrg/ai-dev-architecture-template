# Changelog

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
- If implementation or review suggests the current task may be complete, agents must not declare it closed.
- Agents must propose `task-finish` and wait for user confirmation before checking closure or cleaning `ai/current-task.md`.
- Updated `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, and `task-finish` skill.

## v5.0 — 2026-05-16

- Compacted `AGENTS.md` and `CLAUDE.md` after review and approval.
- Added explicit rule that `ai/architecture.md` and skills are not loaded by default.
- Added explicit skill trigger routing to `AGENTS.md` and `CLAUDE.md` so skills still activate predictably.
- Added `workflow ambiguity, architecture rules, or architecture update: ai/architecture.md` as an on-demand context rule.
- Updated `ai/architecture.md` with on-demand architecture and skill-trigger rules.

## v4.9 — 2026-05-16

- Strengthened the session start check rule.
- When entering an existing project, switching tools, or continuing in a new chat, agents must run `environment-check` before suggesting next steps or starting implementation.
- Agents may skip `environment-check` only if the user explicitly says not to run it.
- Updated `AGENTS.md`, `CLAUDE.md`, and `ai/architecture.md`.

## v4.8 — 2026-05-16

- Added a required mode line to the final report after edits.
- After editing, agents must start the report with the work mode used, for example `Mode: implementation`.
- Updated `AGENTS.md`, `CLAUDE.md`, and `ai/architecture.md`.

## v4.7 — 2026-05-16

- Added a scope control rule.
- Agents must not expand user-confirmed scope during implementation.
- If a larger scope looks useful, the agent must stop and ask before adding it.
- Added the rule to `AGENTS.md`, `CLAUDE.md`, and `ai/architecture.md`.

## v4.6 — 2026-05-16

- Added a required task memory reporting rule after edits.
- Agents must explicitly say whether task memory changed.
- If task memory changed, agents must list the exact files changed:
  - `ai/current-task.md`
  - `ai/changelog.md`
  - `ai/decisions.md`
  - `ai/project-context.md`
  - `ai/paused-tasks.md`
- Updated `AGENTS.md`, `CLAUDE.md`, and `ai/architecture.md`.

## v4.5 — 2026-05-16

- Added a Superpowers trigger proposal rule.
- Agents must not activate Superpowers automatically when a task looks complex.
- If a task matches Superpowers triggers, the agent must explain why Superpowers may help and ask: `Use Superpowers for this task?`
- Added explicit Superpowers triggers: large or vague tasks, architecture design, technical choices, data model changes, migrations, TDD, subagents, major refactoring, and unclear blast radius.
- Updated `AGENTS.md`, `CLAUDE.md`, and `ai/architecture.md`.

## v4.4 — 2026-05-16

- Clarified the difference between `review` and `implementation` modes.
- `review` now explicitly covers reading files, summarizing context, inspecting project state, running `environment-check`, and suggesting the next step without editing.
- `implementation` is now reserved for changes to application code, project files, tests, or task memory.
- Updated `AGENTS.md`, `CLAUDE.md`, and `ai/architecture.md`.

## v4.3 — 2026-05-16

- Simplified the pre-edit communication format for a non-developer user.
- Replaced mandatory `Files to change / Risks / Minimal plan` with a shorter rule:
  - state `Mode: ...`;
  - briefly explain what will be done next in simple words;
  - mention important risks only if they exist.

## v4.2 — 2026-05-15

- Added explicit work mode declaration rule.
- `AGENTS.md` and `CLAUDE.md` now require the agent to state `Mode: ...` before task work.
- Before editing, the agent must explicitly state the current work mode.
- `ai/architecture.md` documents the same rule.

## v4.1 — 2026-05-15

- Fixed documentation inconsistencies after v4.0.
- Updated `template/ai/architecture.md` version to `4.1`.
- Added `ai/paused-tasks.md` and `ai/external-tools.md` to the README repository tree.
- Added `task-switch` and `environment-check` to README main concepts.

## v4.0 — 2026-05-15

- Added `docs/start-prompts.md`.
- Added two ready-to-copy start prompts:
  - first architecture installation in a project;
  - continuation in a new chat or another agent.
- Added `scripts/install.sh` for copying the template into projects without overwriting existing files.
- Updated README structure and installation instructions.
