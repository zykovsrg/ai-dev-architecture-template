---
name: hub-project-router
description: Route an unconfirmed request to a registered hub project without reading project files before confirmation.
---

# Project Router

Use this skill for every real request when no project has been confirmed in the
current chat. Keep `Mode: routing` until the user gives explicit confirmation.

## Read allowlist and phases

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
