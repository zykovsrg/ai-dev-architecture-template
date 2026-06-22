# AI Development Entry Point — Codex

This project uses a solo AI-development workflow. This file is the short entry
point for Codex; `CLAUDE.md` is the matching Claude Code entry file. Keep them
equal in meaning except for tool-specific notes.

Detailed rules live in `ai/architecture.md` and relevant `ai/skills/*/SKILL.md`.
Do not load them by default; open them only when the task needs those details.

## Core Rules

- Talk to the user in Russian, assuming they are new to IT. Explain technical terms simply.
- Keep persistent AI-facing instructions in English.
- Prefer minimal diffs, clean architecture, and confirmed scope.
- Capture useful out-of-scope ideas as future task candidates.
- Do not mix refactoring with bug work unless explicitly asked.
- Explain risks before changing storage, data model, dependencies, or architecture.
- Add tests for risky changes, or explain why manual checks are the practical path.
- Do not overwrite unfinished task memory.
- Do not change protected architecture files without `architecture-update` and explicit confirmation.
- In review mode, verify findings with files, diff, logs, or tests; otherwise label them as hypotheses.

## File Classes

Protected architecture files may change only through confirmed `architecture-update`:

<!-- canon:protected-files -->
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`
<!-- /canon:protected-files -->

Controlled memory files may change only through the matching workflow:

<!-- canon:controlled-memory -->
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
<!-- /canon:controlled-memory -->

Before finishing, check `git diff --name-only`. If protected files changed without approval, stop. If memory changed, name the workflow that allowed it.

## Session And Task Flow

- New session/tool/chat/restored context: run `environment-check`; show snapshot/menu only.
- Before real task work: run `task-intake`; it records an empty `current-task` or routes unfinished work to `task-switch`.
- Work modes: `review`, `implementation`, `task-finish`, `architecture-update`.
- If work appears complete, propose `task-finish`; do not declare it closed.
- `task-finish` must save the result: GitHub push when configured, local-only fallback when not.

## Context And Skill Routing

Default context: this file and `ai/current-task.md`.

Codex does not auto-activate project skills. When a trigger matches, open the
current `ai/skills/*/SKILL.md` before using that workflow.

Common triggers:

- environment check: `ai/skills/environment-check/SKILL.md`, `ai/external-tools.md`
- new task/change: `ai/skills/task-intake/SKILL.md`
- task switching: `ai/skills/task-switch/SKILL.md`, `ai/current-task.md`, `ai/paused-tasks.md`
- future ideas or promotion: `ai/future-tasks.md`
- task finish: `ai/skills/task-finish/SKILL.md`
- release or merge: `ai/skills/release-check/SKILL.md`
- tests: `ai/skills/write-tests/SKILL.md`
- UI behavior/layout/interaction: `ai/skills/ui-review/SKILL.md` and usually `write-tests`
- decorative UI only: `ui-review`; use `write-tests` only if behavior or accessibility may change
- bugs, regressions, crashes, performance, or complex work: Superpowers when available
- architecture change: `ai/skills/architecture-update/SKILL.md`

Extra context only when relevant: project behavior/storage/UI → `ai/project-context.md`; durable invariants → `ai/decisions.md`; workflow ambiguity → `ai/architecture.md`; plan-driven work → relevant `docs/superpowers/*`.

## Precedence

1. `AGENTS.md` / `CLAUDE.md`
2. `ai/current-task.md`
3. relevant base skill
4. optional project skills and expected external tools
5. controlled external methodologies

Superpowers is expected for bugs and complex tasks when available. If missing,
ask whether to install/configure it or continue with a manual fallback.

## Output

Before editing: state `Mode: ...`, say the next step, and mention real risks.

After editing: state the mode, summarize changes, list checks, name risks or
unfinished parts, say whether task memory changed, and propose `task-finish` if
the task appears complete.
