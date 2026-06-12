# AI Development Entry Point

This project uses a solo AI-development workflow.

Use this file as the short entry point. Detailed rules live in `ai/architecture.md` and relevant `ai/skills/*/SKILL.md`. Do not load them by default. Use them only when the task needs those details or when a workflow rule is unclear.

## Core rules

- Communicate with the user in Russian. Use simple words and briefly explain technical terms.
- Keep persistent AI-facing instructions in English.
- Prefer minimal diffs and clean architecture.
- Do not expand user-confirmed scope. If a larger scope looks useful, stop and ask first.
- Do not mix refactoring with bugfixes