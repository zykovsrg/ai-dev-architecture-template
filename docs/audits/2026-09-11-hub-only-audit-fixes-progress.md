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
- `scripts/hub-smoke-test.sh`: FAIL — `hub-template/AGENTS.md` exceeds the existing smoke-test size limit. Classified as a pre-existing architecture/context issue to reconcile in the approved Hub-only consolidation.
- `tests/test_task_records.py`, `tests/test_workflow_friction.py`, `tests/test_hub_release.py`: PASS inside the 34-test architecture unit run.
- Calendar policy including evening review: PASS in baseline.
- `scripts/assistant-workflows-test.sh`: PASS.
- Entire repository Python unit suite: PASS, 34 tests.
- Additional `scripts/architecture-test.sh`: FAIL after its Python unit phase because `scripts/lib/calendar-date.sh` uses macOS `date -j`; GNU `date` rejects the valid fixture date. Classified as a pre-existing Linux portability issue to resolve before final acceptance.
- Earlier run `34586399552` proved the original `/private/tmp` failure was CI setup; workflow setup now creates `/private/tmp` with mode 1777.

## Task 1 — Evening-review friction state

- State: complete.
- RED commit: `6106134e549e4fc33c4949a38799de234e10a51a`.
- RED workflow run: `34586657860`; calendar-policy failed exactly because accepted/rejected observations were still returned as pending and invalid `.state.json` was ignored (`4 failed, 91 passed`).
- GREEN commit: `341b2c8ddcfa4fd93f04085f67c37e6d11dcb250`.
- GREEN workflow run: `34586758742`; calendar-policy job PASS, architecture Python unit suite PASS, assistant-workflows PASS. Overall workflow remains red only on the two recorded baseline issues.
- Changed files: `calendar-policy/tests/test_evening_review.py`, `calendar-policy/src/hub_calendar_policy/evening_review.py`.
- Tests actually run: full calendar-policy pytest suite; repository Python unittest suite; consistency, Hub smoke, architecture smoke, assistant-workflows via CI.
- Result: evening review now uses the same observation ID/disposition state semantics as `workflow_friction.py`; accepted/rejected entries are excluded, pending entries remain, malformed state is rejected.
- Remaining risks: duplicated state parsing logic can drift in the future; no cross-package import was introduced to avoid coupling calendar-policy to repository scripts.
- Next Task: Task 2 — unify learning lifecycle and proposal action vocabulary.
