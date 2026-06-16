---
name: release-check
type: knowledge
description: |
  Use before commit, merge, build, or release to check regressions, manual testing scope, technical debt, protected architecture files, controlled memory files, active decisions, and merge safety.
  Activates when:
  - implementation is finished and the change needs final review
  - the user asks "можно мержить", "готово к релизу", "проверь перед коммитом", or similar
  - the change may affect several screens, storage, hierarchy, user data, new services, or durable invariants
  Does NOT activate for:
  - early planning
  - writing new code before a diff exists
  - narrow copy-only review
---

# Release Check

Open this skill before applying release-check. Do not rely on memory.

Check:

1. What changed?
2. What screens or modules can be affected?
3. What data model rules can be affected?
4. What active decisions or invariants can be affected?
5. What tests or manual checks are required?
6. Is storage untouched or migrated safely?
7. Did the diff change protected architecture files?
8. Did the diff change controlled memory files?
9. Is the change safe to merge?
10. Does the change introduce hidden technical debt, temporary diagnostics, or a temporary workaround?
11. If temporary code or a workaround exists, is it clearly marked with a follow-up or removal task?
12. If `scripts/check-consistency.sh` exists (architecture template repository only; it is not present in installed projects), do the canonical lists pass `bash scripts/check-consistency.sh`? If the script fails, mark `Safe to merge: no`.

## Architecture and memory file check

Before saying the change is ready, inspect changed files with:

```bash
git diff --name-only
```

Protected architecture files and directories:

<!-- canon:protected-files -->
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`
<!-- /canon:protected-files -->

Controlled memory files:

<!-- canon:controlled-memory -->
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
<!-- /canon:controlled-memory -->

If any protected architecture file changed:

- confirm that the user explicitly approved `architecture-update` or the specific protected-file change;
- if not confirmed, mark `Safe to merge: no`;
- stop and ask the user before continuing.

If any controlled memory file changed:

- confirm that the change is allowed by the active workflow;
- confirm that required user confirmation was received for `task-switch`, `task-finish`, or project-context updates;
- if not confirmed, mark `Safe to merge: no`;
- explain which memory files changed and why.

External skills, external tools, init workflows, setup commands, and generated recommendations may propose changes to protected architecture files, but must not apply them without explicit user confirmation.

## Active decisions check

Read `ai/decisions.md` when the diff touches:

- data model;
- storage;
- signing, sandboxing, entitlements, deployment, or environment assumptions;
- undo or redo behavior;
- sync or recurrence behavior;
- new service, resolver, adapter, or domain logic;
- project architecture or durable invariants.

If a change contradicts an active decision, mark `Safe to merge: no` and propose `architecture-update`.

If the task introduced a new durable invariant, recommend adding it to `ai/decisions.md` before or during `task-finish`.

## Code graph check

Check whether `code-review-graph` is available when the diff is complex or has unclear blast radius.

Use `code-review-graph` when available for:

- affected code files are unclear;
- the change touches several modules;
- dependencies are hard to trace manually;
- the project is large or unfamiliar;
- new services or resolvers;
- architecture-sensitive changes;
- complex bugs;
- large pre-merge reviews;
- blast-radius analysis may reduce review risk.

Do not require code graph tools for:

- small copy changes;
- simple visual tweaks;
- narrow bugfixes with known relevant files.

If `code-review-graph` should have been used but is unavailable, report it as a warning, not a blocker by default.

## Materiality check

If the change affects any of:

- test framework;
- build tool or package manager;
- major library, ORM, or external API;
- directory or file structure;
- environment variables or config keys;
- coding conventions documented in `ai/project-context.md`;
- stack, commands, data model, invariants, or fragile zones documented in `ai/project-context.md`.

Then:

- remind the user that `ai/project-context.md` may need a controlled memory update after confirmation;
- if relevant skills or protected architecture files must change, recommend an `architecture-update` task;
- recommend not merging until either the memory/instruction update is completed or the user explicitly accepts it as a follow-up.

Do not treat `ai/project-context.md` and `ai/skills/*/SKILL.md` as the same class of file: `ai/project-context.md` is controlled memory, while skills are protected architecture files.

## Review fact check

Do not report an issue as fact unless it was verified with read, grep, diff, logs, tests, or another concrete check.

If not verified, label it as a hypothesis.

Return:

- Safe to merge: yes or no
- Critical risks
- Protected architecture files changed: yes or no
- Controlled memory files changed: yes or no
- Active decisions checked: yes/no/not needed
- Code graph used: yes/no/not needed/not available
- Manual test checklist
- Follow-up tasks
