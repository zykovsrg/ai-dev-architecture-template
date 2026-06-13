---
name: write-tests
type: worker
description: |
  Use when a change affects data model, storage, migrations, hierarchy rules, statuses, time calculations, cross-screen synchronization, UI behavior, layout logic, interactions, or previously broken behavior.
  Activates when:
  - the change touches data model, storage, migrations, hierarchy, statuses, or time calculations
  - the change can break synchronization across screens or modules
  - the task fixes behavior that has broken before
  - the task changes UI behavior, screen states, layout logic, or user-visible interaction
  - the user asks whether tests are needed
  Does NOT activate for:
  - copy-only changes
  - purely decorative visual changes where no behavior, state, layout logic, or interaction changes
---

# Write Tests

Open this skill before making or justifying a test decision. Do not apply it from memory.

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
9. UI behavior, screen state logic, layout logic, or user-visible interaction.
10. New services, resolvers, adapters, or domain logic.

For UI behavior, screen state, layout logic, or interaction changes:

- add tests if the behavior can be tested reliably;
- otherwise provide a manual UI checklist and explain why automated tests are not practical.

For purely decorative visual changes, this skill is optional unless the visual change can affect behavior, state, layout logic, accessibility, or interaction. If this skill is not used for a decorative-only change, `ui-review` must still provide a manual visual checklist.

## Invariant check before commit

Before committing a new service, resolver, storage path, undo path, sync behavior, or other architecture-sensitive logic:

1. Read relevant active entries in `ai/decisions.md`.
2. Check whether the implementation violates any durable invariant.
3. If an invariant must change, stop and propose `architecture-update` instead of silently changing behavior.

## Rules

- Prefer small focused tests.
- Test behavior, not implementation details.
- Do not add a new test framework without user approval.
- If the current test framework is missing or broken, report this instead of inventing a new setup.
- If tests are not practical, provide a manual test checklist.
- If a test tool is missing or tests cannot run, explicitly report why.
- Do not skip this skill merely because the agent thinks a risky or behavior-affecting change is simple; open it and make a short decision.

## Output

Return:

1. What should be tested.
2. Which tests were added or should be added.
3. How to run them.
4. What manual checks remain.
5. Whether `ai/decisions.md` contains relevant invariants and how they were checked.
