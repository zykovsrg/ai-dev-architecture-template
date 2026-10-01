# Session review

Review ID: 2026-10-01-architecture-audit-closure
Project ID: ai-dev-architecture
Task ID: TASK-ai-dev-architecture-20261001-002
Session ID: unavailable
Trigger: task-close
Coverage: complete
Evidence range: visible session from the audit request ("проведи полный и детальный аудит") to "закрывай задачу"
Missing evidence: none
Chronology audit: every available message reviewed
Claim action audit: "все тесты проходят" — preceded by unittest/architecture/consistency runs each time; "исходники и хаб совпадают" — preceded by `update-installed-hub.sh --check` reporting match; "скрипт обслуживает другой проект, удалить" — made without checking live automations, later disproved by the PR #18 review; "#17 и #18 слиты" — preceded by `gh pr merge` returning MERGED and green checks on the head commit.
Prior review audit: indexed 2026-09-27..2026-10-01 closures; F1 recurs the mechanism of 2026-10-01-legacy-project-cleanup-closure F2 (classifying a file as dead without checking its live users) — 2 occurrences in the inspected set; P1 below extends that review's P1 rather than adding a new rule.
Result: issues-found
Supplements: none

## Goal and result

Goal: full architecture audit — dead code, tech debt, self-learning and its
automation — with proposals, changes only after the user's choice. Result:
report `docs/audits/2026-10-01-architecture-audit.md`; by user choice: sources
synced with the hub (PR #17, merged), cleanup (PR #18, merged), calendar drift
learning and open-proposal review (PR #19, open, CI pending).

## Findings

### F1
Observation: The audit and PR #18 removed `scripts/refresh-session-inventory.sh` as dead code; Codex review showed a live session-audit automation still calls it.
Evidence: PR #18 review comment (P1); `.codex` global state references the script; the script was restored in 14e7784 before merge.
Cause: observed
Root cause: "referenced only by its own test" was taken as proof of no use; external schedulers were not checked.
Impact: Low; caught before merge.

### F2
Observation: The first version of `calendar_drift.py` keyed events by title and skipped duration after a move; Codex review found both.
Evidence: PR #19 review comments (two P2); fixed with tests in the follow-up commit.
Cause: observed
Root cause: tests covered only unique titles and single-change events.
Impact: Low; fixed before merge.

## Improvement proposals

### P1
Finding: F1
Scope: dead-code removal in this project.
Change: before calling a script dead, also search external schedulers (Codex automations, launchd, crontab, app scheduled tasks) for its name.
Rationale: second occurrence of classifying by repository references alone.
Acceptance test: the next dead-code proposal lists the scheduler search it ran.
Recovery: drop the practice.
Disposition: accepted

## Follow-up

- Merge PR #19 after CI, then update the working hub.
