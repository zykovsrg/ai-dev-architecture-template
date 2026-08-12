# Task 1 Report

## Implementation summary

Implemented the hub registry schema and a read-only Bash 3.2-compatible validator. The validator checks required registry files, project IDs, statuses, card paths, allowed roots, and canonical paths for symlink escapes without reading project contents.

Added the requested hub memory templates and the synthetic registry smoke test.

## Changed files

- `scripts/check-hub-registry.sh`
- `scripts/hub-smoke-test.sh`
- `hub-template/ai/allowed-roots.md`
- `hub-template/ai/active-project.md`
- `hub-template/ai/project-registry.md`
- `hub-template/ai/project-cards/.gitkeep`
- `hub-template/ai/cross-project-signals.md`
- `hub-template/ai/archive/.gitkeep`

## TDD RED/GREEN

RED command:

```text
bash scripts/hub-smoke-test.sh
```

Expected RED result:

```text
exit=127
bash: .../scripts/check-hub-registry.sh: No such file or directory
```

GREEN command:

```text
bash scripts/hub-smoke-test.sh
```

Result: exit `0`; the valid fixture contained `Registry check passed`, and the invalid fixture was rejected with `outside allowed roots`.

## All tests and checks

- `bash scripts/hub-smoke-test.sh` — passed.
- `bash scripts/smoke-test.sh` — passed: `Smoke tests passed.`
- `bash scripts/check-consistency.sh` — passed: `All canonical lists are consistent.`
- `bash -n scripts/check-hub-registry.sh scripts/hub-smoke-test.sh` — passed.
- Additional validator cases for duplicate IDs, invalid statuses, missing cards, and symlink escapes — passed.
- `git diff --check` — passed before commit.

## Self-review

- Scope is limited to the eight Task 1 files.
- Existing files and controlled task memory were not modified.
- The validator performs no project-directory listing or project-content reads.
- The final commit is `1d453b2 feat: add hub registry schema and validation`.

## Concerns

The validator snippet in the brief only checked project paths when the path already existed, but the required smoke test uses a non-existent outside path. I added the minimal `else` branch to validate non-existent paths lexically against allowed roots; existing paths still use canonical `pwd -P` validation for symlink escapes.

## P1 follow-up: allowed-root and missing-path containment

### TDD RED/GREEN

RED command executed:

```text
bash scripts/hub-smoke-test.sh; task_status=$?; printf 'exit=%s\n' "$task_status"; exit "$task_status"
```

RED output:

```text
FAIL: expected 'allowed root does not exist' in /var/folders/05/3cf4thws0hdclnk3jfl6vz8r0000gn/T//ai-hub-smoke.qscIjL/missing-root.out
exit=1
```

GREEN command executed:

```text
bash scripts/hub-smoke-test.sh; task_status=$?; printf 'exit=%s\n' "$task_status"; exit "$task_status"
```

GREEN output:

```text
exit=0
```

### Changed files

- `scripts/check-hub-registry.sh`
- `scripts/hub-smoke-test.sh`
- `.superpowers/sdd/task-1-report.md`

### Verification

- `bash scripts/hub-smoke-test.sh` — exit `0` (no output; all assertions passed).
- `bash -n scripts/check-hub-registry.sh scripts/hub-smoke-test.sh` — exit `0`.
- `bash scripts/smoke-test.sh` — exit `0`; output: `Smoke tests passed.`
- `git diff --check` — exit `0`.

### Self-review

- Every listed allowed root is checked before registry entries; a nonexistent root prints `ERROR:` and exits `1`.
- Project paths are resolved component-by-component: `..` is normalized and each existing directory or symlink component is resolved with physical `pwd -P` before containment is evaluated.
- A normal missing descendant of an allowed root remains valid with `Status: missing`; lexical and symlink component escapes are rejected.
- No schema/template content changed, and the validator still does not list or read project contents.

## Task 1 review fix: reject filesystem root

### TDD RED/GREEN

RED command:

```text
bash scripts/hub-smoke-test.sh
```

Result: failed because the new regression case expected `ERROR: allowed root must not be /`, which the validator did not yet emit.

GREEN command:

```text
bash scripts/hub-smoke-test.sh
```

Result: exit `0`.

### Verification

- `bash scripts/hub-smoke-test.sh` — passed.
- `bash -n scripts/check-hub-registry.sh scripts/hub-smoke-test.sh` — passed.
- `git diff --check` — passed.

### Change

- Added Bash 3.2-compatible rejection of `/` in allowed-root validation.
- Added a regression case asserting failure with an `ERROR:` message.

## Root slash bypass fix

RED: added smoke regressions for `//` and an allowed-root symlink resolving to `/`; `bash scripts/hub-smoke-test.sh` failed before the fix.

GREEN: canonicalize each allowed root with `pwd -P`, normalize `//` to `/`, and reject the canonical filesystem root. `bash scripts/hub-smoke-test.sh`, `bash -n scripts/check-hub-registry.sh scripts/hub-smoke-test.sh`, and `git diff --check` all passed.
