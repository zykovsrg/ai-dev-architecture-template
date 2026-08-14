# Current Task

Status: active

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: review

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

architecture-update

## Goal

Back-port the Repository Provisioning feature from the installed hub into
`hub-template/`, and add the two installed-hub guards that would have caught the
drift, so the same divergence cannot recur after a reinstall or hub update.

Root cause: Repository Provisioning was authored directly in the installed hub
(`_ai-hub`) instead of upstream in `hub-template/`. `scripts/check-consistency.sh`
enforces hub entry parity only inside `hub-template/`, so nothing validated the
installed hub, and its `CLAUDE.md` never received the matching line.

## Use Superpowers

no

## Relevant files

- `hub-template/ai/architecture.md` — missing Repository Provisioning section
- `hub-template/CLAUDE.md`, `hub-template/AGENTS.md` — missing provisioning line
- `hub-template/ai/skills/project-create/SKILL.md` — missing Git/GitHub steps
- `scripts/check-hub-registry.sh` — missing entry-file parity and project memory checks
- `CHANGELOG.md`

## Done criteria

- `hub-template/` and the installed hub agree on all four provisioning files.
- `scripts/check-hub-registry.sh` validates entry-file parity and the six
  required project memory files, and passes against the installed hub.
- `bash scripts/check-consistency.sh` and `bash scripts/hub-smoke-test.sh` pass.
- Changes committed locally and pushed to GitHub in one commit per repository.

## Agent handoff

Last agent: Claude Opus 5 (hub mini-audit session, 2026-08-14)

What changed: ported the four provisioning files upstream, removed the Git
contradiction in the hub architecture, bumped hub architecture to 1.2, added
`validate_entry_files` and `validate_project_memory` to `check-hub-registry.sh`,
updated `hub-smoke-test.sh` to the new contract and covered both guards.

Open risks: the two new guards are fatal, so any registered active project that
lacks a memory file now blocks the whole registry check rather than warning.
`FT-20260814` (verify project-create on the next approved new project) is still
open and is not closed by this task.

Next agent should check: audit items 2 (duplicated project skills), 3 (nested
project memory) and 5 (uncommitted project changes) remain unresolved.
