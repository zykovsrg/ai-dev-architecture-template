# Роли файлов

Этот документ объясняет, какие файлы относятся к правилам архитектуры, а какие — к рабочей памяти проекта.

## 1. Protected architecture files

Это правила игры для AI-агентов. Их нельзя менять в обычной задаче.

Файлы:

- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`

Когда можно менять:

- только в режиме `architecture-update`;
- только после явного подтверждения пользователя;
- только если меняется workflow, базовое правило, skill, список tools или способ работы агента.

Внешние skills, init-команды и setup-инструменты могут предлагать изменения этих файлов, но не могут применять их без подтверждения.

## 2. Controlled memory files

Это рабочая память конкретного проекта и текущей задачи. Эти файлы можно менять, но только через подходящий workflow.

Файлы:

- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`

## 3. Матрица прав на редактирование

| Файл | Когда можно менять |
|---|---|
| `AGENTS.md` | только `architecture-update` после подтверждения |
| `CLAUDE.md` | только `architecture-update` после подтверждения |
| `ai/architecture.md` | только `architecture-update` после подтверждения |
| `ai/external-tools.md` | только `architecture-update` или после подтверждённого изменения списка tools |
| `ai/skills/*/SKILL.md` | только `architecture-update` после подтверждения |
| `.claude/` | только `architecture-update` после подтверждения |
| `.codex/` | только `architecture-update` после подтверждения |
| `ai/current-task.md` | `implementation`, `task-switch`, `task-finish`; не перезаписывать незавершённую задачу без подтверждения |
| `ai/paused-tasks.md` | только `task-switch` после подтверждения |
| `ai/project-context.md` | после подтверждения, если изменились стек, команды, структура, модель данных, инварианты или хрупкие зоны |
| `ai/decisions.md` | `task-finish` или `architecture-update`, если появилось важное устойчивое решение |
| `ai/changelog.md` | `task-finish` или заметное изменение в рамках реализации |

## 4. Шаблонные файлы

Эти файлы обычно одинаковы для разных проектов:

- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`

## 5. Проектные файлы

Эти файлы нужно заполнять под конкретный проект:

- `ai/project-context.md`
- `ai/current-task.md`

Эти файлы можно оставить пустыми шаблонами до появления реальных данных:

- `ai/decisions.md`
- `ai/changelog.md`
- `ai/paused-tasks.md`

## 6. Роли основных файлов

### `AGENTS.md`

Короткий входной файл для Codex.

Хранит только правила первого уровня: режимы работы, маршрутизацию контекста, защиту файлов и формат ответа.

### `CLAUDE.md`

Короткий входной файл для Claude Code.

По смыслу должен совпадать с `AGENTS.md`.

### `ai/architecture.md`

Главный справочник по workflow.

Его читают, когда задача касается архитектуры разработки, конфликтов правил или режима `architecture-update`.

### `ai/current-task.md`

Одна текущая задача.

В пустом шаблоне должен быть статус `empty`. Активная задача получает статус `active`.

Допустимые статусы:

- `empty`
- `active`
- `review`
- `blocked`
- `done`
- `paused`

### `ai/paused-tasks.md`

Короткий список задач, которые временно поставили на паузу через `task-switch`.

Это не backlog и не список идей.

### `ai/project-context.md`

Постоянный контекст проекта:

- стек;
- команды запуска, сборки и тестов;
- важные папки;
- экраны или модули;
- модель данных;
- инварианты;
- хрупкие зоны.

### `ai/decisions.md`

Только важные активные решения.

Используй для решений, которые будущие агенты не должны случайно сломать.

Не используй для мелких багфиксов, цветов, отступов и обычной истории изменений.

### `ai/changelog.md`

Последние заметные изменения проекта.

Ориентир — хранить последние 2–4 недели. Старые записи переносить в `ai/archive/`.

### `ai/external-tools.md`

Список ожидаемых внешних skills, tools и controlled methodologies.

Нужен для `environment-check`.

Отсутствие optional tools — предупреждение, а не блокер.

### `ai/skills/*/SKILL.md`

Переиспользуемые процедуры.

Не нужно загружать все skills сразу. Открывай только тот skill, который нужен для текущей задачи.

## 7. Связанные workflows

### `environment-check`

Проверяет установку архитектуры, базовые skills, expected external tools и controlled methodologies.

Это не work mode и не глубокий аудит.

### `task-switch`

Защищает `ai/current-task.md` от случайной перезаписи.

Используется, когда текущая задача не завершена, а пользователь просит перейти к другой.

### `task-finish`

Проверяет, можно ли закрыть задачу.

После подтверждения пользователя может обновить `ai/changelog.md`, `ai/decisions.md` и очистить `ai/current-task.md`.
