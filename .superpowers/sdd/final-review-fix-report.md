# Final-review P2 fix report

Date: 2026-08-25

## Scope

Fixed the four P2 findings in the generated Obsidian project board only.
No real copied vault, original vault, Calendar data, or architecture-memory
file was changed.

## Root cause

- `--write` validated that each supplied ID was registered, but did not ensure
  that the scope was the complete registry.
- Classification considered an active current task before a canonical registry
  status of `completed`.
- Action extraction ran for every non-legacy, non-archived project, including
  non-actionable current-task states.
- Due extraction scanned all task files, so it could use a date from a
  completed, blocked, dropped, paused, or archived record.

## Changes

- `--write` now requires its sorted, unique scope to exactly equal all sorted,
  unique project IDs from `ai/project-registry.md`. Preview remains scoped.
- `completed` now takes precedence over current-task states; `archived` still
  takes highest precedence.
- Current-task actions and dates are emitted only for canonical active projects
  with `active`, `ready`, or `in_progress` current state.
- Ready future entries remain eligible. Their date is parsed only from the same
  `Status: ready` entry, and is used only when no eligible current-task date is
  available.
- Expanded the end-to-end fixture test: completed precedence; hidden actions
  and dates for waiting, paused, completed, archived, done, review, and
  blocked records; preserved current and ready-future dates; and rejected
  truncated write scope without changing either generated target.

## TDD evidence

1. Added the regression fixtures and assertions before changing the generator.
2. Red command:

   ```text
   bash scripts/obsidian-projects-kanban-test.sh
   FAIL: expected Completed project in Completed, got Active
   ```

3. Applied the minimal generator fix.
4. Green command:

   ```text
   bash scripts/obsidian-projects-kanban-test.sh
   PASS: Obsidian project board contract
   ```

## Verification commands and output

```text
bash -n scripts/generate-obsidian-projects-kanban.sh scripts/obsidian-projects-kanban-test.sh && bash scripts/obsidian-projects-kanban-test.sh
PASS: Obsidian project board contract

bash scripts/smoke-test.sh
Smoke tests passed.
Sentinel evidence: validator output and xtrace contain neither the marker nor the named forbidden file paths.
Unregistered-directory evidence: warned on stderr, exit code and stdout summary unchanged.
Malicious traversal evidence: lexical and symlink card escapes were rejected before the card-content check; sentinel markers were absent from output and xtrace.
Scale fixture: 5 projects, 1059/2400 bytes
Scale fixture: 20 projects, 4254/9600 bytes
Scale fixture: 50 projects, 10674/24000 bytes

git diff --check
(exit 0; no output)
```

## Changed files

- `scripts/generate-obsidian-projects-kanban.sh`
- `scripts/obsidian-projects-kanban-test.sh`
- `.superpowers/sdd/final-review-fix-report.md`

## Risks and limits

- The exact-write guard intentionally affects only `--write`; a partial
  `--preview` is still permitted for review.
- The date parser accepts only explicit `due: YYYY-MM-DD` values within an
  eligible record. It deliberately ignores free-form dates.
