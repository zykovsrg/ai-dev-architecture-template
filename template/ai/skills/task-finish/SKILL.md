---
name: task-finish
type: mixed
description: |
  Use when checking whether a task can be closed and, after explicit user confirmation, cleaning up task context.
  Activates when:
  - the user asks whether the task is complete
  - the user says "проверь, можно ли закрыть задачу", "можно ставить done", or similar
  - implementation and review are finished and closure decision remains
  - implementation or review suggests the current task may be complete
  - the user explicitly confirms that the task is completed and asks to clean up
  Does NOT activate for:
  - writing code
  - starting a new task
  - tasks with unresolved blocking risks
---

# Task Finish

Open this skill before applying task-finish. Do not rely on memory.

This skill has three phases. When Phase 1 concludes that the task can be
closed, run Phase 2 and Phase 3 immediately in the same step, without asking
for a separate confirmation. Stop and report instead of cleaning up only when
Phase 1 finds a blocker.

## Phase 1 — Check

Read:

- `ai/current-task.md`
- current diff
- `ai/decisions.md` if the task touched architecture, data model, storage, signing, sandboxing, undo behavior, sync, new services, or durable invariants
- `ai/future-tasks.md` only if the task produced out-of-scope follow-up ideas or the user asked to save future tasks

Answer:

1. Are Done criteria completed?
2. What checks are still needed?
3. Can Status be changed to done?
4. What should be moved to `ai/changelog.md`?
5. Should anything be added to `ai/decisions.md`?
6. Are there TEMP diagnostics or workarounds that need a removal task?
7. Which out-of-scope ideas, missing test seams, follow-up investigations, or non-blocking improvements belong in `ai/future-tasks.md`?
8. Is anything blocking cleanup of `ai/current-task.md`?
9. How should the result be saved: GitHub push, local commit, or local fallback archive/patch?
10. Would a focused `knowledge-review` be useful? Offer it when relevant, but
    never start it automatically.

## Changelog vs decisions vs future tasks

Use `ai/changelog.md` for what changed recently.

Use `ai/decisions.md` for durable rules future agents must not break.

Use `ai/future-tasks.md` for ideas and future implementation tasks that were not part of the completed task scope.

Add or propose a decision when the task introduced or exposed a long-term rule about:

- data model;
- storage location or migration;
- signing, sandboxing, entitlements, deployment, or environment setup;
- undo or redo behavior;
- sync behavior;
- recurrence or scheduling behavior;
- external APIs;
- project architecture;
- agent workflow that must persist across sessions.

Do not add minor implementation details to `ai/decisions.md`.

Do not add new scope to the completed task just because a future task was discovered.

## Rules

- If implementation or review suggests the task is complete, run this check instead of declaring the task closed.
- Do not mark the task as done if manual UI checks are still required.
- Do not mark the task as done if required automated tests were not added, not run, or not explicitly replaced with a justified manual checklist.
- Clean `ai/current-task.md` as soon as Phase 1 finds no blocker; do not wait for a separate confirmation.
- If there are open risks, keep Status as review or blocked.
- If the task created a durable architecture, product, workflow, data model, storage, signing, sandboxing, sync, or undo rule, suggest adding it to `ai/decisions.md`.
- If an issue was only mitigated and root cause is unproven, record that clearly in `ai/changelog.md`.
- If an idea is useful but outside the current task, add it to `ai/future-tasks.md` instead of implementing it during cleanup.
- Offer `knowledge-review` only when selected knowledge records may need a
  focused review. Do not start it without an explicit request or selected scope.
- Do not claim the task is closed until the result is saved.
- If `git remote -v` shows a `github.com` remote, commit and push are mandatory closure steps, not defaults. The task is not closed until the push succeeds or the user explicitly accepts local-only closure after a reported push failure.
- If GitHub is not configured, use local-only saving and explain the limitation.

## Phase 2 — Cleanup

Run automatically when Phase 1 found no blocker.

Do not change application code.

Steps:

1. Add a short summary to `ai/changelog.md`.
2. If the task introduced an important architecture, product, data model, workflow, storage, signing, sandboxing, sync, undo, or agent-process decision, add it to `ai/decisions.md`.
3. Append the identified future task candidates to `ai/future-tasks.md` and name them in the report.
4. If the completed task was promoted from `ai/future-tasks.md`, delete its
   entry from that file. The history lives in `ai/changelog.md`; do not keep
   `promoted` or `done` entries in the backlog.
5. If temporary diagnostics remain, keep removal criteria in `ai/current-task.md` Done criteria or handoff notes. Record retained diagnostics in `ai/changelog.md` if the retention is notable. Do not write TEMP diagnostics cleanup work to `ai/paused-tasks.md`.
6. Clean `ai/current-task.md`.
7. Leave a blank template for the next task in `ai/current-task.md` with `Status: empty` and `Stage: intake`.

Rules:

- Do not edit application files.
- Do not change code.
- Do not remove important unresolved risks.
- If there are unresolved risks, move them to changelog, future-tasks, or leave them in the new task template depending on whether they are completed history, future ideas, or blocking current context. Use `ai/paused-tasks.md` only for paused active work created through `task-switch`.
- Do not add minor implementation details to `ai/decisions.md`.

## Phase 3 — Save result

Run automatically after Phase 2 cleanup.

First inspect:

```bash
git status --short
git remote -v
```

If a GitHub remote exists:

1. Stage the completed task changes.
2. Commit with a clear message.
3. Push the current branch to GitHub.
4. Report the pushed branch and commit.

A GitHub remote means any remote whose URL points to `github.com`. With such
a remote present, do not report the task as closed while the push has not
succeeded and the user has not been told why.

If Git exists but no GitHub remote exists:

1. Stage the completed task changes.
2. Commit locally with a clear message.
3. Tell the user that the task is saved only on this computer and has not been pushed to GitHub.
4. Offer the GitHub setup path as a follow-up, not as an automatic action.

If Git is unavailable:

1. Create a local fallback: patch, archive, or clear list of changed files.
2. Tell the user exactly where the fallback was saved.
3. Explain that this is weaker than Git because history and sync are not automatic.

Rules:

- Do not push if the user explicitly chose local-only mode.
- Report every automatic write and the commit in the answer, so the user sees what changed without asking.
- Do not push secrets, temporary diagnostics, or unresolved workarounds.
- If commit fails, do not claim the task is closed; report the reason and keep or restore enough task context for retry.
- If local commit succeeds but push fails, report `Saved locally, not pushed to GitHub` and ask whether to retry push or accept local-only closure.
- If the selected save step succeeds, the task can be reported as closed.
