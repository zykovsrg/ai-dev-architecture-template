# Release reconciliation — Implementation Plan

> Superseded by R01 in [the complete implementation plan](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-complete.md). The new plan covers actual implementation through final acceptance; this older reconciliation-only assignment is retained for history and must not trigger an unnecessary return to Astra.

> **For agentic workers:** Use superpowers:executing-plans. Execute sequentially on Terra after the user's model switch. Do not dispatch additional agents by default.

**Goal:** Produce a complete, verified inventory of live/distribution divergence and an exact release-preservation manifest before changing the updater or deploying a release.

**Architecture:** The live hub contains changes absent from the distribution. Reconciliation must precede copying. This first package produces the evidence and file map needed for safe code changes; it is not the full refactoring.

**Tech Stack:** Git, existing Bash tools, Markdown manifest; no dependencies or external writes.

## Global constraints

Use [the approved programme specification](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/specs/2026-09-09-hub-refactor-design.md). Preserve all user changes. Do not run updater apply, modify runtime rules or read application code in this first package. Do not assume a newly discovered difference is disposable. On completion return to Astra for the next implementation mini-plan.

## Task 1: Record baseline

Files read: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/architecture.md`, `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/hub-template/ai/architecture.md`, and Git metadata in both repositories.

- [ ] Run:

```bash
git -C /Users/zykovsrg/Documents/vibecode/_ai-hub status --short
git -C /Users/zykovsrg/Documents/vibecode/_ai-hub rev-parse HEAD
git -C /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture status --short
git -C /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture rev-parse HEAD
```

Expected: actual hashes and dirty-file lists. Existing changes are a baseline, not a failure. Do not reset or commit unrelated files. Record command failures rather than substituting old hashes.

## Task 2: Build the exact preservation manifest

Read `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/scripts/update-installed-hub.sh` completely, following only the source-file enumeration and readonly preview dependencies. Read the complete dry-run output, paginating if necessary; never infer that a truncated output is complete.

- [ ] Run:

```bash
bash /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/scripts/update-installed-hub.sh --dry-run --hub /Users/zykovsrg/Documents/vibecode/_ai-hub --source /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture
```

Expected: differences, no apply. If a dry-run dependency fails, inspect that dependency before rerunning; do not install it or switch to apply to get output.

- [ ] Compare live shared skill resources and scripts against the updater's explicit file list. Include live files absent from the list; a dry-run cannot list a file it does not manage. Restrict reads to architecture code and shared procedures.
- [ ] Create `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/audits/2026-09-09-release-preservation-manifest.md` with `apply_patch`. Use this structure, filling every row from actual files:

```markdown
# Release preservation manifest

## Baseline

Hub commit and dirty files; distribution commit and dirty files; inspection date.

## File decisions

| Live absolute path | Distribution absolute path | Current hashes | Decision | Behavior to preserve | Verification |
| --- | --- | --- | --- | --- | --- |

## Unresolved differences

Evidence and the exact decision required, or an explicit statement that none remain.

## Readiness

Whether each acceptance condition below is met; this is release planning, not deployment.
```

Decisions are `preserve-live`, `preserve-distribution`, `merge`, or `needs-design`. `needs-design` is a visible blocker for that item, not permission to guess. Enumerate actual files, not a single wildcard or whole-directory deletion. Do not record private task contents or credentials.

## Task 3: Verify coverage and hand off

- [ ] Confirm the manifest covers goal progress, existing task/calendar learning and its scripts/tests, active-project preservation, calendar naming and permissions, new-board support, shared resources and `.gitignore` preview/commit coverage.
- [ ] For each difference, cite a source and a concrete behavioral test expectation. The plan must preserve the existing task/calendar learner while its cache bugs are fixed later.
- [ ] Cross-check every updater-managed difference and every additional live feature against a manifest row. No omitted difference is implicitly approved for removal.
- [ ] Run `git -C /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture diff --check`; additionally inspect the new untracked Markdown document for malformed rows and wrong paths.
- [ ] Return a short report: manifest path, unresolved items, preserved behaviors, and readiness for the next Astra plan. Do not report runtime defects fixed or release deployed.

The deliverable is intentionally one bounded preparation task for Terra. Luna is not assigned semantic reconciliation. Once this manifest exists, Astra can prepare exact code-and-test patches for updater safety, the snapshot/date defects, task/calendar consistency, standalone migration and closure review without guessing file ownership.
