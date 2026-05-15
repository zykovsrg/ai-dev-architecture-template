---
name: ui-review
type: knowledge
description: |
  Use when reviewing frontend, layout, visual hierarchy, screen states, navigation, modals, or user-facing screens.
  Activates when:
  - the task changes a user-visible screen, modal, navigation, state, or layout
  - the user asks whether the interface is clear, convenient, consistent, or visually good
  - the change may affect theme, labels, buttons, empty states, or screen consistency
  Does NOT activate for:
  - backend-only changes
  - storage-only changes
  - tests that do not affect UI
---

# UI Review

Check:

1. Is the main task of the screen clear?
2. Is visual hierarchy clear?
3. Are primary and secondary actions separated?
4. Are screen states clear?
5. Are related screens consistent?
6. Does the change work in light and dark themes if the project supports them?
7. Are labels and buttons understandable?

Do not suggest decorative changes unless they improve the user scenario.
