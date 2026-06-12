---
name: bugfix-workflow
type: worker
description: |
  Use when fixing a bug, regression, crash, performance problem, broken screen, broken state, or unexpected behavior.
  Activates when:
  - user reports something is broken, does not work, returns a wrong result, or behaves unexpectedly
  - user mentions a crash, freeze, lag, regression, or performance problem
  - user mentions a regression after a previous change
  - user says "почему не работает", "не должно так быть", "должно было", "лагает", "крашится", or similar
  Does NOT activate for:
  - feature requests
  - broad refactoring
  - new functionality without a prior bug report
---

# Bugfix Workflow

## Measurement-first rule

For bugs, crashes, and performance tasks, do not write a full spec or implementation plan based only on an unverified hypothesis.

First try to establish evidence:

1. Reproduce the issue, or explain why it cannot be reproduced.
2. Capture the observed behavior with a test, log, profiler output, screenshot, or manual reproduction steps.
3. Name the expected behavior.
4. Identify the smallest likely affected area.
5. Check relevant active invariants in `ai/decisions.md` before changing architecture-sensitive code.

If the issue cannot be reproduced, the fix can still be shipped as a mitigation, but the final report and `ai/changelog.md` must say:

- `Root cause: unproven`
- `Fix status: mitigated`
- what evidence supports the mitigation
- what follow-up would prove or disprove the root cause

## Steps

1. Open this skill before applying the workflow. Do not rely on memory.
2. Reproduce the expected and actual behavior.
3. For performance work, measure before choosing the solution.
4. Identify the smallest set of relevant files.
5. Read `ai/decisions.md` if the change touches architecture, data model, storage, undo behavior, sync, or durable invariants.
6. Explain the likely root cause and whether it is proven or only suspected.
7. Make minimal changes.
8. Avoid unrelated refactoring.
9. Add or update tests when practical.
10. List manual checks.
11. Check that the fix does not introduce hidden technical debt.
12. If a temporary workaround is used, mark it explicitly and create a follow-up.

## Temporary diagnostics

Temporary diagnostic code may be committed only when keeping it is intentional and useful for the next step.

If temporary diagnostics remain in main, create an explicit removal record in `ai/paused-tasks.md`, `ai/current-task.md` Done criteria, or `ai/changelog.md`:

- diagnostic code location;
- why it remains;
- when to remove it;
- removal criteria;
- risk if it stays too long.

## Do not

- Do not rewrite large files.
- Do not change storage unless the bug is storage-related.
- Do not change project invariants.
- Do not present an unverified hypothesis as proven root cause.
- Do not leave TEMP diagnostics without a removal path.
