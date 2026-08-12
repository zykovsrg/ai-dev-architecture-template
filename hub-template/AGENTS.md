# Personal AI Hub — Codex
<!-- Tool-specific activation: Codex reads AGENTS.md as its project entry file. -->

This is a multi-project hub. The hub registry defines what may be accessed.

## Project Routing

- Start every real request with project routing unless a project was confirmed in the current chat.
- A remembered project still requires explicit confirmation in a new chat.
- Before reading a selected project, show its registered `Project: <project-id>` and exact `Path: <registered-path>`.
- Do not read any selected project's memory or code before explicit confirmation.
- Do not access unregistered paths or paths outside allowed roots.
- Before confirmation, routing may use only hub-owned routing files: `ai/allowed-roots.md`, `ai/project-registry.md`, `ai/active-project.md`, and the matching hub project card.
- After confirmation, use hub skills against the selected project's memory and follow that project's instructions.

## Work Header And Procedures

- Always show `Project: <project-id>` and `Mode: <mode>` before project work.
- Use `Mode: routing` before confirmation; use the selected project's mode after confirmation.
- Route detailed procedures to `hub-template/ai/architecture.md` and one matching skill. Do not copy detailed rules into this entry file.
- If the request is ambiguous, preserve the confirmation gate and ask which registered project to use.

## Boundaries

- Treat project cards as hub metadata, not permission to inspect a project.
- Never place secrets, credentials, private keys, or raw environment values in hub files, cards, or cross-project signals.
- Change hub registry, allowed roots, entry rules, or architecture only with explicit user approval and the documented hub procedure.
