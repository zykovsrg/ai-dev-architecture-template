---
name: info-update
description: Turn temporary meeting information into an approval-gated, project-scoped update proposal without retaining the source transcript.
---

# Info Update

Use this skill when the user supplies temporary meeting text or asks to update
selected project memories from it. Work in `Mode: review` until every proposed
write has the required approval.

## Boundaries

Do not save the source transcript by default. Treat it as temporary input and
extract only the smallest sanitized facts, decisions, tasks, signals, and
hypotheses needed for the proposal. Never copy secrets, personal data, source
code, task logs, or private customer details into hub or project memory.

Confirm each affected project separately. A confirmation for one project never
permits reading or writing another project, even when the same meeting mentions
both. Before reading project memory, use the hub router to show that project's
registered ID and exact path, then obtain the separate project confirmation.

This skill must not replace the current task. It may propose a refinement to an
already confirmed project's current task only when that refinement fits the
existing Done criteria. A different task requires that project's `task-switch`;
a completed task requires its `task-finish` process. Never overwrite, pause,
finish, or copy a current task from this skill.

## Review-only procedure

Read only the supplied temporary text and the smallest already-confirmed
project memories allowed by each project's own instructions. Do not write while
preparing the proposal. Present the following sections in this exact order:

1. Meeting summary.
2. Affected projects.
3. Facts.
4. Decisions.
5. Current-task refinements.
6. Future tasks.
7. Signals.
8. Hypotheses.
9. Uncertain interpretations.
10. Per-file proposed edits.
11. Per-project confirmation.

For every item, name its source, confidence (`verified`, `stated`, `inferred`,
or `unknown`), and target project. Keep facts and decisions separate from
hypotheses and uncertain interpretations. A hypothesis is optional, explicitly
labelled, and never a permission to write or route.

## Proposed writes and approvals

Map each approved write to the selected project's existing controlled-memory
rule before changing it:

- Facts or durable project context: the project's `ai/project-context.md`
  workflow, if its rules allow the update.
- Durable decisions: the project's `ai/decisions.md` workflow.
- A future task: the project's `ai/future-tasks.md` workflow, after separate
  approval for that project.
- An in-scope current-task refinement: the project's `ai/current-task.md`
  rules, without changing its status or replacing its task.
- A cross-project signal: the hub's `ai/cross-project-signals.md`, with its
  source-project reference, sanitized summary, confidence, and explicit hub
  approval.

Show exact per-file diffs or replacement blocks before approval. Ask for one
explicit confirmation per affected project, naming the approved files and exact
registered path. Ask separately for any hub signal write. After approval,
perform only the approved writes in `Mode: implementation`, then report each
changed file and any item intentionally left as uncertain.

## Russian proposal template

```text
Режим: review

1. Краткое резюме встречи
<санитизированное резюме; исходная расшифровка не сохраняется>.

2. Затронутые проекты
- <project-id> — <exact-registered-path> — уверенность: <...>.

3. Факты
- [<project-id>] <факт> — источник: <...> — уверенность: <...>.

4. Решения
- [<project-id>] <решение> — источник: <...> — уверенность: <...>.

5. Уточнения текущей задачи
- [<project-id>] <только в рамках существующих Done criteria|нет>.

6. Будущие задачи
- [<project-id>] <предложение|нет>.

7. Сигналы
- <санитизированный сигнал|нет>.

8. Гипотезы
- <явно помеченная гипотеза|нет>.

9. Неоднозначные интерпретации
- <что требует уточнения|нет>.

10. Предлагаемые изменения по файлам
- <project-id>: <file> — <точное изменение>.

11. Подтверждение по проектам
Подтвердите отдельно: «Обновить <project-id> по пути <path>: <files>».
```
