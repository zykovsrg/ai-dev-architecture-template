# Session review

Review ID: SR-20260927-modular-architecture-steps-1-2-closure
Project ID: ai-dev-architecture
Task ID: TASK-ai-dev-architecture-20260926-001
Session ID: unavailable
Trigger: task-close
Coverage: complete
Evidence range: current visible session, from «открой проект ии-архитектура» (2026-09-26) through the closure request after the phase-order agreement (2026-09-27)
Missing evidence: none
Chronology audit: every available message reviewed (project open, planning-split advice, full audit, re-verification, task intake, brainstorming Q&A, spec, plan, subagent execution of Tasks 1–5 and 7 with reviews, final review and fix wave, user check of fresher skills, Hub update, memory close-out, merge/push, CI failure and fix, reorder of phases)
Claim action audit: audit claim "docs reference the removed template/ directory" had no supporting action beyond a substring grep that also matched `hub-template/` (F1); "мост никем не используется" followed the removal instead of preceding it (F2); "Все тесты проходят" was supported by local runs only, while the moved Hub tests had never run on the CI Linux runner, and CI later failed on main (F3); "хаб обновлён" followed the apply result and `drift` exit 0; "свежее нигде нет" followed a disk-wide search, worktree and branch checks; "ветка влита и отправлена" followed the fast-forward and push output.
Prior review audit: compact index of 14 prior reviews; read SR-20260921-calendar-task-sync-closure and SR-20260918-skipped-heading-warnings-closure (write-path checks) and the 2026-08-31 decision in `ai/decisions.md` (removed rule restored without asking). F2 recurs the 2026-08-31 mechanism (a rule-backed artifact changed without first consulting recorded decisions): 2 occurrences in the inspected set. F4 is related to SR-20260918 (write not followed by the canonical check). F1 and F3 are new.
Result: issues-found
Supplements: none

## Goal and result

Goal: move to a modular architecture; in this task write the spec and plan, bring Hub-only code back into the repository with a drift check, and remove dead code. Result: spec and plan approved; branch `modular-steps-1-2` (519b7d3..b8b6220) merged to `main` and pushed; Hub updated with `drift` exit 0; about 18.6k dead lines removed; CI green after one test fix (0ccd68c). Phases 4–8 recorded as future tasks; the user reordered them so that phase 4 starts with Obsidian as the first switchable module.

## Findings

### F1
Observation: The audit stated as fact that five docs referenced the removed `template/` directory; there were no such references.
Evidence: the audit used `grep -c "template/"`, which counts `hub-template/`; the Task 7 implementer and reviewer found only `hub-template/` hits.
Cause: inferred
Root cause: a substring search was reported as a verified finding without checking one hit.
Impact: Low. It added one unnecessary plan step; the correction was reported to the user.

### F2
Observation: The legacy Obsidian bridge installer was removed while an active decision (2026-08-29) in `ai/decisions.md` still described it; the decision was found only afterwards.
Evidence: Task 5 grep covered code and docs but not `ai/decisions.md`; during close-out the controller found the active decision, then verified that 0 of 71 projects carry the bridge block and marked the decision superseded.
Cause: inferred
Root cause: the dead-code check looked for code references, not for recorded decisions that require the code.
Impact: Low. The removal turned out safe and is reversible in git, but the order was wrong: evidence came after the change.

### F3
Observation: The branch was merged to `main` before CI had ever run the newly moved tests; CI then failed on `main`.
Evidence: the final reviewer recommended pushing and checking CI before merge; the assistant proposed "влить и отправить" in one step; CI run 36295566887 failed on `test-count-goal-progress.sh` (missing `de_DE.UTF-8` on the runner); fixed in 0ccd68c, run 36295736365 green.
Cause: inferred
Root cause: the reviewer's recommendation was not carried into the question put to the user.
Impact: Low. `main` was red for about three minutes; the script itself was correct.

### F4
Observation: A future-task entry was written with an invalid status line (`Status: promoted — …`) and not checked right after the write.
Evidence: `check-all-task-records.sh` reported `invalid_status` only when it ran as part of the Hub update the next day.
Cause: inferred
Root cause: the canonical check was not run immediately after a task-memory write, as `hub-workflows` requires.
Impact: Low. Caught before commit and fixed.

## Improvement proposals

### P1
Finding: F2
Scope: dead-code removal steps in future architecture plans in this project (next: FT-20260926-005).
Change: before removing a file, also grep `ai/decisions.md` for its name or feature; if an active decision refers to it, ask the user or mark the decision superseded with evidence in the same change.
Rationale: the same mechanism (changing a rule-backed artifact before consulting recorded decisions) occurred on 2026-09-01 and again here.
Acceptance test: the next plan that removes files lists a decisions grep per removal, and its review finds no active decision describing a removed file.
Recovery: restore the file from git and set the decision back to active.
Disposition: proposed

## Follow-up

none
