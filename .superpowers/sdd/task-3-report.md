# Task 3 Report: Updater safety and user documentation

## Implementation summary

The standalone architecture updater now makes its knowledge boundary explicit:
`knowledge/` remains outside both `ARCHITECTURE_FILES` and
`CONTROLLED_MEMORY_FILES`, and every normal update reports that it does not
enable knowledge in existing projects. A new smoke fixture represents a
pre-knowledge project and proves that `--apply` neither creates `knowledge/`
nor changes existing task memory.

The user documentation now consistently explains that knowledge is optional,
separate from `ai/project-context.md`, and deliberately captured rather than
implicitly enabled by an update. It documents the five record statuses,
`knowledge-capture`/`knowledge-review` confirmation gates, and the optional
focused review offer from `task-finish`.

## Changed files

- `scripts/update-installed-architecture.sh`
- `scripts/smoke-test.sh`
- `docs/file-roles.md`
- `docs/install.md`
- `docs/update.md`
- `docs/concepts.md`
- `.superpowers/sdd/task-3-report.md`

## TDD evidence

### RED

The pre-knowledge fixture and its assertion for the required lifecycle message
were added to `scripts/smoke-test.sh` before the updater output was added.

```text
bash scripts/smoke-test.sh
FAIL: expected 'Updating does not enable knowledge in existing projects.' in .../pre-knowledge-update.out
```

The same fixture had already asserted that `knowledge/` was absent and that
`ai/current-task.md` matched its pre-update copy. The failing message confirms
the new lifecycle contract was not merely documented after the implementation.

### GREEN

After adding the explicit updater boundary comment and lifecycle output, the
full smoke suite passed, including the new fixture.

```text
Smoke tests passed.
Hub smoke tests passed.
```

## Fresh verification

All commands below completed with exit code `0` after the final changes:

- `bash scripts/check-consistency.sh`
- `bash scripts/smoke-test.sh`
- `bash -n scripts/update-installed-architecture.sh scripts/smoke-test.sh`
- `git diff --check`

`check-consistency` reported that all canonical lists are consistent and that
the standalone updaters do not overwrite controlled memory.

## Concerns

No open concerns. Legacy standalone migration remains outside this change:
the normal updater neither migrates nor enables knowledge in existing projects.
