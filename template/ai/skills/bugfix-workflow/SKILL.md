---
name: bugfix-workflow
type: worker
description: |
  Use when fixing a bug, regression, broken screen, broken state, or unexpected behavior.
  Activates when:
  - user reports something is broken, does not work, returns a wrong result, or behaves unexpectedly
  - user mentions a regression after a previous change
  - user says "почему не работает", "не должно так быть", "должно было", or similar
  Does NOT activate for:
  - feature requests
  - broad refactoring
  - new functionality without a prior bug report
---

# Bugfix Workflow

## Steps

1. Reproduce the expected and actual behavior.
2. Identify the smallest set of relevant files.
3. Explain the likely root cause.
4. Make minimal changes.
5. Avoid unrelated refactoring.
6. List manual checks.
7. Check that the fix does not introduce hidden technical debt.
8. If a temporary workaround is used, mark it explicitly and create a follow-up.

## Do not

- Do not rewrite large files.
- Do not change storage unless the bug is storage-related.
- Do not change project invariants.
