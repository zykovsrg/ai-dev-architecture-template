# External Tools and Skills

This file lists external skills and tools used by this development setup.

External tools are not copied from this template.

The agent must check expected external tools and controlled external methodologies during the first-session environment check and report what is missing.

The agent must not install or activate anything without explicit user confirmation.

## Optional project skills

Optional project skills are installed only in projects where they are useful.

Missing optional project skills are warnings, not blockers.

### frontend-design

Type: optional project skill

Source:
https://github.com/anthropics/skills/tree/main/skills/frontend-design

Purpose:
Frontend design, UI composition, visual hierarchy, component design, and UX improvements.

Expected: optional, only for projects with UI/frontend/design tasks.

How to check:
- project skill file: `ai/skills/frontend-design/SKILL.md`

Missing means:
Work can continue. UI/frontend design guidance is unavailable until the skill is installed in the project.

Install only after explicit user confirmation.

### impeccable

Type: optional project skill

Source:
https://github.com/pbakaus/impeccable/tree/main/.agents/skills/impeccable

Purpose:
Systematic UI design, critique, polish, accessibility, responsive behavior, and
design anti-pattern detection. The installed package includes the focused
`animate` workflow.

How to check:
- project skill file: `ai/skills/impeccable/SKILL.md`
- animate router: `ai/skills/animate/SKILL.md`

### theme-factory

Type: optional project skill

Source:
https://github.com/anthropics/skills/tree/main/skills/theme-factory

Purpose:
Apply a consistent palette and font system to slides, documents, reports, and
web artifacts, or create a new theme when the presets do not fit.

How to check:
- project skill file: `ai/skills/theme-factory/SKILL.md`

### design-motion-principles

Type: optional project skill

Source:
https://github.com/kylezantos/design-motion-principles/tree/main/skills/design-motion-principles

Purpose:
Create purposeful interface motion or audit existing animations through
context-aware motion-design principles, accessibility, and performance checks.

How to check:
- project skill file: `ai/skills/design-motion-principles/SKILL.md`

## Expected external skills and tools

These tools should be installed when available.

Missing expected external tools are warnings, not blockers.

### code-review-graph

Type: external code analysis tool

Source:
https://github.com/tirth8205/code-review-graph

Purpose:
Code dependency graph, affected-files analysis, blast-radius review, and token-efficient code review.

Expected: yes, if available.

Why this is primary:
It is focused on code review and impact analysis, so it fits this architecture.

How to check:
- command: `code-review-graph --version`
- project data folder, if already generated: `.code-review-graph/`
- MCP configuration, if configured by the user

Missing means:
Work can continue, but dependency graph review and blast-radius analysis may be weaker.

### agent-skills-for-context-engineering

Type: external skillset

Source:
https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering

Purpose:
Additional context-engineering skills and workflows.

Expected: yes, if available.

How to check:
- check the user's configured Claude Code, Codex, or local skills directories
- if unsure, report `not confirmed`

Missing means:
Work can continue, but extra context-engineering skills are unavailable.

### playwright-mcp

Type: external MCP browser automation tool

Source:
https://github.com/microsoft/playwright-mcp

Purpose:
Browser interaction, live UI verification, accessibility snapshots, and
screenshot feedback loops.

Expected: yes, if supported by the current agent harness.

How to check:
- inspect the current agent's available MCP/browser tools for Playwright;
- inspect configured MCP servers, for example with the harness MCP listing;
- do not run an installer merely to test availability;
- if the harness configuration cannot be inspected, report `not confirmed`.

Missing means:
Work can continue, but live browser verification may require a different
available browser tool or manual checks.

## Controlled external methodologies

These tools may be installed and checked, but they must not become the default workflow.

### Superpowers

Type: full external development methodology

Status:
Critical plugin: installation is strongly recommended for every project. Required for bugs and complex tasks when available.

Purpose:
Spec-first planning, TDD-first development, subagent-driven development, stronger verification, and branch-finishing workflows.

Use for:
- bugs, regressions, crashes, flaky behavior, debug requests, and performance investigations;
- large or vague tasks;
- architecture design;
- choosing between technical options;
- data model changes;
- migrations;
- TDD;
- subagents;
- major refactoring;
- unclear blast radius.

For bugs and complex tasks:
- use Superpowers when it is available;
- if it is missing or not confirmed, ask whether to install/configure it or continue with a manual fallback.

For other tasks, activate only when:
- the user explicitly asks to use Superpowers;
- the user explicitly confirms the agent's proposal to use Superpowers;
- `ai/current-task.md` says `Use Superpowers: yes`.

Do not use for:
- copy changes;
- simple UI tweaks;
- narrow tasks with known relevant files;
- `task-finish`;
- `architecture-update`, unless the user explicitly asks.

Must not override:
- work mode;
- `ai/current-task.md`;
- user confirmation rules;
- `task-finish` rules;
- `architecture-update` rules;
- clean architecture principle;
- project-specific rules in `ai/project-context.md`.

How to check:
- check the user's configured Claude Code, Codex, or local skills/plugin directories
- if unsure, report `not confirmed`

Missing means:
Simple work can continue. For bugs and complex tasks, stop, recommend installing Superpowers as the preferred option, and continue with a manual fallback only if the user declines.

## Reporting format

During environment check, return:

1. Required base skills:
   - present
   - missing

2. Optional project skills:
   - present
   - not installed, not a blocker

3. Expected external skills and tools:
   - present
   - missing
   - not confirmed

4. Controlled external methodologies:
   - present
   - missing
   - not confirmed
   - activation status: not active unless explicitly requested

5. Blockers:
   - only missing required base skills are blockers
   - missing optional project skills and external tools are warnings, not blockers for simple tasks
   - missing Superpowers is a warning for simple tasks, but requires an explicit user decision for bugs and complex tasks

6. Recommended next action:
   - restore missing base skills from the template
   - install or configure missing optional project skills and external tools only after explicit user confirmation
   - for bugs and complex tasks, use Superpowers when available or ask the user to choose install/configure vs manual fallback
