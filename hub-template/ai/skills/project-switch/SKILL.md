---
name: project-switch
description: Switch between registered projects without turning a project switch into a task switch.
---

# Project Switch

Use this skill only when the user asks to leave a confirmed project for another
project. A project switch is not a task switch. It must not modify the current task, pause a task, replace a task, or edit either project's task memory.

## Procedure

1. Return to `Mode: routing`. Read the hub registry and active-project record
   only. Display the current registered project and path, plus the requested
   registered project and exact path.
2. Warn that unfinished work remains in its current project unchanged. If the
   current task's completion state is not already known from the confirmed
   project context, say that it is unknown rather than reading a project file
   before confirmation.
3. Request explicit confirmation of the new project ID and exact registered
   path. Do not read the new project's files, memory, or instructions before
   that confirmation.
4. After confirmation, perform canonical path validation by running
   `scripts/check-hub-registry.sh` for the hub and confirming that the selected
   registry path still matches the displayed record and remains under allowed
   roots. Stop on a failed validation or mismatch.
5. Update `ai/active-project.md` only with the confirmed, non-secret project
   ID and canonical registered path. This update is a selection record, not a
   task update.
6. Enter the confirmed project. Run the hub-owned `environment-check` against
   its `ai/` memory, then hand the user's requested work to the hub-owned
   `task-intake` workflow. That workflow routes a different unfinished task to
   the hub-owned `task-switch` or `task-finish` workflow when needed. Do not
   require or read duplicated project `AGENTS.md` or `CLAUDE.md` files.

If the user asks to carry unfinished work across projects, stop and ask for
separate confirmations and an explicit, sanitized handoff plan. Never copy
task memory across project boundaries.

## Russian confirmation template

```text
Текущий проект: <current-id> — <current-path>
Новый проект: <new-id> — <new-path>
Режим: routing

Незавершённая задача в текущем проекте не будет поставлена на паузу, заменена или изменена. Подтвердите переход: «Переключить на <new-id> по пути <new-path>».
```

After a valid confirmation, show `Project: <new-id>` and the selected project's
mode before project work begins.
