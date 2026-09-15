# Scoped Obsidian forward refresh

## Confirmed scope

Fix the generator's one-project write mode without expanding the supplied scope.
The user also explicitly approved the scoped-refresh paragraph in
`hub-task-intake`, `hub-task-switch`, `hub-task-finish`, and `hub-info-update`,
both in `hub-template/` and in the installed Hub. No central architecture or
entry rules were changed.

## Cause and implementation

The generator rejected every write whose IDs differed from the complete
registry. Removing that check alone would have deleted unrelated generated
boards and replaced their overview/manifest records with a partial set.

The generator now distinguishes full-registry scope from a partial scope:

- Both modes validate the supplied IDs and selected paths and render only IDs
  from the scope file. No IDs are automatically added.
- Partial writes validate the existing v4 manifest, overview hash, and selected
  board hashes. They replace only selected overview rows and selected board,
  task, and source entries in the shared manifest. Foreign shared records are
  retained; foreign cards, task sources, and boards are never opened.
- Only full-registry mode retains the existing retired-board cleanup.
- Both modes use the existing staged transaction and rollback mechanism.
- A new partial projection can initialize absent shared generated files.
  Existing untracked selected boards still block publication.
- Partial mode refuses legacy v3 migration. A separately authorized full-scope
  rebuild is needed for that migration; the command never expands scope itself.
- Preview retains its existing read-only, supplied-scope rendering behavior.

The tested generator was copied to the installed Hub after confirming that its
previous contents exactly matched the source repository's HEAD. All four
installed workflow files match their updated template counterparts. Release
hashes were updated only for these five changed files.

## Verification

All executions used synthetic temporary fixtures, not other registered projects
or the live vault's project boards.

- Original regression: the single-project test failed with
  `error: write scope must match all registered project IDs` before the fix.
- `tests/test_scoped_obsidian_refresh.py`: 15 tests passed against the installed
  generator. Coverage includes one-project and full writes, FIFO read traps for
  foreign files, manual edits, manifest merging, invalid IDs, unsafe paths,
  rollback at each of three publication moves, empty task sets, new projects,
  initialization, read-only preview, and a confirmed undated reverse proposal.
- `scripts/obsidian-projects-kanban-test.sh`: passed, including the existing
  complete-registry refresh, migration, and transaction contracts.
- Bash syntax, `git diff --check`, and exact installed/source parity: passed.
- Independent read-only review found no actionable defects. Its initial
  rollback-coverage gap was subsequently covered by failure-injection tests.

## Existing broader check limitations

- `check-consistency.sh` and `smoke-test.sh` stop because the existing untracked
  `ai/skills/` directory is present in this project (its directory timestamp
  predates this work). These files were not modified or removed.
- `obsidian-task-sync-test.sh` exits 3 at the dated-task calendar confirmation
  gate. An isolated copy of the unmodified HEAD scripts reproduces the same
  exit and message. The new undated one-project scan/apply integration test passes.
- The release manifest already has 11 stale source hashes outside this change;
  a full release consistency check is therefore not claimed as passing.

These unrelated cleanup/update tasks are deferred to avoid changing architecture
rules, calendar approval behavior, or unrelated release entries in this fix.

## Closure update

The user subsequently authorized task closure, updating the working architecture,
and publishing to GitHub. The installed five task files were verified equal to
the source. The complete release manifest was rebuilt against existing source
files and its consistency check passed; the earlier stale-hash limitation is
resolved as metadata only. The remaining broader test limitations above remain.
The session review is `ai/session-reviews/2026-09-15-scoped-obsidian-refresh-closure.md`.
