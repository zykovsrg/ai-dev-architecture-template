---
name: architecture-update
type: worker
description: |
  Use when a new important rule, workflow, project constraint, skill, or architecture principle should be added to the AI development architecture.
  Activates when:
  - the user asks to add, change, or remove development rules
  - a new reusable workflow or project constraint appears
  - AGENTS.md, CLAUDE.md, ai/architecture.md, ai/decisions.md, or skills may need an update
  Does NOT activate for:
  - temporary preferences
  - one-off task constraints
  - normal implementation or review work
---

# Architecture Update

Use when the user wants to add or change development rules, project rules, skills, or workflow.

Do not edit files without explicit user confirmation. Before replacing any architecture rule, show what changes, what it changes to, and ask: "Replace this?"

## Steps

1. Identify what changed.
2. Decide where it belongs:
   - `AGENTS.md`
   - `CLAUDE.md`
   - `ai/architecture.md`
   - `ai/project-context.md`
   - `ai/decisions.md`
   - `ai/skills/.../SKILL.md`
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
- Prefer `ai/decisions.md` for important active decisions.
