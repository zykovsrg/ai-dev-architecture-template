---
name: hub-task-switch
description: Safely change one confirmed registered project's unfinished task after separate approval.
---

# Hub Task Switch

Use this skill only after explicit confirmation of a confirmed registered
project and after the hub-owned `hub-task-intake` classifies the request as a
different task. Its scope is the selected project `ai/` memory only; do not
require or read duplicated project `AGENTS.md` or `CLAUDE.md` files.

## Procedure

1. Read only the selected project's `ai/current-task.md` and
   `ai/paused-tasks.md`.
2. Show the current goal, the requested replacement, and the exact project
   memory files that would change.
3. Require a separate explicit confirmation before pausing the current task,
   writing the replacement task, or promoting a future task.
4. After confirmation, make only the approved memory changes in the selected
   project. Never transfer task content to another project.
5. After that approved selected-project task write, invoke the guarded trusted architecture-to-Obsidian refresh
   with `--write --refresh-from-architecture`.
   This direction is trusted only from canonical `ai/` records to generated
   Obsidian views. Keep manifest validation enabled. If it detects a manual
   Obsidian edit, report the pending proposal and do not overwrite it.
6. Obsidian-to-`ai/` is a confirmed Obsidian-to-architecture proposal only:
   show its exact status and require `apply --confirm-proposal <sha256>` before
   any canonical task write.

This workflow cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules. It never changes task state during a project switch.
