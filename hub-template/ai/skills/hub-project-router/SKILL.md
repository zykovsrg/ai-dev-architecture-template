---
name: hub-project-router
description: Classify an unconfirmed request, route personal-assistant work safely, or route project-specific work to a registered hub project.
---

# Project Router

Use this skill for every real request when no project has been confirmed in the
current chat. Classify intent before choosing a project.

## Intent-first route

Choose exactly one route before reading project data:

1. A **personal-assistant request** asks for a day plan, cross-project status,
   overdue or blocked work, an evening or weekly review, capture of supplied
   task or meeting text, or cross-project knowledge search. Set `Mode:
   assistant` and invoke `hub-workflows`.
2. A **project-specific request** asks to build, fix, review, or otherwise work
   inside one named or implied project. Keep `Mode: routing` and use the
   project-confirmation phases below.
3. An architecture request names the architecture project; treat it as a
   project-specific request and preserve its explicit project confirmation.
4. If the route is genuinely unclear, ask one concise clarification question.

For a personal-assistant request, `hub-workflows` may read only
`ai/current-task.md`, `ai/future-tasks.md`, and `ai/paused-tasks.md` from all
active registered projects. It must separate personal and work results, cite
the project and canonical record for every fact, and skip inactive or archived
projects. Do not read project code, knowledge records, credentials, or arbitrary
files in this route. The user does not need to confirm each project read; every
write still uses the workflow's explicit proposal confirmation.

## Read allowlist and phases

Apply these phases only to a project-specific request.

1. Run `scripts/read-compact-project-index.sh`. Before confirmation, use only
   its five fields: `project_id`, `name`, `tags`, `status`, `purpose_brief`.
   Do not read candidate cards, signals, project memory, knowledge, source code,
   configuration, arbitrary hub files, or linked targets.
2. Match the request against those five fields and select a maximum of three
   candidates. An unregistered path is never a candidate.
3. Classify routing confidence as `high, medium, or low` and preserve evidence
   confidence from the hub architecture (`verified`, `stated`, `inferred`, or
   `unknown`). High means a direct registered ID/name match; medium means a
   bounded metadata match; low means weak or conflicting metadata.
4. To show a selected candidate, read its exact registered path only. Show the
   reason, registered project ID, exact path, and confidence; then ask for and
   wait for explicit confirmation. Do not enter, read, or change a project first.

The registry is authoritative for the ID and path. If a candidate is missing
from the compact index, has invalid compact metadata, or is outside allowed
roots, reject it safely and ask for a registered alternative. A remembered
active project is not a confirmation in a new chat.

Project/task files remain canonical; project cards are metadata only and remain
unavailable before confirmation. Compact-index metadata never grants a project
read, and a link never grants a project read. Waiting is task/subtask-only: do not place a project in Waiting
while other work is actionable. Related archiproject links never add contribution.

## Required response shape

Show `Mode: routing` and use one of these Russian templates. Replace only the
angle-bracket placeholders with registered hub metadata.

### One candidate

```text
Проект: <project-id>
Путь: <registered-path>
Режим: routing
Уверенность маршрутизации: высокая|средняя|низкая
Причина: <краткая причина из метаданных compact index>.

Подтвердите, что открыть именно этот проект по указанному пути.
```

### Two or three candidates

```text
Режим: routing
Нашёл несколько зарегистрированных вариантов:
1. <project-id-1> — <exact-path-1> — Уверенность маршрутизации: <высокая|средняя|низкая> — <краткая причина>.
2. <project-id-2> — <exact-path-2> — Уверенность маршрутизации: <высокая|средняя|низкая> — <краткая причина>.
3. <project-id-3> — <exact-path-3> — Уверенность маршрутизации: <высокая|средняя|низкая> — <краткая причина>.

Укажите номер или точное имя проекта и подтвердите путь. До подтверждения я ничего в проектах не открываю.
```

### No candidate

```text
Режим: routing
В реестре нет подходящего зарегистрированного проекта. Я не буду искать папки самостоятельно.

Назовите зарегистрированный проект или попросите отдельно зарегистрировать новый.
```

### Rejection

```text
Режим: routing
Не могу выбрать <project-id>: <причина — нет в compact index|путь вне разрешённых корней|некорректные метаданные>.

Назовите другой зарегистрированный проект или подтвердите отдельную регистрацию.
```

### Explicit project naming

```text
Вы назвали проект <project-id>. В реестре ему соответствует путь <registered-path>.
Подтвердите: «Открыть <project-id> по пути <registered-path>».
```

Do not treat a project name, a number, or a request such as “open it” as
explicit confirmation unless it unambiguously confirms the displayed project
and exact path.
