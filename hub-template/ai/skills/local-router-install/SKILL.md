---
name: local-router-install
description: Install a small, approval-gated local area index inside one confirmed project after stable boundaries are proven.
---

# Local Router Installation

Use this skill only for a confirmed active project that has at least three stable independent areas. An area is stable when it has a clear responsibility,
an enduring owner/boundary, and repeated work that does not require reading
unrelated areas to understand it. Do not install a local router merely because
the project has several folders or tags.

## Preconditions

1. Confirm the active project's registered ID and exact path through the hub.
2. Read the confirmed project's entry instructions and smallest relevant
   architecture context.
3. Propose the areas, their boundaries, and why each is stable and independent.
4. Obtain explicit `architecture-update` approval from that project before
   creating files. The approval must name the project and the local-router
   files to create.

If any precondition is absent, remain in `Mode: review` and present a proposal
only. A hub-level approval does not replace project architecture approval.

## Installation boundary

Create only these files after approval:

- `ai/local-router/index.md`
- `ai/local-router/areas/<id>.md` for each individually confirmed area

Do not create another task store, Git repository, global project card, project
registry, or cross-project signal store. Areas have no separate current task;
the confirmed project's existing `ai/current-task.md` remains the only task
memory. The local router is a navigation aid, not a permission to bypass that
project's task-intake, task-switch, task-finish, access rules, or skill
selection.

## Required content

`index.md` lists only the local-router purpose, area IDs, one-line boundaries,
and links to the area files. Each `areas/<id>.md` lists the area purpose,
included paths or concepts, exclusions, relationships to other areas, and the
smallest suggested context to read first. Do not copy source code, credentials,
task history, or source transcripts.

When a request spans areas, retain one project task and follow the existing
task-switch process only if the project's task rules require it. The local
router itself creates no separate current task.

## Russian proposal template

```text
Режим: review
Проект: <project-id>
Путь: <exact-confirmed-path>

Предлагаю локальный роутер для <N> независимых стабильных областей:
- <area-id> — <граница и причина стабильности>.

Будут созданы только:
- ai/local-router/index.md
- ai/local-router/areas/<area-id>.md

Текущая задача проекта не будет заменена; для областей отдельные задачи не
создаются. Подтвердите architecture-update для указанных файлов.
```
