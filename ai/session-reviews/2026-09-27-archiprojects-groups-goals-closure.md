# Session review

Review ID: 2026-09-27-archiprojects-groups-goals-closure
Project ID: ai-dev-architecture
Task ID: TASK-ai-dev-architecture-20260927-003
Session ID: unavailable
Trigger: task-close
Coverage: complete
Evidence range: visible session span from "продолжи здесь этап 6" through the closure approval
Missing evidence: none
Chronology audit: every available message reviewed
Claim action audit: "все 30 промо-проектов" was stated before counting — unsupported, see F1; "CI зелёный" after gh pr checks pass; "хаб обновлён, данные перенесены" after update exit 0, migration `archiprojects: ok`, registry check passed, drift exit 0, goal progress printed; "выборка по SEO только SEO-проекты" after running `--group hadassah-seo`.
Prior review audit: read 2026-09-27-planning-calendar-modules-closure.md. Its F1 (relaying a claim without checking it) recurs here as F1 (count stated without checking), count 2 in the inspected set.
Result: issues-found
Supplements: none

## Goal and result

Goal: nested groups, goals in `ai/goals.md`, group column and filter, one-time
migration. Outcome: done; PR #12 merged after green CI; working Hub migrated
(aa23ba8) with 29 promo and 8 SEO projects; registry OK; drift 0.

## Findings

### F1
Observation: The assistant told the user there were 30 promo projects (16 linked + 14 unlinked); the real count was 29. The user chose option "1" based on that number.
Evidence: the question listed "14 похожих проектов"; the migration dry-run and reviewer counted 26 release-page cards + 2 stranitsa + promo-pages = 29; the assistant corrected the number before the migration was approved.
Cause: inferred
Root cause: the number was computed by eye from a listing instead of by a count command.
Impact: Low. The set the user chose was unchanged; only the stated number was wrong, and it was corrected before any write.

### F2
Observation: The controller verified several small fix rounds itself instead of dispatching a scoped re-review.
Evidence: Task 1, 2 and 3 fix rounds are marked "controller verified" in the plan ledger.
Cause: observed
Root cause: cost trade-off on small diffs.
Impact: Low; each diff was read in full or its behaviour checked on real data.

## Improvement proposals

### P1
Finding: F1
Scope: questions to the user that quote counts in this project.
Change: produce any count quoted to the user with a command (`ls | wc -l`, `grep -c`) in the same turn, and show the command's result, not an estimate.
Rationale: second occurrence of stating a number or effect without checking it (after 2026-09-27 planning-calendar F1).
Acceptance test: the next session review finds no count or effect stated to the user without a preceding command.
Recovery: drop the practice.
Disposition: proposed

## Follow-up

none
