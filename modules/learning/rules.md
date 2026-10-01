# Learning Module Rules

## Hub-Managed Project Flow

- `hub-session-review` — reviews a completed task's current session or an
  explicitly selected session. Reviews live only in the selected project's
  `ai/session-reviews/`; improvements the review finds are applied directly
  and reported; removing an existing rule waits for an explicit yes.

## Self-Learning Workflows

`ai/workflow-observations.md` is the canonical append-only journal of workflow
friction and calendar drift. A rule matures at three repeats, or two within one
week; `retire_rule` is the only way to remove it and needs an explicit yes, because it deletes a rule.

`ai/tmp/calendar-snapshots/` and `ai/tmp/workflow-friction/` are non-canonical
caches, written directly and pruned after 14 days.
`scripts/check-workflow-memory.sh` validates the two canonical learning files.
These workflows remain independent of `hub-session-review`: a session review
supplies improvement proposals but never automatically changes a rule or
consumes a pending observation.

## before-task-close

When `hub-task-finish` fires `before-task-close` after the Done criteria pass,
run `hub-session-review` for this task's current visible session before
clearing task context. Save and validate the review, then add
`Session review: ai/session-reviews/<file>.md` to the task so a closure retry
can reuse it; on a retry, reuse the recorded review instead of writing a new
one. A review-write failure leaves the task open and its context intact.
Partial history is recorded honestly and does not alone block closure. Do not
review the review or closure output again here. An improvement suggested by
the review is applied directly, reported, and is not a closure blocker.
