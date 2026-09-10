# Architecture refactor handoff

## User intent and decisions

- Audit the architecture, registered projects and their future tasks, but not
  application implementation or application user scenarios.
- Centralize generic standalone project rules in the hub; remove duplication
  and unnecessary mechanisms while preserving project-specific memory.
- Preserve existing task/calendar learning, goal tracking and weekly learning.
  Add session review at task closure and for a user-selected session on request.
  Improvements require user approval; a review never authorizes a rule change.
- Do not use Codex scheduled automation for architectural self-learning.
  Removal of any previously configured automation is not evidenced here.
- Use Astra for design/planning, Terra or Luna for implementation and economical
  review. Do not claim a model switch unless it actually occurred.
- The user declined further regression checks after deployment and requested
  closure. Do not interpret that as evidence that unrun tests passed.

## Recorded implementation and deployment

Branch `codex/hub-refactor` was merged into main at fbd4c1d. Work included
content-based release checks, task date/record validation, snapshot collision
protection, pending-friction handling, compact project entries, session review
templates/validation and task-close instructions. Earlier conversation summary
reports 66 compact entry files across 33 projects and 33 architecture pointers;
these counts were not independently rechecked during memory capture.

Live-rule reconciliation followed in 2fec384, 2a8837d and 37d44f2; manifest
commit d40ab25. Deployment used `update-installed-hub.sh --apply --allow-dirty`,
not `hub_release.py apply`. The first attempt failed on compiler cache access;
the escalated retry succeeded and rebuilt the Calendar bridge. It did not
request Calendar access or change the calendar allowlist according to output.
No remote push is evidenced. Source changes are in local main; installed hub
changes and older audit/planning documents were not all committed in this work.

## Verification limits and unresolved concerns

The visible run passed 33 Python unit tests before the final closure-order test
was added. Five focused tests then passed. Post-install checks confirmed task
record validity and selected rule strings. These are not end-to-end proof.
The long Obsidian integration test did not yield a successful full completion;
earlier claims of a fixture hang were not established. Timed traces showed
progress into transaction scenarios. Further regression checking was declined.

The merge was described as preserving the full learning mechanism, but its
tests largely check string presence. The installed workflow has contradictory
instructions: pending observations must not be consumed by presentation, yet
the appended lifecycle says evening review marks friction consumed. It also
retains output/action schemas lacking some of the appended learning actions.
The deployment diff removed detailed goal and calendar instructions; complete
semantic preservation is therefore not established. These are visible-text
concerns, not a new regression test result. Do not silently fix or call them
verified preservation during a later handoff.

The date batching change ea85bd5 also lacks full integration confirmation.
Do not infer correctness for multiple task due dates from its one-date test.

## Documents

- Audit: `docs/audits/2026-09-09-architecture-audit.md` and companion details,
  project inventory and service inventory in that directory.
- Original design: `docs/superpowers/specs/2026-09-09-hub-refactor-design.md`.
- Original plans: `docs/superpowers/plans/2026-09-09-refactor-complete.md`
  and the release/tasks/migration/learning package plans in that directory.
- Low-cost review: `docs/superpowers/specs/2026-09-09-low-cost-session-review-design.md`
  and its matching plan.
- Live merge: `docs/superpowers/specs/2026-09-10-live-hub-merge-design.md`
  and `docs/superpowers/plans/2026-09-10-live-hub-merge.md`.
- Closure review: `ai/session-reviews/2026-09-10-refactor-closure.md`.

## Closure

The user requested closure despite declining further verification. The existing
current-task record was already an empty template; no historical task ID is
invented. This handoff records the delivered work and remaining uncertainty.
Review findings are proposals only, not new approved implementation tasks.
