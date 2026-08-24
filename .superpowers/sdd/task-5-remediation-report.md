# Task 5 — final-review remediation

## Scope

Changed only the assigned scripts, `docs/file-roles.md`, smoke tests, and this
report. Protected hub entry files, architecture, and skills were not edited.

## Fixes

- Installation and installed-hub updates now distribute
  `read-compact-project-index.sh`.
- The compact reader now validates only routing metadata (`project_id`, name,
  tags, status) and the card `Purpose`. It does not call the full registry
  validator, inspect project `ai/`, warn about unregistered directories, parse
  project paths, or validate other card fields.
- Archiproject registry entries now validate slug IDs, nonempty name and unit,
  allowed status, numeric target, and calendar-valid ISO due date or `none`.
- `archiproject_contribution: 0` is accepted; negative and nonnumeric values
  remain rejected.
- The file-roles documentation now uses the canonical snake_case card fields.

## TDD evidence

- Baseline smoke passed before the new regression coverage.
- The new zero-contribution regression initially failed with the former
  positive-only rule.
- The new metadata-only compact-index regression initially failed because the
  reader called the full validator.
- The installation regression initially failed because the reader was absent
  from an installed hub.

## Verification

- `bash scripts/hub-smoke-test.sh` — passed.
- `bash scripts/check-consistency.sh` — passed.
- `bash -n` for all changed shell scripts — passed.
- `git diff --check` — passed.
