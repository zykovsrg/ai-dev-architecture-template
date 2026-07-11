---
name: start-screen
type: knowledge
description: |
  Show a short plain-language introduction to the AI development architecture and the current project task.
  Activates when the user explicitly asks "покажи стартовый экран", "с чего начать", "как работать с архитектурой", "что умеет эта архитектура", or similar.
  Does NOT activate automatically at session start, during environment-check, or for a request to list every installed skill or tool.
---

# Start Screen

Use this skill only after an explicit user request. It is a read-only orientation screen, not a workflow and not an environment audit.

## Read

- `ai/current-task.md`
- `ai/future-tasks.md`
- `ai/external-tools.md`

Use the currently available skill/tool catalog when the platform exposes one. If availability cannot be verified, describe only the configured project categories and label external availability as not confirmed.

## Output principles

- Write in Russian for a non-developer.
- Use information style: short sentences, concrete verbs, no promotional filler.
- Keep the whole answer close to one normal screen.
- Explain technical terms in plain language or omit them.
- Show categories and important examples, not the full skill catalog.
- End with the live current-task snapshot.
- Do not repeat the full `environment-check` report.

## Required sections

Use these headings and adapt the content to the current project:

### Что это

Explain in no more than two short sentences that the architecture keeps project context in files, helps AI agents continue work without losing task state, and protects scope.

### Как идёт работа

Explain briefly:

- project memory lives in `ai/` files;
- one task is current;
- unfinished work can be paused;
- future ideas are saved separately;
- task completion requires user confirmation and a saved result.

### С чего начать

Show no more than six useful commands:

- `task-intake` — start and record a new task;
- `task-switch` — pause, resume, or switch work;
- `task-finish` — verify and finish the current task after confirmation;
- `environment-check` — check architecture files and external capabilities;
- `start-screen` — show this screen again;
- "Покажи все skills и инструменты" — show the full catalog separately.

### Что доступно

Use compact categories:

- project workflows for tasks, reviews, tests, security, releases, and architecture changes;
- optional or external skills for specialized work;
- external tools for code analysis and controlled methodologies such as Superpowers, only when present or configured.

Do not print every skill name. Offer the full-catalog request instead.

### Как удалить

Say that removal is a separate confirmed operation. Tell the user to ask "Помоги удалить архитектуру". Before deletion, the agent must show the affected files, offer to preserve or back up project memory, distinguish rules from task history, and request explicit confirmation. Link to `docs/uninstall.md` when it exists. Never delete anything while showing the start screen.

### Сейчас в проекте

For `ai/current-task.md`, show only:

- short goal;
- `Status`;
- `Stage`;
- next step or blocker.

If `Status: empty`, say there is no active task and suggest `task-intake`.

For future tasks, mention only the count when easy to determine. Do not print the backlog.

## Safety

- Do not edit files.
- Do not activate `task-intake`, `task-switch`, `task-finish`, installation, update, or removal automatically.
- Do not claim an external tool is installed unless availability is verified.
- Do not expose secrets, raw configuration, or full task-memory files.
