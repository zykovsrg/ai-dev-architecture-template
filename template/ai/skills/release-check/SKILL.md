---
name: release-check
type: knowledge
description: |
  Use before commit, merge, build, or release to check regressions, manual testing scope, technical debt, and merge safety.
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
6. Is the change safe to merge?
7. Does the change introduce hidden technical debt or a temporary workaround?
8. If a workaround exists, is it clearly marked with a follow-up?

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
- Manual test checklist
- Follow-up tasks
