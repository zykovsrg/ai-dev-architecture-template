# Session review

Review ID: SR-20260918-skipped-heading-warnings-closure
Project ID: ai-dev-architecture
Task ID: TASK-ai-dev-architecture-20260915-002
Session ID: unavailable
Trigger: task-close
Coverage: partial
Evidence range: visible conversation of 2026-09-18, from the day-plan request through this closure. The implementing work happened on 2026-09-15 in a session not visible here.
Missing evidence: the 2026-09-15 implementation session in which the warnings, the strict check and the format documentation were written and verified.
Chronology audit: partial; every message of the visible 2026-09-18 span was reviewed in order. The 2026-09-15 implementation span was omitted because it is not available.
Claim action audit: the task's recorded claim «106 unit tests and all shell tests passed; release manifest check passed» has no visible preceding action in this span and is carried from the task record, not verified here. In the visible span, the closure claim rests on `check-all-task-records.sh --hub .` returning OK on 2026-09-18, which is evidence that the delivered strict check runs clean, not that the 2026-09-15 test run occurred. The visible span independently confirms the delivered behaviour once: the 2026-09-18 day plan produced no skipped-heading warnings and the compact index ran without stderr warnings.
Prior review audit: inspected the seven records in `ai/session-reviews/`. F1 below repeats the mechanism of REVIEW-20260910-refactor-closure F2 (completion reported beyond the checks actually run); recurrence count 2 in the inspected set. No proposal was reused; REVIEW-20260910-refactor-closure P2 addressed claim wording, not validator invocation.
Result: issues-found
Supplements: none

## Goal and result

Goal: stop task discovery from silently skipping task records whose headings do
not match the machine-read format, and document that format.

Expected result: the compact task index warns on stderr for every skipped `###`
heading; `check-all-task-records.sh` fails on skipped headings; `hub-workflows`
requires surfacing those warnings to the user; `task-record-format.md`
documents future and paused heading formats; tests cover all of it.

Observed outcome: delivered. In the visible span the compact index ran with no
stderr warnings, the day plan of 2026-09-18 reported none, and the strict check
passed across all 66 registered projects. The task record reports the full test
run from the 2026-09-15 session, which this review cannot verify directly.

## Findings

### F1
Observation: The strict record check delivered by this task was not invoked by
any workflow, so a non-canonical record produced by a confirmed write survived
undetected for most of the working day.
Evidence: On 2026-09-18 a confirmed day-plan package set `Status: empty` in
`hadassah-seo-audits/ai/current-task.md` and `housing-search/ai/current-task.md`
while leaving their `Task ID:` lines in place. Both records stayed invalid until
`check-all-task-records.sh --hub .` was run hours later for an unrelated reason
and reported `invalid_status` for both. A search of `ai/skills/` at that moment
found no reference to `check-all-task-records.sh` in any skill text.
Cause: inferred
Root cause: the task delivered a strict checker but did not wire it into the
workflows that write task records. `hub-workflows` mandates
`validate-day-plan-output.py` before showing a day plan and mandated no
equivalent check after applying task-record writes.
Impact: The guarantee the task was meant to provide was available but unused on
the write path. Two canonical records were briefly wrong and a completion was
reported without the one check that would have caught it. Repaired in the same
session; both files now pass.

## Improvement proposals

### P1
Finding: F1
Scope: `hub-workflows` task-record write path
Change: After applying any confirmed task-record write, run
`scripts/check-all-task-records.sh --hub <hub>`, report its result, repair a
failure in the same reply, and never report a task write as complete without
that passing check.
Rationale: The checker already exists, is already tested and already fails
correctly. Only its invocation was missing, so this adds no new code path. A
Git hook was considered and rejected: `projects/` is excluded from the hub
repository and each project is a separate repository, which would require and
maintain 66 hooks.
Acceptance test: A task-record write that leaves `Status: empty` beside a
populated `Task ID:` is reported as a failure in the same reply that applied it.
Recovery: Remove the added paragraph from `ai/skills/hub-workflows/SKILL.md`;
no code or data changes accompany it.
Disposition: implemented

## Follow-up

The recurrence noted in the prior review audit is about reporting completion
beyond the checks actually run. P1 closes the task-record instance of it. The
general form is not addressed here and no rule is proposed for it, because two
instances with different surfaces do not yet justify a shared rule.
