# Registered Project Architecture

The shared architecture for this registered project belongs to the Personal AI
Hub at `../../..`:

- `../../../AGENTS.md` or `../../../CLAUDE.md` for the active agent;
- `../../../ai/architecture.md` for shared workflows and rule precedence.

Keep project-specific facts in `project-context.md` and project-specific
invariants in `decisions.md`. This file must not duplicate shared hub rules.
If the project is moved outside that hub, replace this file with an explicit
standalone architecture; never guess a different hub location.
