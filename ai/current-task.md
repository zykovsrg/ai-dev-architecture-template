# Current Task

Status: done
Task ID: TASK-ai-dev-architecture-20260915-002
Stage: task-finish

## Goal

Stop task discovery from silently skipping task records whose headings do not
match the machine-read format, and document that format.

## Done criteria

- The compact task index warns on stderr about every skipped `###` heading.
- `check-all-task-records.sh` fails on skipped headings; template examples pass.
- `hub-workflows` requires surfacing those warnings to the user.
- `task-record-format.md` documents future and paused heading formats.
- Tests cover warnings, strict check, and paused due after `Paused:` metadata.

## Agent handoff

Last agent: Claude

What changed: Heading warnings and strict check added in `task_records.py`,
`read-compact-task-index.py`, `check-all-task-records.sh`; paused compact
parsing now reads due after `Paused:`/`Stage:` lines; instructions updated;
release manifest rebuilt. Installed and verified in the working Hub first.

Verification: 106 unit tests and all shell tests passed; release manifest
check passed; working Hub check-all-task-records passed with no warnings.

Open risks: Records without IDs created by other tools still need manual
normalization when warnings appear.
