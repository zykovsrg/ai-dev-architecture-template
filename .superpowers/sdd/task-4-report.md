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
5. Added a two-future-tasks-to-Active fixture. **RED:** scanner produced a
   ready proposal for multiple Active tasks in one project. **GREEN:** scanner
   now validates the final board delta, creates `state: blocked` with a clear
   reason, leaves canonical files unchanged, and `apply` rejects the proposal.

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

## Final-review P1 remediation — RED/GREEN

1. **Promotion replacement files were not both stale-checked.**
   **RED:** the new fixture promoted a future card, edited a replacement file,
   and inspected the signed proposal. It failed with
   `FAIL: proposal did not hash promotion target: paused-tasks.md`.
   **GREEN:** a promotion now adds both project replacement targets
   (`current-task.md` and `paused-tasks.md`) with SHA-256 values to
   `affected_sources` while scanning. `apply` therefore verifies and stages
   both before processing operations. The fixture checks stale edits to each
   file, plus an empty current-task file that is absent from the manifest; all
   fail before a canonical write.

2. **Two promotions could allocate the same TASK ID.**
   **RED:** promoting one future task in each of two projects in a single
   proposal failed during regeneration with `error: duplicate task ID in
   renderable tasks`.
   **GREEN:** `next_task_id` now considers staged files and IDs reserved by
   the same apply operation, then reserves the generated ID immediately. The
   fixture confirms that both resulting current tasks have distinct valid
   `TASK-YYYYMMDD-NNN` IDs before generator output is accepted.

3. **Non-active unfinished current tasks were overwritten.**
   **RED:** promoting over a `ready` current task failed with
   `FAIL: expected 'Prior ready task' in .../paused-tasks.md`.
   **GREEN:** promotion now preserves `active`, `ready`, `in_progress`,
   `waiting`, `blocked`, `review`, and `paused` current records as paused
   records. It also retains `done`/`completed` records with their terminal
   state, and safely leaves a truly empty current file without a phantom
   archive record. Focused fixtures cover every unfinished state and the
   completed case.

### Verification after remediation

```text
$ bash scripts/obsidian-task-sync-test.sh
PASS: Obsidian confirmed task sync contract

$ bash scripts/obsidian-projects-kanban-test.sh
PASS: Obsidian task Kanban and project overview contract

$ bash -n scripts/obsidian-task-sync.sh scripts/obsidian-task-sync-test.sh \
    scripts/generate-obsidian-projects-kanban.sh scripts/obsidian-projects-kanban-test.sh
exit 0

$ git diff --check
exit 0
```
