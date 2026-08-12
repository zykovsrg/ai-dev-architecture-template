---
name: project-router
description: Route an unconfirmed request to a registered hub project without reading project files before confirmation.
---

# Project Router

Use this skill for every real request when no project has been confirmed in the
current chat. Keep `Mode: routing` until the user gives explicit confirmation.

## Read allowlist and phases

1. Read the compact hub index only: `ai/allowed-roots.md`,
   `ai/project-registry.md`, and `ai/active-project.md`. Do not list allowed
   roots or inspect project directories.
2. Match the request against registered IDs, names, types, statuses, and tags.
   Select a maximum of three candidates. An unregistered path is never a
   candidate.
3. In this phase, read only candidate cards at
   `ai/project-cards/<registered-id>.md`. Do not read project memory, source
   code, configuration, or arbitrary hub files. Compare only each card's
   purpose, tasks, boundaries, and relationships.
4. Read only related active signals from the compact index: use the active
   project record only when it names one of the candidates. Do not read
   cross-project signals, project task memory, or project files during routing.
5. Classify routing confidence as `high, medium, or low` and preserve evidence
   confidence from the hub architecture (`verified`, `stated`, `inferred`, or
   `unknown`). High means a direct registered ID/name match; medium means a
   bounded metadata match; low means weak or conflicting metadata.
6. Show the reason, registered project ID, and exact registered path. State
   the confidence and ask for explicit confirmation. Then wait for explicit confirmation; do not enter, read, or change a project first.

The registry is authoritative for the ID and path. If a candidate is missing,
invalid, outside allowed roots, or has an unusable card, reject it safely and
ask for a registered alternative. A remembered active project is not a
confirmation in a new chat.

## Required response shape

Show `Mode: routing` and use one of these Russian templates. Replace only the
angle-bracket placeholders with registered hub metadata.

### One candidate

```text
Проект: <project-id>
Путь: <registered-path>
Режим: routing
Уверенность маршрутизации: высокая|средняя|низкая
Причина: <краткая причина из реестра и карточки>.

Подтвердите, что открыть именно этот проект по указанному пути.
```

### Two or three candidates

```text
Режим: routing
Нашёл несколько зарегистрированных вариантов:
1. <project-id-1> — <exact-path-1> — <краткая причина>.
2. <project-id-2> — <exact-path-2> — <краткая причина>.

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
Не могу выбрать <project-id>: <причина — нет в реестре|путь вне разрешённых корней|некорректная карточка>.

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
