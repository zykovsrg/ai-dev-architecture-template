# Learning Module Rules

## Hub-Managed Project Flow

- `hub-session-review` — reviews a completed task's current session or an
  explicitly selected session. Reviews live only in the selected project's
  `ai/session-reviews/`; findings are proposals and require explicit approval
  before any improvement is applied.

## Self-Learning Workflows

`ai/workflow-observations.md` is the canonical append-only journal of workflow
friction and calendar drift. A rule matures at three repeats, or two within one
week; `retire_rule` is the only way to remove it and also needs confirmation.

`ai/tmp/calendar-snapshots/` and `ai/tmp/workflow-friction/` are non-canonical
caches, written without confirmation and pruned after 14 days.
`scripts/check-workflow-memory.sh` validates the two canonical learning files.
These workflows remain independent of `hub-session-review`: a session review
supplies improvement proposals but never automatically changes a rule or
consumes a pending observation.
