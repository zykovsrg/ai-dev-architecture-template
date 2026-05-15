# External Tools and Skills

This file lists external skills and tools used by this development setup.

External tools are not copied from this template.

The agent must check expected external tools and controlled external methodologies during the first-session environment check and report what is missing.

The agent must not install or activate anything without explicit user confirmation.

## Expected external skills and tools

These tools should be installed when available.

Missing expected external tools are warnings, not blockers.

### code-review-graph

Type: external code analysis tool

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

Purpose:
Additional context-engineering skills and workflows.

Expected: yes, if available.

How to check:
- check the user's configured Claude Code, Codex, or local skills directories
- if unsure, report `not confirmed`

Missing means:
Work can continue, but extra context-engineering skills are unavailable.

### claude-seo

Type: external SEO skillset

Purpose:
SEO, content, audit, and semantic-core tasks.

Expected: yes, if available.

How to check:
- check the user's configured Claude Code, Codex, or local skills directories
- if unsure, report `not confirmed`

Missing means:
Work can continue, but external SEO-specific workflows are unavailable.

## Controlled external methodologies

These tools may be installed and checked, but they must not become the default workflow.

### Superpowers

Type: full external development methodology

Status:
Expected to be installed when available, but gated.

Purpose:
Spec-first planning, TDD-first development, subagent-driven development, stronger verification, and branch-finishing workflows.

Use only when:
- the user explicitly asks to use Superpowers;
- `ai/current-task.md` says `Use Superpowers: yes`;
- the task is large, vague, risky, or requires design, TDD, or subagent-driven development.

Do not use for:
- small bugfixes;
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
Work can continue. Superpowers workflows are unavailable until installed.

## Reporting format

During environment check, return:

1. Required base skills:
   - present
   - missing

2. Expected external skills and tools:
   - present
   - missing
   - not confirmed

3. Controlled external methodologies:
   - present
   - missing
   - not confirmed
   - activation status: not active unless explicitly requested

4. Blockers:
   - only missing required base skills are blockers
   - missing external tools are warnings, not blockers

5. Recommended next action:
   - restore missing base skills from the template
   - install or configure missing external tools only after explicit user confirmation
   - activate Superpowers only after explicit user confirmation
