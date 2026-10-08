# Learning Module Rules

## Hub-Managed Project Flow

- `hub-session-review` — on the user's request only, reviews an explicitly
  selected session of a confirmed project. Reviews live only in the selected project's
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

## Task closure

Task closure does not run a session review. Sessions, including the ones that
closed tasks, are learned from by `hub-session-scan`; this avoids reviewing
the same session twice. `hub-session-review` runs only when the user asks for
it for a confirmed project and an explicit session or range.

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

## Rule home

This section is the only description of the mechanism (user decisions
2026-10-08); the weekly review and the scan skill point here.

Limits. `ai/learned-rules.md` holds at most 30 global rules; per-project
rule files have no count limit. Every `ai/skills/**/*.md`, `ai/rules/*.md`
and learned-rules file stays within 300 lines:
`python3 scripts/session_rules.py --hub <hub> check-limits` lists files over
the limit, and the weekly review offers to compress or split them. The
catalog `ai/learning/rules.json` has no archive: the assistant never reads
it, and the scanner gets at most 60 rules.

Waiting room. A learned rule is not a permanent home. A rule that belongs to
one workflow lives in that workflow's skill or module rules file. The weekly
review analyses every injected rule on its own, without being asked:
- the owning file already states it → offer to retire it, citing the exact
  line; prove the line with
  `session_rules.py --hub <hub> check-home --file <hub-relative path> --quote "<line>"`;
- it belongs to one workflow but the file does not state it → offer to add
  it there, then retire it;
- at least 3 rules describe one process that has no fitting skill, and their
  cases come from at least 3 distinct sessions → offer a new skill; first
  compare its description with existing skill descriptions and prefer
  extending an existing skill;
- it is about work in general → it stays in `ai/learned-rules.md`.
A rule that applies across projects never moves into one project's skill.
Project skill files are outside the weekly review's read scope: a move into
a project skill is checked when that project is confirmed.
Every edit of a skill or rules file, every new skill (built through
`superpowers:writing-skills`) and every retirement waits for the user's
explicit yes. Retire with `--note "moved to <file>"` so the catalog keeps
where the rule went.

Duplicates and leaks (`session_rules.py apply`). A new rule that repeats
`CLAUDE.md` or `AGENTS.md` is dropped (`skipped_standing`). A new rule that
repeats a rule retired with `moved to` is not added again: it is recorded as
a `leak` case on the moved rule (`leaks` in the apply output). A leak never
changes confidence or re-activates the rule; it means the skill did not do
its job, and the weekly review offers to fix that skill.
