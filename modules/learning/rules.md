# Learning Module Rules

## Hub-Managed Project Flow

- `hub-session-review` — reviews a completed task's current session or an
  explicitly selected session. Reviews live only in the selected project's
  `ai/session-reviews/`; improvements the review finds are applied directly
  and reported; removing an existing rule waits for an explicit yes.
- `hub-session-scan` — scans new Claude Code and Codex sessions into the
  learning catalog with a cheap model and runs the weekly merge pass; removing
  a catalog rule waits for an explicit yes.

## Self-Learning Workflows

`ai/workflow-observations.md` is the canonical append-only journal of workflow
friction and calendar drift. Rule maturity is computed only by `scripts/session_rules.py` (see
`## Session learning`). Accepted observations are fed to the next session scan
as input; removing a catalog rule needs an explicit yes.

`ai/tmp/calendar-snapshots/` and `ai/tmp/workflow-friction/` are non-canonical
caches, written directly and pruned after 14 days.
`scripts/check-workflow-memory.sh` validates the two canonical learning files.
These workflows remain independent of `hub-session-review`: a session review
supplies improvement proposals but never automatically changes a rule or
consumes a pending observation.

## Open review proposals

The weekly review may read, across active registered projects, only the
`## Improvement proposals` sections of `ai/session-reviews/*.md`, through
`python3 scripts/review_proposals.py --hub <hub> list --until <date>`. Apart from the
`## Findings` read by the session scan (see `## Session learning`), this is the
only cross-project read of session reviews; evidence and other review text stay
project-scoped.

Show each open proposal (project, review, ID, change, age) and ask the user to
accept, reject or skip it. Record the answer with
`python3 scripts/review_proposals.py --hub <hub> set --project <id> --review <path> --proposal <ID> --decision <accepted|rejected>`;
the script rewrites only that proposal's `Disposition:` line. An accepted
proposal also gets a future-task entry in that project's `ai/future-tasks.md`
(the personal-assistant task-record write scope), unless an entry for the same
review and proposal already exists. Skipping changes nothing. When the work for
an accepted proposal is done in its project, set `--decision implemented`.

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

## Session learning

`hub-session-scan` scans new Claude Code and Codex Hub sessions with a cheap
model (Haiku 4.5 or GPT-6-Luna) and writes cases to `ai/learning/rules.json`.
`scripts/session_rules.py` alone computes confidence and scope and renders
`ai/learned-rules.md` and `ai/learned-rules/<project-id>.md`. Each scan also
passes new entries of `ai/workflow-observations.md` and the `## Findings`
section of new session reviews in active registered projects to the scanner
as extra sessions (`obs-<n>`, `review-<project>-<file>`), tracked in the same
ledger. The weekly review runs the weekly pass. The scan may also read the
`## Findings` section of session reviews in active registered projects.
