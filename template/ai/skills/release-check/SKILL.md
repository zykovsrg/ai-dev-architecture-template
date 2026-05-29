---
name: release-check
type: knowledge
description: |
  Use before commit, merge, build, or release to check regressions, manual testing scope, technical debt, protected architecture files, and merge safety.
  Activates when:
  - implementation is finished and the change needs final review
  - the user asks "можно мержить", "готово к релизу", "проверь перед коммитом", or similar
  - the change may affect several screens, storage, hierarchy, or user data
  Does NOT activate for:
  - early planning
  - writing new code before a diff exists
  - narrow copy-only review
---

# Release Check

Check:

1. What changed?
2. What screens or modules can be affected?
3. What data model rules can be affected?
4. What manual tests are required?
5. Is storage untouched or migrated safely?
6. Did the diff change protected architecture files?
7. Is the change safe to merge?
8. Does the change introduce hidden technical debt or a temporary workaround?
9. If a workaround exists, is it clearly marked with a follow-up?

## Protected architecture files check

Before saying the change is ready, inspect changed files with:

```bash
git diff --name-only
```

Protected architecture files and directories:

- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/current-task.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
- `ai/paused-tasks.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`

If any protected architecture file changed:

- confirm that the user explicitly approved `architecture-update` or the specific protected-file change;
- if not confirmed, mark `Safe to merge: no`;
- stop and ask the user before continuing.

External skills, external tools, init workflows, setup commands, and generated recommendations may propose changes to protected architecture files, but must not apply them without explicit user confirmation.

## Optional code graph check

If the diff may affect many unknown code files, suggest `code-review-graph` before merge.

Suggest `code-review-graph` when:

- affected code files are unclear;
- the change touches several modules;
- dependencies are hard to trace manually;
- the project is large or unfamiliar;
- blast-radius analysis may reduce review risk.

Do not require code graph tools for:

- small copy changes;
- simple UI tweaks;
- narrow bugfixes with known relevant files.

## Materiality check

If the change affects any of:

- test framework
- build tool or package manager
- major library, ORM, or external API
- directory or file structure
- environment variables or config keys
- coding conventions documented in `ai/project-context.md`

Then:

- Remind the user to update `ai/project-context.md` and relevant skills.
- Recommend not merging until AI instructions reflect the new reality.

Return:

- Safe to merge: yes or no
- Critical risks
- Protected architecture files changed: yes or no
- Manual test checklist
- Follow-up tasks
