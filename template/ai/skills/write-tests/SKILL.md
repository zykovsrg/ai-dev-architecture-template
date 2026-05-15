---
name: write-tests
type: worker
description: |
  Use when a change affects data model, storage, migrations, hierarchy rules, statuses, time calculations, cross-screen synchronization, or previously broken behavior.
  Activates when:
  - the change touches data model, storage, migrations, hierarchy, statuses, or time calculations
  - the change can break synchronization across screens or modules
  - the task fixes behavior that has broken before
  Does NOT activate for:
  - copy-only changes
  - visual-only CSS changes
  - spacing, colors, or decorative UI polish without behavior changes
---

# Write Tests

## Check whether tests are needed

For risky changes, add automated tests or explicitly explain why tests are not practical. Tests are expected if the change affects:

1. Data model.
2. Storage.
3. Migrations.
4. Project invariants.
5. Status transitions.
6. Time calculations.
7. Cross-screen synchronization.
8. Previously broken behavior.

## Rules

- Prefer small focused tests.
- Test behavior, not implementation details.
- Do not add a new test framework without user approval.
- If the current test framework is missing or broken, report this instead of inventing a new setup.
- If tests are not practical, provide a manual test checklist.
- If a test tool is missing or tests cannot run, explicitly report why.

## Output

Return:

1. What should be tested.
2. Which tests were added or should be added.
3. How to run them.
4. What manual checks remain.
