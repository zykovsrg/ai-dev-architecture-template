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
existing Done criteria. A different task requires that project's separate
confirmed `task-switch` workflow. A completed task requires its separate
confirmed `task-finish` workflow. This skill MUST NOT invoke or perform `task-finish`; it stops and requires that separate confirmed workflow. Never overwrite, pause, finish, or copy a current task from this skill.

This skill MUST NOT invoke or perform `project-switch`. If the meeting requires another project, it stops and requires a separate confirmed `project-switch` workflow before any read or proposal for that project. Project confirmations inside this skill remain separate confirmation gates; they do not authorize a project switch.

## Review-only procedure

Read only the supplied temporary text and the smallest already-confirmed
project memories allowed by each project's own instructions. Do not write while
preparing the proposal. First present one meeting summary, then a distinct
`Affected projects` section listing every affected project ID and exact path,
then present the following per-project sections for every affected project. Do
not merge items from different projects into a shared facts, decisions, task,
or approval list.

## Per-project proposal sections

For each project, use this exact order:

### Project identity and path

State the registered project ID and exact registered path.

### Facts

### Decisions

### Task changes

Include only an in-scope refinement; otherwise say that a separate confirmed
`task-switch` or `task-finish` workflow is required and stop that item.

### Future tasks

### Signals

### Hypotheses

### Uncertainties

### Proposed file edits

### Per-project approval

For every item, name its source and confidence (`verified`, `stated`,
`inferred`, or `uncertain`). Keep facts and decisions separate from hypotheses
and uncertainties. A hypothesis is optional, explicitly labelled, and never a
permission to write or route. The approval in one project group permits neither
a read nor a write in another group.

A cross-project signal may appear in a separate hub section only after each related project group. It must name the related project IDs, retain its source and confidence, and still requires its own explicit hub approval.

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

2. Affected projects
- <project-id> — <exact-registered-path>.

3. Предложения по проектам.

### <project-id>

#### Проект: идентификатор и путь
<project-id> — <exact-registered-path>.

#### Факты
- <факт|нет> — источник: <...> — уверенность: <...>.

#### Решения
- <решение|нет> — источник: <...> — уверенность: <...>.

#### Изменения текущей задачи
- <уточнение в рамках существующих Done criteria|нет; для иной задачи нужна
  отдельная подтверждённая процедура task-switch, которую info-update не запускает>.

#### Будущие задачи
- <предложение|нет> — источник: <...> — уверенность: <...>.

#### Сигналы
- <сигнал, относящийся только к этому проекту|нет> — источник: <...> — уверенность: <...>.

#### Гипотезы
- <явно помеченная гипотеза|нет> — источник: <...> — уверенность: <...>.

#### Неопределённости
- <что требует уточнения|нет> — источник: <...> — уверенность: <...>.

#### Предлагаемые изменения файлов
- <file> — <точный diff или блок замены>.

#### Подтверждение по проекту
Подтвердите отдельно: «Обновить <project-id> по пути <path>: <files>».

3. Межпроектные сигналы hub (только после каждой связанной группы проектов).
- <санитизированный сигнал|нет> — связанные проекты: <...> — источник: <...> — уверенность: <...>.
Подтвердите отдельно: «Записать hub-сигнал: <signal-id|summary>».
```
