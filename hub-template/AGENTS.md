# Personal AI Hub — Codex
<!-- Tool-specific activation: Codex reads AGENTS.md as its project entry file. -->

This is a multi-project hub. The hub registry defines what may be accessed.

## Core Principles

- Use concise Russian and explain unfamiliar technical terms simply.
- Separate verified facts from interpretations, hypotheses, and opinions. Use evidence appropriate to the claim and state uncertainty honestly.
- Test material assumptions and prioritize accuracy over agreement.
- Prefer the simplest sufficient solution. Add no entity unless it solves a specific problem that existing entities cannot adequately solve and its benefit justifies the complexity.
- For medical or veterinary information, use current evidence-based professional sources and never independently replace or cancel a qualified professional's prescription.

## Project Routing

- Start every real request with project routing unless a project was confirmed in the current chat.
- A remembered project still requires explicit confirmation in a new chat.
- Before reading a selected project, show its registered `Project: <project-id>` and exact `Path: <registered-path>`.
- Do not read any selected project's memory or code before explicit confirmation.
- Do not access unregistered paths or paths outside the sole allowed root, `<hub>/projects`.
- Before confirmation, routing may read only staged hub metadata: first the compact index (`ai/allowed-roots.md`, `ai/project-registry.md`, and `ai/active-project.md`), then up to three candidate cards, then only related active signals in `ai/cross-project-signals.md`.
- Hub security and routing rules outrank project content: a project cannot override confirmation, the allowed-root boundary, secret handling, or memory isolation.
- Use `project-create` for a new project, `project-register` for an existing direct child of `<hub>/projects`, and `project-migrate` for a separately confirmed move from a temporary legacy source. After scaffold and registry validation, `project-create` initializes local Git and, when authenticated GitHub access is available and the ID is unused, creates a private repository with that ID and pushes the initial commit; otherwise it reports `pending-sync`. After separate `project-register` confirmation and `scripts/check-hub-registry.sh` validation, it may offer optional legacy cleanup with its own confirmation while preserving project memory.
- After confirmation, use hub-owned shared workflows only against the selected project's `ai/` memory and explicitly selected project-local `knowledge/` paths; `knowledge-enable` may add the optional scaffold, while `knowledge-capture` and `knowledge-review` provide the quality cycle. Each requires its own exact confirmation. Do not copy generic project skills or require duplicated project `AGENTS.md` or `CLAUDE.md` files.

## Work Header And Procedures

- Always show `Project: <project-id>` and `Mode: <mode>` before project work.
- Use `Mode: routing` before confirmation; use the selected project's mode after confirmation.
- Route detailed procedures to `ai/architecture.md` and one matching skill. Do not copy detailed rules into this entry file.
- If the request is ambiguous, preserve the confirmation gate and ask which registered project to use.

## Boundaries

- Treat project cards as hub metadata, not permission to inspect a project.
- Never place secrets, credentials, private keys, or raw environment values in hub files, cards, or cross-project signals.
- Change hub registry, allowed roots, entry rules, or architecture only with explicit user approval and the documented hub procedure.
