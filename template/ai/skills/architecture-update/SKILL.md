---
name: architecture-update
type: worker
description: |
  Use when a new important rule, workflow, project constraint, skill, or architecture principle should be added to the AI development architecture.
  Activates when:
  - the user asks to add, change, or remove development rules
  - a new reusable workflow or project constraint appears
  - stale architecture or project memory is discovered
  - AGENTS.md, CLAUDE.md, ai/architecture.md, ai/external-tools.md, ai/skills/*, ai/project-context.md, or ai/decisions.md may need an update
  Does NOT activate for:
  - temporary preferences
  - one-off task constraints
  - normal implementation or review work
---

# Architecture Update

Open this skill before applying architecture-update. Do not rely on memory.

Use when the user wants to add or change development rules, project rules, skills, tools, durable decisions, or workflow.

Do not edit files without explicit user confirmation. Before replacing any architecture rule, show what changes, what it changes to, and ask: "Replace this?"

## When stale content is found

If an agent discovers stale content in architecture or controlled memory files, it must not only mention it in chat or changelog.

It should propose a concrete update task and wait for confirmation before editing.

Examples of stale or durable content that may need an update:

- outdated `ai/project-context.md` rule;
- missing storage, signing, sandboxing, or deployment invariant;
- missing undo, sync, recurrence, scheduling, or data model decision;
- outdated skill trigger;
- external tool list no longer matches the project;
- workflow rule that repeatedly fails in real sessions.

## Steps

1. Identify what changed or what is stale.
2. Decide where it belongs:
   - `AGENTS.md`
   - `CLAUDE.md`
   - `ai/architecture.md`
   - `ai/external-tools.md`
   - `ai/project-context.md`
   - `ai/decisions.md`
   - `ai/skills/.../SKILL.md`
   - docs files that explain installation or usage
3. Show current wording or current behavior.
4. Show replacement wording or replacement behavior.
5. Ask explicitly: "Replace this?"
6. Explain why it belongs there.
7. Explain token impact:
   - always loaded
   - loaded only when requested
   - skill-based
8. Wait for explicit user confirmation.
9. Only after confirmation, update files.
10. Sync the architecture repository documentation if available. If repo access is not available, return the exact text that must be added or replaced.
11. If `scripts/check-consistency.sh` exists (you are working in the architecture template repository itself) and you edited any canonical list (a `<!-- canon:... -->` block), run `bash scripts/check-consistency.sh` and confirm it passes before finishing. If it fails, fix the named holder so all copies match. In an installed project this script is absent — skip this step.

## Rules

- Do not add temporary preferences to permanent rules.
- Do not duplicate full rules in many files.
- Use layered storage: short mandatory version in `AGENTS.md` and `CLAUDE.md`, detailed version in `ai/architecture.md`, practical checks in relevant skills.
- Keep `AGENTS.md` and `CLAUDE.md` short.
- Write permanent AI-facing instruction content in English.
- Working project memory files may be written in Russian or English.
- Explain proposed architecture changes to the user in Russian.
- Prefer skills for procedures.
- Prefer `ai/architecture.md` for workflow overview.
- Prefer `ai/decisions.md` for important active decisions and durable project invariants.
- Prefer `ai/changelog.md` for recent history, not durable constraints.
