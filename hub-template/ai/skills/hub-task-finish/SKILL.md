---
name: hub-task-finish
description: Verify and close one confirmed registered project's task memory after separate approval.
---

# Hub Task Finish

Use this skill only after explicit confirmation of a confirmed registered
project and when the user asks to close its task. Its scope is the selected
project `ai/` memory only; do not require or read duplicated project
`AGENTS.md` or `CLAUDE.md` files.

## Procedure

Use the central Obsidian vault at `<hub>/projects/ai-dev-architecture/obsidian-vault`, derived from the confirmed
hub root. The selected board is
`Obsidian/Projects/<project-id>/Kanban.md` inside that vault. Select it by the
confirmed registered project ID; never ask for a per-project vault path.
Manual board edits remain reviewable proposals, not direct canonical writes.
Use these reverse commands with the mandatory selector:

```text
bash scripts/obsidian-task-sync.sh scan --project-id <confirmed-project-id> --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault
bash scripts/obsidian-task-sync.sh apply --project-id <confirmed-project-id> --confirm-proposal <sha256> --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault
```

1. Read the selected project's `ai/current-task.md` and the smallest relevant
   `ai/decisions.md`, `ai/changelog.md`, or `ai/future-tasks.md` file.
2. Check recorded Done criteria and report any missing verification or open
   risk. Do not change task memory during this check.
3. After the normal completion check, if durable records linked from this task
   may need a focused check, the agent may offer the hub-owned `hub-knowledge-review`
   workflow, but must never start it automatically. Declining the offer has no effect on task closure. An accepted offer starts that separate workflow with
   its own scope, containment checks, and confirmation gate.
4. Require a separate explicit confirmation before writing the approved
   changelog, decision, future-task, or current-task cleanup.
5. After confirmation, save only the selected project's result through its
   repository and report whether it was saved locally or pushed.
6. After an approved selected-project task write, invoke the guarded trusted architecture-to-Obsidian refresh
   with `--write --refresh-from-architecture`.
   This direction is trusted only from canonical `ai/` records to generated
   Obsidian views. Keep manifest validation enabled. If it detects a manual
   Obsidian edit, run the local `obsidian-task-sync scan --project-id <confirmed-project-id>` to create its pending
   proposal, report that proposal, and do not overwrite the board.
7. Obsidian-to-`ai/` is a confirmed Obsidian-to-architecture proposal only:
   show its exact status and require `apply --project-id <confirmed-project-id> --confirm-proposal <sha256>` before
   any canonical task write.

This workflow cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules. Its closure writes remain limited to selected project
`ai/` memory. It never closes, copies, or cleans another project's task memory,
and an optional review offer does not authorize reading or writing knowledge.
