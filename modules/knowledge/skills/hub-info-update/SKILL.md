---
name: hub-info-update
description: Turn temporary meeting information into project-scoped memory updates without retaining the source transcript.
---

# Info Update

Use this skill when the user supplies temporary meeting text or asks to update
selected project memories from it. Writes need no confirmation (Write Confirmation Policy in
`ai/architecture.md`); only opening each project still needs its routing
confirmation, and deletions need an explicit yes.

Module rules: `ai/rules/knowledge.md`.

## Boundaries

Do not save the source transcript by default. Treat it as temporary input and
extract only the smallest sanitized facts, decisions, tasks, signals, and
hypotheses needed for the update. Never copy secrets, personal data, source
code, task logs, or private customer details into hub or project memory.

Open each affected project through its own routing confirmation. A confirmation
for one project never permits reading or writing another project, even when the same meeting mentions
both. Before the first project group, use the hub router to show that project's
registered ID and exact path, then obtain the separate project confirmation.

This skill must not replace the current task. It may apply a refinement to an
already confirmed project's current task only when that refinement fits the
existing Done criteria. A different task requires that project's separate
confirmed `hub-task-switch` workflow. A completed task requires its separate
confirmed `hub-task-finish` workflow. This skill MUST NOT invoke or perform `hub-task-finish`; it stops and requires that separate confirmed workflow. Never overwrite, pause, finish, or copy a current task from this skill.

This skill MUST NOT invoke or perform `hub-project-switch`. It must not invoke or
perform `hub-project-switch` automatically. If the meeting requires another
project, it stops after the current project group. A separate confirmed
`hub-project-switch` between project groups is required before any read or write
for the next project; resume `hub-info-update` only after that switch. Project
confirmations inside this skill remain separate confirmation gates; they do not
authorize a project switch.

## Procedure

Read only the supplied temporary text and the smallest selected-project `ai/`
memory allowed by the hub-managed flow. First present one meeting summary and a distinct `Affected projects`
section listing every affected project ID and exact path. Then prepare the
following sections for the currently confirmed project group only. Before a
next group, stop for the separate confirmed `hub-project-switch`; do not read or
write for that group until `hub-info-update` resumes after the switch. Do not
merge items from different projects into a shared facts, decisions, or task
list.

## Per-project proposal sections

For the currently confirmed project group, use this exact order:

### Project identity and path

State the registered project ID and exact registered path.

### Facts

### Decisions

### Task changes

Include only an in-scope refinement; otherwise say that a separate confirmed
`hub-task-switch` or `hub-task-finish` workflow is required and stop that item.

### Future tasks

### Signals

### Hypotheses

### Uncertainties

### Proposed file edits

### Per-project writes

For every item, name its source and confidence (`verified`, `stated`,
`inferred`, or `uncertain`). Keep facts and decisions separate from hypotheses
and uncertainties. A hypothesis is optional, explicitly labelled, and never a
permission to write or route: hypotheses and uncertainties are reported, not
written. Work in one project group permits neither a read nor a write in
another group.

A cross-project signal may appear in a separate hub section only after every
related project group has been processed. It must name the related project
IDs and retain its source and confidence; it is written directly like any
other update.

## Writes

Map each write to the selected project's existing controlled-memory
rule before changing it:

- Facts or durable project context: the project's `ai/project-context.md`
  workflow, if its rules allow the update.
- Durable decisions: the project's `ai/decisions.md` workflow.
- A future task: the project's `ai/future-tasks.md` workflow.
- An in-scope current-task refinement: the project's `ai/current-task.md`
  rules, without changing its status or replacing its task.
- A cross-project signal: the hub's `ai/cross-project-signals.md`, with its
  source-project reference, sanitized summary, and confidence.

Apply the writes directly in `Mode: implementation` and show the exact
per-file diffs in the report. After every selected-project write to `ai/current-task.md` or
`ai/future-tasks.md`, run the `after-task-write` event: read
`<hub>/ai/modules.md`; for each subscriber listed under `after-task-write`,
read its rules file and run its command for the confirmed project ID only.
With no subscribers, do nothing. Apply a subscriber's pending proposal
directly unless it deletes something; a deletion waits for an explicit yes.
Then report
each changed file and any item intentionally left as uncertain.

## Russian report template

```text
Режим: implementation

1. Краткое резюме встречи
<санитизированное резюме; исходная расшифровка не сохраняется>.

2. Affected projects
- <project-id> — <exact-registered-path>.

3. Изменения по проектам.

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
Source: <...> — confidence: <verified|stated|inferred|uncertain>.

#### Будущие задачи
- <задача|нет> — источник: <...> — уверенность: <...>.

#### Сигналы
- <сигнал, относящийся только к этому проекту|нет> — источник: <...> — уверенность: <...>.

#### Гипотезы
- <явно помеченная гипотеза|нет> — источник: <...> — уверенность: <...>.

#### Неопределённости
- <что требует уточнения|нет> — источник: <...> — уверенность: <...>.

#### Изменённые файлы
- <file> — <точный diff или блок замены>.


3. Межпроектные сигналы hub (только после каждой связанной группы проектов).
- <санитизированный сигнал|нет> — связанные проекты: <...> — источник: <...> — уверенность: <...>.
Записано в `ai/cross-project-signals.md`.

4. Следующая группа проекта
Если есть следующий <project-id>, остановитесь. Нужен отдельный подтверждённый
project-switch между группами проектов; после него возобновите info-update
только для нового подтверждённого проекта.
```
