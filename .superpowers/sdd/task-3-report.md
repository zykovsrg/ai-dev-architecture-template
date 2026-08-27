# Task 3 report — Obsidian proposal scanner

## Scope

Added only the non-writing scanner and its contract test:

- `scripts/obsidian-task-sync.sh`
- `scripts/obsidian-task-sync-test.sh`

There is no `apply` command and no watcher in this task.

## Behaviour

- `scan --hub ABS --scope ABS --vault ABS` validates the local architecture
  vault, registry, scope, manifest v3, source hashes, and known task records.
  It writes only the local runtime proposal at
  `.ai-architecture-sync/pending-proposal.json`.
- The proposal contains `proposal_sha256`, actual board and manifest hashes,
  affected source hashes, explicit operations, and blocked reasons.
- `status --vault ABS` prints that exact JSON proposal and its hash.
- `dismiss --vault ABS` removes only the pending proposal.
- Known cards are matched exclusively by the verified Obsidian block ID
  `^TASK-ID` / `^FT-ID`. A title collision without an ID is blocked rather
  than treated as a known task.
- Tests cover rename, column/status move, due-date change, new future card,
  missing ID, duplicate ID, unknown column, unknown project, and unchanged
  canonical-source hashes.

## TDD evidence

### RED

After creating the fixture contract and before creating the scanner, this
command failed because the requested command did not exist:

```text
$ bash scripts/obsidian-task-sync-test.sh
scripts/obsidian-task-sync-test.sh: line 59: .../scripts/obsidian-task-sync.sh: No such file or directory
```

During GREEN implementation, the new-card fixture initially failed because
empty TSV fields were collapsed by Bash and its title was interpreted as an
ID. The scanner parser now uses a non-whitespace field separator, preserving
the empty ID of a valid new card.

### GREEN and fresh verification

```text
$ bash -n scripts/obsidian-task-sync.sh scripts/obsidian-task-sync-test.sh \
    scripts/generate-obsidian-projects-kanban.sh scripts/obsidian-projects-kanban-test.sh
$ bash scripts/obsidian-task-sync-test.sh
PASS: Obsidian confirmed task sync contract
$ bash scripts/obsidian-projects-kanban-test.sh
PASS: Obsidian task Kanban and project overview contract
$ git diff --check
```

All commands above exited with code 0.

## Concerns

The earlier plan text mentions an HTML ID comment, but Task 1’s verified
compatibility decision replaced it with Obsidian block IDs: the installed
Kanban plugin preserves `^TASK-ID` across card edits while it removes HTML
comments. This scanner follows that established format. Applying a proposal,
stale-proposal handling, and background detection intentionally remain Task 4
and Task 5 work.
