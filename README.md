# AI Dev Architecture Template

Переиспользуемая архитектура одиночной AI-разработки для проектов, где используются Codex, Claude Code или другие coding agents.

Главная идея:

- хранить важный контекст в репозитории, а не только в чате;
- переходить между AI-агентами без потери контекста задачи;
- тратить меньше токенов;
- не копить скрытый технический долг;
- отделять проектные правила от универсальных правил работы агента.

## Структура репозитория

```text
template/
  AGENTS.md
  CLAUDE.md
  ai/
    architecture.md
    current-task.md
    project-context.md
    decisions.md
    changelog.md
    skills/
      bugfix-workflow/SKILL.md
      ui-review/SKILL.md
      security-review/SKILL.md
      release-check/SKILL.md
      copy-review/SKILL.md
      write-tests/SKILL.md
      task-finish/SKILL.md
      task-switch/SKILL.md
      architecture-update/SKILL.md
      environment-check/SKILL.md

docs/
  concepts.md
  install.md
  update.md
  file-roles.md
  prompts.md

scripts/
  install.sh
```

## Быстрая установка в проект

Один раз склонируй репозиторий шаблона:

```bash
cd ~/Documents
git clone git@github.com:zykovsrg/ai-dev-architecture-template.git
```

Перейди в проект:

```bash
cd /path/to/project
```

Скопируй шаблонные файлы без перезаписи существующих файлов:

```bash
rsync -av --ignore-existing ~/Documents/ai-dev-architecture-template/template/ ./
```

После этого заполни проектные файлы:

- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
- `ai/current-task.md`

## Источник правды

Этот GitHub-репозиторий — источник правды для архитектуры.

- `README.md`
- `CHANGELOG.md`
- `docs/`
- `template/`

## Главные понятия

- `AGENTS.md` — входной файл для Codex.
- `CLAUDE.md` — входной файл для Claude Code.
- `ai/current-task.md` — текущая задача.
- `ai/project-context.md` — проектный контекст и инварианты.
- `ai/skills/*/SKILL.md` — переиспользуемые процедуры.
- `task-finish` — проверяет, можно ли закрыть задачу, и чистит контекст после подтверждения.
- `architecture-update` — меняет правила AI-разработки только после явного подтверждения.

Простые объяснения терминов — в `docs/concepts.md`.

## Skill precedence

Project architecture files define workflow priority:

1. `AGENTS.md` / `CLAUDE.md`
2. `ai/current-task.md`
3. relevant base skill
4. expected external skills/tools
5. controlled external methodologies

External skills and tools are helpers. They must not override work mode, confirmation rules, task-finish, architecture-update, or the clean architecture principle. Superpowers is gated and must not activate unless the user explicitly allows it.


## Work modes and environment check

The architecture has four work modes:

- `implementation`
- `review`
- `task-finish`
- `architecture-update`

`environment-check` is not a work mode. It is a first-session availability check for required base skills and expected external tools.


## Task switching

If `ai/current-task.md` has an unfinished task and the user asks for a different task, the agent must not overwrite it silently.

The agent should use `task-switch`, show the current task, the new task, the risk of switching, and ask for confirmation.

Paused tasks are stored briefly in `ai/paused-tasks.md`.

A request is treated as a different task when it changes the goal, work mode, main files, Done criteria, or creates a separate deliverable.
