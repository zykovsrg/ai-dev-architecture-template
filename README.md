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
    paused-tasks.md
    project-context.md
    decisions.md
    changelog.md
    external-tools.md
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
  start-prompts.md

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

После этого обязательно заполни:

- `ai/project-context.md`
- `ai/current-task.md`

В `ai/current-task.md` должны быть отдельные поля:

- `Status` — состояние задачи: `empty / active / review / blocked / done / paused`;
- `Stage` — этап работы: `intake / spec / planning / implementation / review / task-finish`.

Можно оставить пустыми шаблонами до появления реальных данных:

- `ai/decisions.md`
- `ai/changelog.md`
- `ai/paused-tasks.md`

`ai/external-tools.md` обычно не нужно менять после установки. Обновляй его только если меняется список ожидаемых внешних skills, tools или controlled methodologies.

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
- `ai/paused-tasks.md` — задачи, временно поставленные на паузу через `task-switch`.
- `ai/project-context.md` — проектный контекст и инварианты.
- `ai/decisions.md` — устойчивые решения и инварианты, которые будущие агенты не должны сломать.
- `ai/changelog.md` — последние заметные изменения.
- `ai/external-tools.md` — ожидаемые внешние tools и controlled methodologies.
- `ai/skills/*/SKILL.md` — переиспользуемые процедуры.
- `task-finish` — проверяет, можно ли закрыть задачу, и чистит контекст после подтверждения.
- `task-switch` — безопасно переключает незавершённые задачи.
- `architecture-update` — меняет правила AI-разработки только после явного подтверждения.
- `environment-check` — проверяет установку архитектуры и внешние tools.

Простые объяснения терминов — в `docs/concepts.md`.
Готовые стартовые промты — в `docs/start-prompts.md`.

## Architecture files and task memory

### Protected architecture files

Это правила архитектуры. Их нельзя менять в обычной задаче.

- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`

Меняются только через `architecture-update` и только после явного подтверждения.

### Controlled memory files

Это рабочая память проекта и задачи. Её можно менять, но только через подходящий workflow.

- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`

Примеры:

- `task-switch` может менять `ai/current-task.md` и `ai/paused-tasks.md` после подтверждения;
- `task-finish` может менять `ai/current-task.md`, `ai/changelog.md` и `ai/decisions.md` после подтверждения;
- `ai/project-context.md` меняется только если изменились стек, команды, структура, модель данных, инварианты или хрупкие зоны.

## Skill routing

Если задача попадает под trigger skill, агент должен открыть актуальный `ai/skills/*/SKILL.md`. Не нужно применять skill по памяти.

- UI-задачи: `ui-review` + `write-tests`.
- Баги, краши, регрессии, performance: `bugfix-workflow`.
- Pre-merge или сложное review: `release-check`; если доступен и нужен — `code-review-graph`.
- Закрытие задачи: `task-finish`.
- Переключение задачи: `task-switch`.

## Skill precedence

Project architecture files define workflow priority:

1. `AGENTS.md` / `CLAUDE.md`
2. `ai/current-task.md`
3. relevant base skill
4. expected external skills/tools
5. controlled external methodologies

External skills and tools are helpers. They must not override work mode, confirmation rules, task-finish, architecture-update, environment-check, protected architecture file rules, controlled memory rules, or the clean architecture principle. Superpowers is gated and must not activate unless the user explicitly allows it.

## Work modes and environment check

The architecture has four work modes:

- `implementation`
- `review`
- `task-finish`
- `architecture-update`

`environment-check` is not a work mode. It is an availability check for required base skills and expected external tools.

Run `environment-check` when entering an existing project, switching tools or agents, continuing in a new chat, or continuing after compressed context, compacted context, restored summary, or conversation summary continuation.

## Task switching

If `ai/current-task.md` has an unfinished task and the user asks for a different task, the agent must not overwrite it silently.

The agent should use `task-switch`, show the current task, the new task, the risk of switching, and ask for confirmation.

Paused tasks are stored briefly in `ai/paused-tasks.md`.

A request is treated as a different task when it changes the goal, work mode, main files, Done criteria, or creates a separate deliverable.
