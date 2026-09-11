# Standalone consumer inventory — 2026-09-11

Scope: active repository files only. Historical `docs/superpowers/**`, `docs/audits/**`, and `CHANGELOG.md` are evidence and are excluded from active-product cleanup.

## Active runtime consumers found before retirement

- `scripts/install.sh` defaulted to the old project-local distribution and copied `template/`.
- `scripts/update-installed-architecture.sh` could restore/copy the old project-local shared rules.
- `README.md`, `docs/install.md`, `docs/start-prompts.md`, `docs/update-installed-projects.md`, and `docs/update.md` described the old install/update path.
- `scripts/check-consistency.sh`, `scripts/hub-smoke-test.sh`, and legacy architecture tests contain assertions for the old dual-distribution model and must be reconciled to Hub-only invariants.

## Root rule/skill classification

The repository root is itself a registered architecture-development project. Its canonical project memory and knowledge are preserved.

- `ai/skills/knowledge-capture` and `ai/skills/knowledge-review`: exact generic copies of the old distributable tree; remove.
- `ai/skills/environment-check`, `ai/skills/start-screen`, `ai/skills/task-finish`: drifted versions of generic project architecture behavior, not documented project-specific extensions; remove rather than preserve a second shared workflow layer.
- `ai/architecture.md` and `ai/external-tools.md`: generic shared architecture copies; remove.
- root `AGENTS.md` and `CLAUDE.md`: replace with minimal Hub-managed project pointers required for direct-open safety.

Preserve: `ai/current-task.md`, `ai/future-tasks.md`, `ai/paused-tasks.md`, `ai/project-context.md`, `ai/decisions.md`, `ai/changelog.md`, project `knowledge/`, `.claude/`, `.agents/`, `.codex/`, and unrelated configuration/application files.
