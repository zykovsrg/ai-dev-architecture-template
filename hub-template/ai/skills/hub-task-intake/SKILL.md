---
name: hub-task-intake
description: Record or classify requested work for one confirmed registered project without crossing hub boundaries.
---

# Hub Task Intake

Use this skill only after explicit confirmation of a confirmed registered
project and after the hub-owned `hub-environment-check`. Its scope is the selected
project `ai/` memory only; do not require or read duplicated project
`AGENTS.md` or `CLAUDE.md` files.

## Procedure

1. Read the selected project's `ai/current-task.md`.
2. If it is empty, record the user's requested goal, scope, Done criteria, and
   `Stage: intake` in that same file. Write a concrete unique `Task ID:` in the
   `TASK-<UTC-date>-<NNN>` form, where `<NNN>` is the next free three-digit
   number for that date across the selected project's `ai/current-task.md` and
   `ai/paused-tasks.md`; never leave the `TASK-YYYYMMDD-NNN` placeholder.
3. If it is unfinished, compare the request with its recorded Done criteria.
   Continue only when it fits; otherwise stop and require the hub-owned
   `hub-task-switch` workflow.
4. Keep out-of-scope ideas out of the current task until the user separately
   approves their project-memory update.
5. After an approved selected-project task write, invoke the guarded trusted architecture-to-Obsidian refresh
   with `--write --refresh-from-architecture`.
   This direction is trusted only from canonical `ai/` records to generated
   Obsidian views. Keep manifest validation enabled. If it detects a manual
   Obsidian edit, report the pending proposal and do not overwrite it.
6. Obsidian-to-`ai/` is a confirmed Obsidian-to-architecture proposal only:
   show its exact status and require `apply --confirm-proposal <sha256>` before
   any canonical task write.

This workflow cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules. It never reads, writes, or classifies another project's
memory.
