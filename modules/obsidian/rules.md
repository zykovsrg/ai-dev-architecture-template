# Obsidian Module Rules

## Vault

The hub has one central Obsidian vault at `<hub>/projects/ai-dev-architecture/obsidian-vault`.
Workflows derive this path from the confirmed hub root; they must not ask for
or accept a per-project vault path. The selected board is
`Obsidian/Projects/<project-id>/Kanban.md` inside that vault. A reverse
proposal always selects exactly one confirmed project board by its registered
project ID.

Use a scope file containing only the confirmed project ID. Never expand scope
to bypass a refresh error. A partial refresh updates only scoped boards, their
overview rows, and their manifest entries; it preserves all other projects
without reading their files. A full-registry refresh requires explicit
authorization for that full scope. If a partial refresh is blocked, report the
blocker and leave the generated views unchanged.

Manual Obsidian edits are never written to canonical records automatically:
they produce a reviewable proposal only.

## after-task-write

After an approved selected-project task write, invoke the guarded trusted
architecture-to-Obsidian refresh with:

```text
bash scripts/generate-obsidian-projects-kanban.sh --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault --write --refresh-from-architecture
```

This direction is trusted only from canonical `ai/` records to generated
Obsidian views. Keep manifest validation enabled. If it detects a manual
Obsidian edit, run the local `obsidian-task-sync scan --project-id
<confirmed-project-id>` to create its pending proposal, report that proposal,
and do not overwrite the board.

## Reverse proposals

Obsidian-to-`ai/` is a confirmed Obsidian-to-architecture proposal only:
show its exact status and require `apply --project-id <confirmed-project-id>
--confirm-proposal <sha256>` before any canonical task write. Use these
commands with the real hub, scope, and vault values:

```text
bash scripts/obsidian-task-sync.sh scan --project-id <confirmed-project-id> --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault
bash scripts/obsidian-task-sync.sh apply --project-id <confirmed-project-id> --confirm-proposal <sha256> --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault
```

The ID is mandatory for both scan and apply. Apply only after the user
confirms the proposal SHA.
