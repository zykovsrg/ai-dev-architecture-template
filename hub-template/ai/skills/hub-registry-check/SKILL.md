---
name: hub-registry-check
description: Audit hub registration metadata and propose separately approved maintenance actions.
---

# Registry Check

Use this skill to inspect hub registration health. It is read-only until approval: the audit must not edit allowed roots, registry entries, cards,
signals, archives, active-project data, or any registered project.

## Audit procedure

1. Run `scripts/check-hub-registry.sh` against the hub and record its output
   and exit status. A validator failure is a finding, not permission to fix
   anything.
2. Read hub-owned registry metadata only as needed to report:
   - registered paths that are missing or no longer canonical;
   - stale or missing cards and card relationships that no longer name a
     registered project;
   - unregistered direct children of the sole allowed root, using names only
     and without recursive scanning or project-content reads;
   - archive candidates indicated by registry status or clearly obsolete hub
     metadata;
   - old signals in `ai/cross-project-signals.md`, based on their recorded
     status and date, without treating a signal as project permission.
3. Present a report with evidence, confidence, and a separate proposed action
   for every finding. Clearly distinguish verified observations from inferred
   archive candidates.
4. Wait for explicit confirmation for each individual fix. Re-run the
   validator after an approved hub-metadata fix. Do not batch unrelated fixes
   under one vague approval.

A weekly reminder may offer this skill, but cannot invoke it automatically.
The reminder must not run the validator, enumerate roots, or create a report.

## Russian report template

```text
Проверка реестра: <пройдена|обнаружены проблемы>
Режим: routing

1. <категория>: <наблюдение>.
   Доказательство: <путь или вывод проверки>.
   Уверенность: <проверено|предположение>.
   Предлагаемое действие: <одно конкретное действие>.

Ничего не изменено. Подтвердите отдельно каждое действие, которое нужно выполнить.
```
