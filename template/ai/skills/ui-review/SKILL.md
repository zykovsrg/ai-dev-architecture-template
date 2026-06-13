---
name: ui-review
type: knowledge
description: |
  Use when reviewing frontend, layout, visual hierarchy, screen states, navigation, modals, or user-facing screens.
  Activates when:
  - the task changes a user-visible screen, modal, navigation, state, or layout
  - the task changes UI behavior, screen state, highlighting, scrolling, timeline rendering, or interaction feedback
  - the user asks whether the interface is clear, convenient, consistent, or visually good
  - the change may affect theme, labels, buttons, empty states, or screen consistency
  Does NOT activate for:
  - backend-only changes
  - storage-only changes
  - tests that do not affect UI
---

# UI Review

Open this skill before applying UI review. Do not rely on memory.

## Pair with tests

For UI behavior, screen state, layout logic, scrolling, rendering logic, or interaction changes, also open `ai/skills/write-tests/SKILL.md` and make an explicit test decision.

For purely decorative visual changes, `write-tests` is optional unless the change can affect behavior, state, layout logic, accessibility, or interaction.

If automated tests are not practical, provide a manual UI checklist.

## Check

1. Is the main task of the screen clear?
2. Is visual hierarchy clear?
3. Are primary and secondary actions separated?
4. Are screen states clear?
5. Are related screens consistent?
6. Does the change work in light and dark themes if the project supports them?
7. Are labels and buttons understandable?
8. Does the change preserve existing user habits and interaction patterns?
9. Is there a manual visual check for the exact changed state?

## Rules

- Do not suggest decorative changes unless they improve the user scenario.
- If the UI iteration changes goal, relevant files, or Done criteria, pause and decide whether `task-switch` is needed.
- If the user rejects a UI direction, explain what will be reverted before editing and mention any risk of losing useful work.
