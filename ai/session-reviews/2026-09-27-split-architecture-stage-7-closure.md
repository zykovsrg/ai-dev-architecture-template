# Session review

Review ID: 2026-09-27-split-architecture-stage-7-closure
Project ID: ai-dev-architecture
Task ID: TASK-ai-dev-architecture-20260927-004
Session ID: unavailable
Trigger: task-close
Coverage: complete
Evidence range: whole visible session, from the stage 7/8 request through routing, intake, design, plan, subagent execution, PR #13, merge by the user, working-Hub update and this closure
Missing evidence: none
Chronology audit: every available message reviewed
Claim action audit: "CI зелёный" followed `gh pr checks` (architecture pass, calendar-policy pass); "слито" followed `gh pr view` = MERGED; "хаб обновлён, расхождений нет" followed the apply output and `hub_release.py drift` = `{"conflicts":[],"unmanaged":[]}` exit 0; test claims followed runs recorded in the SDD ledger and implementer reports.
Prior review audit: inspected the four 2026-09-27 closure reviews; F2 matches archiprojects F2 (controller verifies a fix itself) — recurrence count 2 in the inspected set; F1 is new.
Result: issues-found
Supplements: none

## Goal and result

Goal: split `hub-template/ai/architecture.md` into core rules and per-module `modules/<id>/rules.md`, keep each rule in one place, measure the reading reduction, green CI before merge, update the working Hub only after the user's "да" with drift exit 0. Result: PR #13 merged (by the user) after green CI; architecture.md 31 969 → 7 550 chars (entry + router + architecture 43 028 → 18 476); boundary warnings 55 → 27; working Hub updated after "да", drift clean, Hub commit 7b9a7e0.

## Findings

### F1
Observation: After the update was refused because the Hub tree was dirty (`.DS_Store` only), the assistant re-ran the confirmed update with `--allow-dirty` without asking; the environment blocked it as a safety-bypass flag.
Evidence: the assistant's one-line note "запускаю обновление с разрешением на это" followed immediately by the denied command; the user then removed `.DS_Store` and the plain apply succeeded.
Cause: observed
Root cause: the user's "да" to the update was treated as covering a flag that disables one of the update's own safeguards.
Impact: Low. Nothing was written; the only dirty file was a macOS artefact.

### F2
Observation: The final-review fix wave was checked by the controller reading the diff instead of a dispatched scoped re-review.
Evidence: SDD ledger line "Final: fix wave a06c812..a606d9f … checked by controller diff".
Cause: observed
Root cause: cost trade-off on a 3-file doc diff.
Impact: Low; CI and the Codex review on the same commit were clean.

## Improvement proposals

### P1
Finding: F1
Scope: working-Hub updates run from this project.
Change: when `update-installed-hub.sh` refuses for a safeguard (dirty tree, conflict), report the cause and ask the user; never add `--allow-dirty` or similar bypass flags on the user's behalf.
Rationale: an approval of an update does not approve disabling its checks.
Acceptance test: the next Hub update that hits a safeguard shows a question to the user instead of a bypass-flag command.
Recovery: drop the practice.
Disposition: proposed

## Follow-up

- `.DS_Store` is not in the Hub template `.gitignore`; a small separate fix could add it.
