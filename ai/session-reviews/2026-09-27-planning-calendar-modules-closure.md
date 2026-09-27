# Session review

Review ID: 2026-09-27-planning-calendar-modules-closure
Project ID: ai-dev-architecture
Task ID: TASK-ai-dev-architecture-20260927-002
Session ID: unavailable
Trigger: task-close
Coverage: complete
Evidence range: visible session span from the user's "Делаем шаг №5" through the closure approval, including the usage-limit pause and "Продолжаем"
Missing evidence: none
Chronology audit: every available message reviewed
Claim action audit: "коммиты хаба отправлены" after push; "мелочи исправлены" after exclude edit, trash move and check-consistency 0 MISMATCH; "задачи 1–6 проверены" after task reviews; "CI зелёный" after gh pr checks pass; "хаб обновлён, drift 0" after apply, drift exit 0, record check OK; the pre-update claim ".mcp.json станет 0600" was unsupported, see F1.
Prior review audit: read 2026-09-27-module-passports-obsidian-switch-closure.md (same task line). Its F2/P1 mechanism (merge before CI) did not recur: CI ran on PR #11 before merge. Its F1 mechanism (relative baselines) did not recur: briefs named the branch base.
Result: issues-found
Supplements: none

## Goal and result

Goal: stage 5 — planning and calendar become switchable modules, task skills
use events, the calendar server is calendar-only, capture and overview work
without planning. Outcome: done; PR #11 merged after green CI; working Hub
updated (6cdea19) with both modules on; drift 0.

## Findings

### F1
Observation: Before the Hub update the assistant told the user `.mcp.json` would become mode 0600; the update did not rewrite the file, so the mode stayed 644.
Evidence: the final reviewer's triage said the rewrite gives 0600; after apply, `ls -l .mcp.json` showed `-rw-r--r--`; the assistant corrected the statement in its next report.
Cause: inferred
Root cause: a reviewer's conditional remark was relayed as a certain outcome without checking whether the rewrite path would run.
Impact: Low; corrected before the user acted on it.

### F2
Observation: The plan's Task 6 did not require the preview to announce the calendar server refresh that runs on every apply; the task review caught it.
Evidence: Task 6 review Important 1; fixed in 13d35fe with a test for the unchanged-selection preview.
Cause: inferred
Root cause: the plan described extra steps only for membership changes and not for side effects that run on every apply.
Impact: Low; caught before merge.

## Improvement proposals

none

## Follow-up

none
