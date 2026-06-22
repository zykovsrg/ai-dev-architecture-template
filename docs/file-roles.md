# Роли файлов

Этот документ объясняет, какие файлы относятся к правилам архитектуры, а какие — к рабочей памяти проекта.

## 1. Protected architecture files

Это правила игры для AI-агентов. Их нельзя менять в обычной задаче.

Файлы:

<!-- canon:protected-files -->
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/` (создаётся проектом по необходимости; в шаблоне отсутствует)
- `.codex/` (создаётся проектом по необходимости; в шаблоне отсутствует)
<!-- /canon:protected-files -->

`.claude/` и `.codex/` — это папки настроек самих инструментов (Claude Code и Codex): разрешения, свои команды, хуки. Это не инструкция для ИИ, а конфиг программы. В шаблоне их нет; они становятся защищёнными, только если вы их создадите.

Когда можно менять:

- только в режиме `architecture-update`;
- только после явного подтверждения пользователя;
- только если меняется workflow, базовое правило, skill, список tools или способ работы агента.

Внешние skills, init-команды и setup-инструменты могут предлагать изменения этих файлов, но не могут применять их без подтверждения.

## 2. Controlled memory files

Это рабочая память конкретного проекта и текущей задачи. Эти файлы можно менять, но только через подходящий workflow.

Файлы:

<!-- canon:controlled-memory -->
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
<!-- /canon:controlled-memory -->

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
| `ai/current-task.md` | `task-intake`, `implementation`, `task-switch`, `task-finish`; `task-intake` может записать первую задачу, но не перезаписывает незавершённую без `task-switch` |
| `ai/paused-tasks.md` | только `task-switch`; не использовать как backlog, future tasks или список cleanup-работ |
| `ai/future-tasks.md` | `implementation` после явной просьбы сохранить идею, `task-finish` после подтверждения кандидатов, `task-switch` при promotion |
| `ai/project-context.md` | после подтверждения, если изменились стек, команды, структура, модель данных, инварианты или хрупкие зоны |
| `ai/decisions.md` | `task-finish` или `architecture-update`, если появилось важное устойчивое решение |
| `ai/changelog.md` | `task-finish` после подтверждения; `architecture-update`, если этого требует одобренное изменение архитектуры |

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
- `ai/future-tasks.md`

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

В пустом шаблоне должны быть:

```text
Status: empty
Stage: intake
```

`Status` показывает состояние задачи:

- `empty`
- `active`
- `review`
- `blocked`
- `done`
- `paused`

`Stage` показывает этап работы:

- `intake`
- `spec`
- `planning`
- `implementation`
- `review`
- `task-finish`

Не записывай в `Status` свободный текст вроде `spec done, planning next`. Для этого есть `Stage` и handoff notes.

### `ai/paused-tasks.md`

Короткий список задач, которые временно поставили на паузу через `task-switch`.

Это не backlog, не список идей и не место для cleanup-работ.

### `ai/future-tasks.md`

Список идей и будущих задач, которые не входят в текущий scope.

Это backlog, но не активная работа.

Используй для:

- идей, которые появились во время реализации или ревью;
- non-blocking follow-up investigations;
- missing test seams, если они полезны, но не входят в текущую задачу;
- крупных улучшений или рефакторингов на потом;
- явных просьб пользователя: `запиши на потом`, `добавь в будущие задачи`, `потом надо сделать`.

Не используй для:

- незавершённой активной задачи — для этого `ai/paused-tasks.md`;
- истории уже сделанных изменений — для этого `ai/changelog.md`;
- устойчивых решений — для этого `ai/decisions.md`;
- блокирующей уборки, без которой нельзя закрыть текущую задачу.

### `ai/project-context.md`

Постоянный контекст проекта:

- стек;
- команды запуска, сборки и тестов;
- важные папки;
- экраны или модули;
- модель данных;
- инварианты;
- хрупкие зоны.

Если агент обнаружил устаревший project-context, он должен предложить отдельный update после подтверждения, а не просто упомянуть это в changelog.

### `ai/decisions.md`

Только важные активные решения.

Используй для решений, которые будущие агенты не должны случайно сломать.

Примеры:

- data model invariant;
- storage path или migration rule;
- signing, sandboxing, entitlements, deployment или local setup requirement;
- undo или redo invariant;
- sync behavior;
- recurrence, scheduling или time logic;
- architecture boundary;
- agent workflow rule that must persist across sessions.

Не используй для мелких багфиксов, цветов, отступов и обычной истории изменений.

### `ai/changelog.md`

Последние заметные изменения проекта.

Ориентир — хранить последние 2–4 недели. Старые записи переносить в `ai/archive/`.

`changelog` отвечает на вопрос: что изменилось.

`decisions` отвечает на вопрос: что нельзя забыть и сломать в будущем.

`future-tasks` отвечает на вопрос: что можно сделать позже, но не надо смешивать с текущей задачей.

### `ai/external-tools.md`

Список ожидаемых внешних skills, tools и controlled methodologies.

Нужен для `environment-check`.

Отсутствие optional tools — предупреждение, а не блокер.

### `ai/skills/*/SKILL.md`

Переиспользуемые процедуры.

Не нужно загружать все skills сразу. Открывай только тот skill, который нужен для текущей задачи.

Если задача попадает под trigger skill, агент должен открыть актуальный файл skill. Не работай по памяти.

## 7. Связанные workflows

### `environment-check`

Проверяет установку архитектуры, базовые skills, expected external tools и controlled methodologies.

Это не work mode и не глубокий аудит.

Запускается при новой сессии, новом чате, смене tools/агента и после compressed context или restored summary.

После проверки агент должен вывести короткое меню доступных следующих commands и skills. Это меню справочное: оно не запускает `task-switch`, `task-finish`, `architecture-update` или другие workflow автоматически.

### `task-intake`

Принимает новую рабочую задачу.

Используется перед реальной работой после `environment-check`.

Если `ai/current-task.md` пустой, записывает новую задачу в текущую память.

Если текущая задача не завершена, а пользователь просит другую, передаёт управление в `task-switch`.

Если пользователь просит сохранить идею на потом, не делает её текущей задачей, а использует `ai/future-tasks.md`.

### `task-switch`

Защищает `ai/current-task.md` от случайной перезаписи.

Используется, когда текущая задача не завершена, а пользователь просит перейти к другой.

Также используется, когда пользователь явно продвигает запись из `ai/future-tasks.md` в текущую задачу.

### `task-finish`

Проверяет, можно ли закрыть задачу.

После подтверждения пользователя может обновить `ai/changelog.md`, `ai/decisions.md`, подтверждённые записи в `ai/future-tasks.md` и очистить `ai/current-task.md`.

После cleanup результат должен быть сохранён: push на GitHub, если GitHub настроен, или local-only fallback, если GitHub недоступен.

### `release-check`

Проверяет готовность к commit, merge, build или release.

Для сложных изменений должен проверить необходимость `code-review-graph`.

### Superpowers for bugs and complex tasks

Локальный `bugfix-workflow` больше не используется.

Баги, краши, регрессии, flaky behavior, debug requests, performance-проблемы и сложные задачи должны идти через Superpowers, если он доступен.

Если Superpowers отсутствует, агент должен сказать об этом и спросить, установить/настроить его или продолжать вручную.
