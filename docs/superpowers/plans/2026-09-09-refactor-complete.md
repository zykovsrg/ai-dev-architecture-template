# Complete Hub Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans`, one task at a time. Implementation uses Terra, with the specifically marked tasks available to Luna. No automatic subagent dispatch. Checkboxes track execution, not planning completion.

**Goal:** Correct the confirmed architecture defects, consolidate standalone projects into the hub, preserve task/calendar learning, and implement semantic review at every task closure and on explicit session requests.

**Architecture:** One distribution source deploys verified shared procedures to the hub. Project-specific memory and session reviews stay local. Calendar changes retain the existing guarded confirmation path. Semantic review proposes improvements; confirmation authorizes implementation.

**Tech Stack:** Existing Bash 3.2, Git, jq, Markdown, Python 3 standard library; existing calendar-policy environment for its tests. No additional service, database or scheduled model worker.

## Global Constraints

- Authoritative specification: [2026-09-09-hub-refactor-design.md](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/specs/2026-09-09-hub-refactor-design.md).
- User authorized the programme. Planning is on Astra; implementation begins only after the user switches to Terra/Luna. Do not execute code blocks during planning.
- Do not test or modify application internals. Project task memory and architecture resources are in scope.
- Preserve existing task/calendar learning, goal progress, calendar title rules and current permissions, project-selection preservation, and new-project board support.
- Every task closure gets an AI review, including a clean/partial review where appropriate. No background sampling replaces closure review.
- Shared-rule improvements discovered during learning require user approval. Recording a review does not authorize that improvement.
- Access remains limited to registered projects under the confirmed hub. Use the registry's exact paths. No new permission prompts for already authorized reads or routine implementation.
- Existing uncommitted changes belong to the user. Never reset, stash or commit them wholesale.
- No runtime implementation or automation deletion was performed while writing this plan. Code and tests below are instructions for the implementation model, not verified finished software.

## Complete execution order

| Part | Tasks | Model | Deliverable |
| --- | --- | --- | --- |
| [1. Release and preservation](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-01-release.md) | R01–R06 | Terra; R04 may use Luna | Reconciled source, safe update, cache/date defects fixed, reproducible tests |
| [2. Task records and calendar](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-02-tasks.md) | T01–T05 | Terra; approved record edits may use Luna | Compatible parsing, no silent loss, dated changes use joint confirmation |
| [3. Hub-only migration](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-03-migration.md) | M01–M06 | Terra; M04 may use Luna | Custom resources preserved, all registered projects reconciled, standalone retired |
| [4. Session review and acceptance](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-04-learning.md) | L01–L07 | Terra; L03 fixture authoring may use Luna | Closure/manual review, confirmed improvement cycle, old schedule retired, final verified release |

Sequence: R01 → R02 → R03 → R04 → R05 → R06 → T01 → T02 → T03 → T04 → T05 → M01 → M02 → M03 → M04 → M05 → M06 → L01 → L02 → L03 → L04 → L05 → L06 → L07. Work runs sequentially to limit context and coordination cost. Do not request a new Astra plan between tasks: all tasks are specified here and in the four parts. A new requirement or genuinely ambiguous project meaning is a specific exception, not an excuse to defer the next task's design.

R03 establishes deployment safety; intermediate runtime releases are not required. M03 may deploy the reconciled, tested intermediate source to run migration pilots, using R03's preview and recovery. L07 deploys the final source and verifies it. Do not remove currently loaded project entry rules before the tested hub can replace them.

## Repository and execution conventions

The following are task-specific variables used by all command blocks. They are exact paths, not unresolved placeholders:

```bash
ARCH_REPO=/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture
HUB_ROOT=/Users/zykovsrg/Documents/vibecode/_ai-hub
cd "$ARCH_REPO"
```

In file lists below, paths are relative to this exact `ARCH_REPO`, unless explicitly prefixed with `HUB_ROOT`. Before a standalone handoff, expand these two roots and include the selected task's complete text and dependencies. Do not send the entire audit/history by default. Newly proposed paths are explicitly labeled Create.

Build/test implementation in an isolated Git worktree only where the current project's access rules permit its path; consult `superpowers:using-git-worktrees`. A Codex worktree outside the allowed project root is not implicitly authorized by this plan. When a compliant isolated checkout is unavailable, use the confirmed source checkout with explicit scoped commits and preserve unrelated edits. Set ARCH_REPO to the actual permitted implementation checkout in that case. Record repository heads and dirty-file lists. Tests use disposable fixtures, never the 57 project directories. Live deployment uses the verified updater.

Each task ends with a focused diff review, its named tests and one scoped commit in the implementation checkout. Use explicit file paths with `git add`; never `git add .`. Commit messages are listed in each part. Commits do not authorize push, merge to an unrelated branch, or a new external repository. Record an unavailable remote as local-only, not a test failure.

Test-driven cycle: create the specified regression → observe expected failure → implement → observe pass → review diff. A failing environmental prerequisite is not the intended red test. For documentation workflows use the stated behavior scenarios, not a test that merely searches for a keyword. Semantic pilot outputs must be evaluated against expected decisions.

## Exact handoff record

Create `docs/audits/2026-09-09-refactor-progress.md` at R01; append one short record after each completed task:

```markdown
### R01
State: complete
Implementation commit: actual commit hash
Checks: exact command; exit code; concise observed result
Changed files: exact paths
Remaining: explicit item or none
Next: R02
```

The task ID in this example is literal for the first record; subsequent entries use their actual IDs. Report failures with `State: blocked` and a concrete cause, keeping independent work possible. The record is an execution log, not another product-task database. A task requiring an external operation is not completed by merely documenting it.

## Coverage of the original findings

| Finding | Resolution tasks |
| --- | --- |
| A01 — release drift | R01–R03, L07 |
| A02 — Due/due | T01–T02 |
| A03 — calendar bypass | T03, L06 |
| A04 — snapshot collision/retention | R04 |
| A05 — early consumption | R05 |
| A06 — historical audit / new lifecycle | L01–L05; do not label yesterday's learner ineffective |
| A07 — context growth / effect checking | R05, T05, L01–L04 |
| A08 — conflicting instructions | R01, M05–M06, L02 |
| A09 — incomplete test coverage | R06, T02–T03, L03, L07 |
| A10 — stale architecture backlog | T04, M06 |
| A11 — .gitignore invisible in preview/commit | R02–R03 |
| A12 — invalid dates accepted | R04 |
| A13 — missing task records | T01–T02, T04 |
| A14 — custom resources at risk | M01–M04 |
| A15 — mixed ideas/history/debt | T04; app defects remain out of scope |
| A16 — ownership ambiguity | T04, M06 |
| A17 — unsafe app test suites | R06, L07 exclude app tests |
| A18 — historical Google key concern | L06 records explicit separate disposition; no credential values read |
| A19 — standalone returns on install | M05 |

## Completion gate

- [ ] Every task R01–L07 has a checked result or a clearly recorded user-approved scope exception.
- [ ] Every registered project has a migration disposition; count comes from the current registry, not the historical constant 57.
- [ ] Live hub matches the final approved release for managed code; user memory, allowlists and runtime environment are preserved.
- [ ] Closure review works on clean, problematic and partial sessions; manual review works on a selected session; improvements wait for confirmation.
- [ ] Existing task/calendar learning works and unresolved observations survive interruption and retention.
- [ ] All required safe tests pass; live checks are reported separately. Unavailable permission is not falsely reported as a passed live test.

The full planning deliverable is this index plus four implementation parts. They replace the earlier 24-package outline and reconciliation-only first assignment. The implementation model can start R01 and follow the sequence without requesting another general plan.
