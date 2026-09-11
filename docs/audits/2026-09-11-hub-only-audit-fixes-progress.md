# 2026-09-11 Hub-Only Audit Fixes — Progress

Specification: `docs/superpowers/specs/2026-09-11-hub-only-audit-fixes-design.md`
Plan: `docs/superpowers/plans/2026-09-11-hub-only-audit-fixes.md`
Branch: `audit/hub-only-fixes-2026-09-11`
Base main SHA: `2a172790e6d45ab33aced3b4f14e9a310493e02f`
Execution environment: GitHub branch + GitHub Actions (the requested local repository path is unavailable in this session).

## Baseline

- CI workflow commits: `e753004869b82b31dbbc4980b54120e25d07f68a`, Linux temp-path fixes `86c4a3557aa7b62a66bc002d31d18e1c1c339b93` and `55ebc5d3c5ac9d776895e76205e5289e119a2b87`.
- Primary baseline workflow run: `34586554005`.
- `scripts/check-consistency.sh`: PASS.
- `scripts/hub-smoke-test.sh`: FAIL — `hub-template/AGENTS.md` exceeds the existing smoke-test size limit. Classified as a pre-existing architecture/context issue to reconcile in the approved Hub-only consolidation, not a Task 1 regression.
- `tests/test_task_records.py`: PASS inside the 34-test architecture unit run.
- `tests/test_workflow_friction.py`: PASS inside the 34-test architecture unit run.
- `tests/test_hub_release.py`: PASS inside the 34-test architecture unit run.
- Calendar policy including `tests/test_evening_review.py`: PASS; `calendar-policy` job succeeded in run `34586554005`.
- `scripts/assistant-workflows-test.sh`: PASS.
- Entire repository Python unit suite: PASS, 34 tests.
- Additional `scripts/architecture-test.sh`: FAIL after its Python unit phase because `scripts/lib/calendar-date.sh` uses macOS `date -j`; GNU `date` on the standard Linux runner rejects even the valid fixture date. Classified as an environmental portability issue outside Task 1; it must be addressed before final Task 9 acceptance rather than treated as a product RED.
- Earlier run `34586399552` proved the original `/private/tmp` failure was CI setup, not product behavior; workflow setup now creates `/private/tmp` with mode 1777.

## Task 1

- State: ready for RED.
