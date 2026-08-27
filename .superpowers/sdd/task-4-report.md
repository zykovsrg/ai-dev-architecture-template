# Task 4 report — confirmed Obsidian task proposals

## Scope

Implemented only Task 4: confirmed `apply`, stale-proposal guards, staged
canonical writes, and the minimal generator escape hatch needed to regenerate
the confirmed board. Task 5 watcher, templates, and documentation were not
changed.

## Delivered

- `obsidian-task-sync.sh apply --hub ... --scope ... --vault ... --confirm-proposal SHA256`
  is the only reverse writer.
- Apply accepts only a ready, structurally valid proposal whose supplied SHA-256
  equals the proposal's canonical payload hash.
- Board, manifest, and every affected canonical source are checked before any
  source replacement. A stale proposal is retained and the sources remain
  unchanged.
- Operations are written to same-directory temporary files, validated, then
  atomically renamed one file at a time. Supported operations are rename, due
  date, future task creation, and supported status moves.
- Promotion creates a fresh `TASK-YYYYMMDD-NNN` current-task ID, marks the
  future record `promoted`, and pauses the replaced active current task.
- Successful apply regenerates the three generated views and removes the
  proposal.
- Generator flag `--replace-confirmed-board` bypasses only the task-board hash
  check and is rejected unless combined with `--write --refresh-from-architecture`.

## TDD evidence

1. Added tests for wrong confirmation and explicit stale-source error. The first
   run failed because `load_known_cards` reported a manifest mismatch before the
   stale-proposal check. Reordered apply so affected source hashes are checked
   first; the test then passed.
2. Added apply coverage for due dates, promotion, and new future cards. The
   first promotion run failed with:
   `error: invalid temporary current task: .../current-task.md`.
   The cause was copying the `FT-*` ID into current-task. Promotion now creates
   a valid `TASK-*` ID and retains the source record as `promoted`; the test
   then passed.
3. Added a direct generator-bypass regression test. **RED:**
   `FAIL: unconfirmed board replacement succeeded`. **GREEN:** replacement now
   requires `--confirm-generated-write`, and `apply` passes that flag only
   after proposal hash and stale-state checks.
4. Added one combined rename + due + Active-promotion fixture. **RED:** the
   generated current task retained the old title. **GREEN:** promotion reads
   the staged temporary future record, so the new current task keeps the new
   title; its due update is redirected to that current record.

## Fresh verification

```text
$ bash scripts/obsidian-task-sync-test.sh
PASS: Obsidian confirmed task sync contract

$ bash scripts/obsidian-projects-kanban-test.sh
PASS: Obsidian task Kanban and project overview contract

$ bash -n scripts/*.sh
exit 0

$ git diff --check
exit 0
```

## Concerns

- All canonical files are fully staged and validated before the first rename.
  Each replacement is atomic within its directory, but POSIX has no atomic
  multi-file rename. A process crash during the short rename loop could leave
  a mixed set; the specified Task 4 contract does not include crash-recovery
  journaling.
