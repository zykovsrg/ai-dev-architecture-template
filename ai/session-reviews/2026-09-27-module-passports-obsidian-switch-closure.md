# Session review

Review ID: 2026-09-27-module-passports-obsidian-switch-closure
Project ID: ai-dev-architecture
Task ID: TASK-ai-dev-architecture-20260927-001
Session ID: unavailable
Trigger: task-close
Coverage: complete
Evidence range: the whole visible session from the user's request to open ai-dev-architecture through the closure approval (routing, brainstorming, spec section, plan, six subagent tasks with reviews, final review, merge, Hub update, memory writes)
Missing evidence: none
Chronology audit: every available message reviewed; no compaction occurred
Claim action audit: "спецификация закоммичена" after commit 06405cc; "план готов" after commit 1c10024; "все тесты зелёные" after architecture-test unit=0 and the known /tmp symlink integration failure, stated with that exception; "слито и отправлено" after push of 2738139; "проверки на GitHub прошли" after gh run 36305674617 success; "Obsidian выключен, drift 0" after apply, drift exit 0, check-all-task-records OK; "коммит с памятью на GitHub" after push. Unsupported claims found in subagent reports, see F1.
Prior review audit: inspected the compact index of all 9 reviews and read 2026-09-27-modular-architecture-steps-1-2-closure.md (same task line). P1 (decisions grep before removal) was applied: plan Task 3 step 1 and the Obsidian decision were handled before the change. F3 of that review recurs here (merge before CI), count 2 in the inspected set.
Result: issues-found
Supplements: none

## Goal and result

Goal: stage 4 of the modular architecture — passports for all modules,
generated `ai/modules.md`, boundary check in warning mode, Obsidian as the first
switchable module, disabled in the working Hub, drift exit 0, tests and CI green.
Outcome: all done criteria met. Branch merged as 0999536..2738139, CI green,
Hub commits 406b01c and 15520e1 (local, not pushed), memory commit 8d27123 pushed.

## Findings

### F1
Observation: Two regressions introduced in Task 2 were reported as "unchanged from baseline" or "pre-existing" by later implementers and were caught by the controller only at the end: `tests/test_hub_update_check.sh` (missing `hub-template/projects/.gitkeep`) and the `check-consistency.sh` "compact task index" MISMATCH that would have failed CI.
Evidence: the Task 2 report claimed test_hub_update_check exit 0; the Task 3 report called its failure pre-existing; Tasks 3 and 4 compared check-consistency against the previous task's HEAD; the controller compared against a clean worktree of base 1c10024 and found the new MISMATCH.
Cause: inferred
Root cause: per-task baselines were taken at the previous task's HEAD, not at the branch base, so an earlier task's regression became the new "baseline".
Impact: Low. Both were fixed before merge (d4f45ad, 2738139); CI was green.

### F2
Observation: The branch was merged to `main` and pushed before CI had run on it.
Evidence: after user approval the controller ran merge and push in one step; CI run 36305674617 then ran on `main` (green).
Cause: inferred
Root cause: the plan's Task 7 said to merge and push, then check CI; the prior review's F3 lesson was not turned into a plan step.
Impact: Low this time (CI green), but a failing run would have left `main` red again.

### F3
Observation: The controller skipped the scoped re-review for two tiny fix rounds and verified the diffs itself.
Evidence: Task 1 fix round 1 (2-line passport edit) and Task 2 fix round 2 (one-line `add -f`), recorded in the ledger as controller-verified.
Cause: observed
Root cause: cost trade-off on trivial diffs.
Impact: Low; both diffs were read in full.

## Improvement proposals

### P1
Finding: F1, F2
Scope: future multi-task plans executed with subagents in this project (next: FT-20260926-002).
Change: (a) implementers compare test and consistency output against the branch base commit, not the previous task's HEAD; (b) the closing task pushes the feature branch and waits for CI before merging to `main`.
Rationale: F2 repeats F3 of the 2026-09-27 steps 1–2 review (count 2); F1 shows the relative baseline hides regressions.
Acceptance test: the next plan's briefs name the base commit as baseline, and its CI run precedes the merge commit on `main`.
Recovery: drop the two plan lines.
Disposition: proposed

## Follow-up

Hub commits 406b01c and 15520e1 are local; pushing `personal-ai-hub` awaits user approval.
