# Architecture Onboarding and Task Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the architecture easier to start, make new tasks reliably enter `ai/current-task.md`, remove `bugfix-workflow`, route bugs and complex work through Superpowers, and harden install/update scripts.

**Architecture:** Add a dedicated `task-intake` workflow before task work. Keep `task-switch` for switching away from unfinished work. Treat Superpowers as the required path for bugs and complex tasks when available, with a clear fallback when it is missing. Add a human-facing start screen and local-only usage path.

**Tech Stack:** Markdown instructions, Bash scripts, Git.

---

### Task 1: Replace Bugfix Workflow With Task Intake

**Files:**
- Delete: `template/ai/skills/bugfix-workflow/SKILL.md`
- Create: `template/ai/skills/task-intake/SKILL.md`
- Modify: `template/AGENTS.md`
- Modify: `template/CLAUDE.md`
- Modify: `template/ai/architecture.md`
- Modify: `template/ai/skills/environment-check/SKILL.md`
- Modify: `template/ai/skills/task-switch/SKILL.md`
- Modify: `template/ai/external-tools.md`

- [x] Remove `bugfix-workflow` from the base skills list.
- [x] Add `task-intake` as the first workflow for new user tasks.
- [x] Route bugs and complex tasks to Superpowers instead of a local bugfix skill.
- [x] Update task-switch so it receives new-task handoff from task-intake.

### Task 2: Add Human Start Screen and Local-Only Path

**Files:**
- Create: `docs/start-here.md`
- Create: `docs/no-github.md`
- Modify: `README.md`
- Modify: `docs/concepts.md`
- Modify: `docs/install.md`
- Modify: `docs/start-prompts.md`
- Modify: `docs/prompts.md`
- Modify: `docs/update.md`
- Modify: `docs/update-installed-projects.md`
- Modify: `docs/file-roles.md`

- [x] Add a first-screen guide with clear paths for new projects, old architecture versions, plugin setup, first task, and task close.
- [x] Explain that bugs and complex tasks should use Superpowers.
- [x] Explain how to use the architecture without GitHub.
- [x] Replace `bugfix-workflow` references with `task-intake` or Superpowers guidance.

### Task 3: Make Task Finish Save Work

**Files:**
- Modify: `template/ai/skills/task-finish/SKILL.md`
- Modify: `template/ai/architecture.md`
- Modify: `template/AGENTS.md`
- Modify: `template/CLAUDE.md`

- [x] Add default close behavior: task-finish ends by saving work.
- [x] In GitHub mode, saving means commit and push.
- [x] In local-only mode, saving means local commit or a fallback archive/patch.

### Task 4: Harden Scripts

**Files:**
- Modify: `scripts/install.sh`
- Modify: `scripts/update-installed-architecture.sh`
- Create: `scripts/smoke-test.sh`

- [x] Make `install.sh` find `template/` next to the script before falling back to `~/Documents`.
- [x] Make updater require `AGENTS.md`, `ai/architecture.md`, and `ai/current-task.md`.
- [x] Add smoke tests for install, updater memory preservation, version check, and updater guard.

### Task 5: Verify

**Files:**
- Modify: `CHANGELOG.md`

- [x] Bump architecture version.
- [x] Run Bash syntax checks.
- [x] Run canonical-list consistency check.
- [x] Run smoke tests.
