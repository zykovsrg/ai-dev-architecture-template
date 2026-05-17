# Архитектура AI-разработки

Version: 5.3

Этот файл — короткий индекс всей системы разработки. Его не нужно загружать для каждой задачи. `ai/architecture.md` — справочник по workflow и иерархии правил. Читай его только если задача касается архитектуры, workflow, конфликтов правил или если правило неясно.

## Главная идея

Контекст должен жить в репозитории, а не только в чате.

- Чат — временная рабочая память.
- `AGENTS.md` и `CLAUDE.md` — короткие входные файлы для AI-агентов.
- `ai/current-task.md` хранит текущую задачу.
- `ai/project-context.md` хранит проектный контекст.
- `ai/skills/*/SKILL.md` хранит переиспользуемые процедуры.
- Git хранит полную историю изменений.

## Режимы работы

Before starting task work, the agent must explicitly state the mode as `Mode: ...`.

- `implementation` — менять код, проектные файлы, тесты или рабочую память задачи.
- `review` — читать файлы, проверять состояние проекта или diff, пересказывать контекст, сообщать о проблемах или предлагать следующий шаг; не редактировать файлы.
- `task-finish` — проверять завершение задачи и чистить контекст только после подтверждения.
- `architecture-update` — предлагать изменения архитектуры разработки, но не менять файлы без подтверждения.

If the mode is unclear, the agent must ask or state the assumption before acting.

Use `review` when the agent only reads files, summarizes context, inspects project state, runs `environment-check`, or suggests the next step without editing.

Use `implementation` only when the agent is going to change application code, project files, tests, or task memory.

If implementation or review suggests the current task may be complete, the agent must not declare the task closed. It must propose `task-finish` and wait for user confirmation.

## Session start check

`environment-check` is not a work mode.

`task-switch` is also not a work mode. It is a safety workflow for switching between unfinished tasks.

At the start of a new project session, use `environment-check` to check whether required base skills and expected external skills/tools are available.

When entering an existing project, switching tools, or continuing in a new chat, run `environment-check` before suggesting next steps or starting implementation. Do not skip it unless the user explicitly says not to run it.

This check is not a deep audit. It is a quick availability check.

Required base skills:

- `bugfix-workflow`
- `ui-review`
- `security-review`
- `release-check`
- `copy-review`
- `write-tests`
- `task-finish`
- `task-switch`
- `architecture-update`
- `environment-check`

Expected external skills/tools:

- `code-review-graph`
- `agent-skills-for-context-engineering`
- `claude-seo`

Controlled external methodologies:

- `Superpowers`

Rules:

- Do not install missing tools automatically.
- Do not fail the session if external tools are missing.
- Clearly separate missing required files, missing expected external tools, and controlled methodologies.
- If a required base skill is missing, tell the user which file is missing and suggest restoring it from the template.
- If an external tool is missing, report it as a warning, not a blocker.
- If an external tool cannot be verified, report it as `not confirmed`.
- Do not load all skill contents during the check; verify file presence first.

After `environment-check`, continue in one of the work modes:

- `implementation`
- `review`
- `task-finish`
- `architecture-update`

## Основные файлы

### AGENTS.md

Входной файл для Codex.

Должен быть коротким: только правила первого уровня, маршрутизация контекста, триггеры skills, режимы работы и формат ответа.

### CLAUDE.md

Входной файл для Claude Code.

По смыслу должен совпадать с `AGENTS.md`.

### ai/current-task.md

Одна текущая задача.

Должен быть коротким: примерно один экран.

### ai/paused-tasks.md

Короткий список задач, которые поставили на паузу через `task-switch`.

Это не backlog. Используй только для незавершённых задач, к которым нужно вернуться.

### ai/project-context.md

Проектный контекст:

- что это за проект;
- стек;
- команды запуска, сборки и тестов;
- важные папки и файлы;
- главные экраны или модули;
- модель данных или ключевые сущности;
- инварианты проекта;
- хрупкие зоны.

Ориентир — до 150 строк.

### ai/decisions.md

Только важные активные решения.

Используй для архитектурных решений, продуктовых правил, ограничений модели данных и решений, которые будущие агенты не должны случайно сломать.

Не используй для мелких багфиксов, цветов, отступов или обычной истории изменений.

### ai/changelog.md

Последние заметные изменения проекта.

Храни последние 2–4 недели. Старые записи переноси в `ai/archive/`.

### ai/external-tools.md

Список ожидаемых внешних skills, tools и controlled methodologies.

Используется при `environment-check`.

Отсутствие внешних tools — предупреждение, а не блокер.

## Язык общения и файлов

Постоянные файлы инструкций для ИИ должны быть на английском:

- `AGENTS.md`
- `CLAUDE.md`
- `ai/skills/*/SKILL.md`

Рабочие файлы памяти проекта можно вести на русском или английском:

- `ai/current-task.md`
- `ai/project-context.md`
- `ai/architecture.md`
- `ai/decisions.md`
- `ai/changelog.md`

Агент должен общаться с пользователем на русском и объяснять технические термины простыми словами.

## Skills

Базовые skills:

- `bugfix-workflow` — исправление багов и регрессий.
- `ui-review` — проверка изменений интерфейса.
- `security-review` — проверка рисков безопасности.
- `release-check` — проверка перед коммитом, merge, сборкой или релизом.
- `copy-review` — проверка интерфейсных текстов.
- `write-tests` — решение, нужны ли автотесты, и создание тестов для рискованных изменений.
- `task-finish` — закрытие задачи и чистка контекста после подтверждения.
- `task-switch` — безопасное переключение между незавершёнными задачами без потери контекста.
- `architecture-update` — обновление архитектуры разработки после одобрения пользователя.
- `environment-check` — проверка установки архитектуры, базовых skills и внешних tools.

Use skills by trigger. Do not load all skills automatically. Open only the skill that matches the current task.

### Optional project skills

Optional project skills may be installed only in projects where they are useful. They are not required base skills and must not make `environment-check` fail when absent.

- `frontend-design` — optional project skill for UI composition, visual hierarchy, frontend component design, and UX improvements. Use only for UI/frontend/design tasks when `ai/skills/frontend-design/SKILL.md` is installed.

Внешние skills и инструменты не заменяют базовые skills.

Expected external skills/tools:

- `code-review-graph` — основной инструмент для анализа связей в коде, code review и blast-radius analysis.
- `agent-skills-for-context-engineering` — дополнительные skills для работы с контекстом.
- `claude-seo` — SEO-набор skills.

Controlled external methodologies:

- `Superpowers` — усиленная методология разработки. Проверяется при первом запуске, но используется только после явного разрешения.

## Приоритет скиллов

Иерархия управления процессом:

1. `AGENTS.md` / `CLAUDE.md`
2. `ai/current-task.md`
3. релевантный базовый skill
4. optional project skills and expected external skills/tools
5. controlled external methodologies

Optional project skills, external skills and tools help the agent, but do not control the workflow. They must not override work mode, confirmation rules, `task-finish`, `architecture-update`, `environment-check`, clean architecture principle, or project-specific rules in `ai/project-context.md`.

## Контекст и токены

Не читай всю папку `ai/` автоматически.

Минимальный контекст по умолчанию:

- `AGENTS.md` или `CLAUDE.md`
- `ai/current-task.md`

Читай `ai/project-context.md` только если задача касается проектного поведения, архитектуры, storage, экранов или если это просит `current-task`.

Читай `ai/decisions.md` только для архитектурно чувствительных задач.

Читай `ai/architecture.md` только если задача касается workflow, архитектуры разработки, конфликтов правил, architecture-update или если правило неясно.

Для plan-driven или Superpowers-задач читай только релевантные файлы:

- `docs/superpowers/specs/<spec>.md`
- `docs/superpowers/plans/<plan>.md`
- при необходимости — этот раздел архитектуры про plan-driven работу.

Используй skills только по триггеру. Не загружай все skills автоматически.

Не читай `ai/archive/` без конкретной причины.

## Формат общения перед изменениями

Перед редактированием агент должен:

1. Явно назвать режим: `Mode: ...`.
2. Коротко объяснить простыми словами, что будет делать дальше.
3. Назвать важный риск, только если он есть.

Не перечисляй технические файлы перед редактированием, если это не помогает пользователю понять изменение или пользователь сам не попросил список файлов.

## Контроль scope

Не расширяй scope, который подтвердил пользователь.

Если во время реализации становится полезно сделать больше, остановись и спроси пользователя перед добавлением нового объёма.

Пример: если пользователь подтвердил импорт одного CSV, не добавляй импорт трёх CSV без отдельного подтверждения.

## Формат отчёта после изменений

После редактирования агент должен:

1. Начать отчёт с использованного режима, например `Mode: implementation`.
2. Кратко описать, что изменилось.
3. Перечислить ручные проверки.
4. Назвать риски или незавершённые части.
5. Явно сказать, менялась ли task memory.
6. Если задача выглядит завершённой, предложить `task-finish`, а не объявлять задачу закрытой.

Если task memory менялась, агент должен перечислить точные файлы:

- `ai/current-task.md`
- `ai/changelog.md`
- `ai/decisions.md`
- `ai/project-context.md`
- `ai/paused-tasks.md`

## Принцип чистой архитектуры

Не копи технический долг и временные решения.

Временные решения допустимы только как исключение. Если workaround всё-таки используется:

1. Явно пометь его как temporary workaround.
2. Объясни, почему он нужен сейчас.
3. Объясни, какой риск он создаёт.
4. Добавь follow-up: что заменить, где и когда.
5. Реши, нужно ли записать это в `ai/changelog.md` или `ai/decisions.md`.

Не чини баг способом, который ухудшает модель данных, согласованность экранов или читаемость проекта.

Если чистое решение требует больше времени, предложи два варианта:

- быстрый безопасный фикс;
- правильное архитектурное решение.

## Plan-driven work with Superpowers

Этот раздел применяется только к задачам, которые явно ведутся через Superpowers planning, writing-plans, subagent-driven-development или похожий plan-driven workflow.

Обычные задачи не обязаны использовать эти правила.

### Источник правды по прогрессу

Для plan-driven работы `docs/superpowers/plans/<plan>.md` — источник правды по прогрессу выполнения плана.

- Не используй внутренний TodoWrite как единственный источник прогресса.
- После завершения каждой задачи плана обновляй чекбокс в `docs/superpowers/plans/<plan>.md`.
- Если задача плана частично выполнена, оставь чекбокс пустым и добавь короткую заметку под задачей.
- Если задача отменена или перенесена, явно пометь это в плане короткой строкой `Note:`.

Пример:

```markdown
- [x] Task 2 — Add app wrapper
  - Note: chose minimal wrapper over Xcode project to avoid restructuring Package.swift.
- [ ] Task 3 — Add UI smoke tests
  - Note: blocked until .app bundle launches reliably.
```

### Промежуточные решения

Мелкие judgment calls по ходу plan-driven работы фиксируй рядом с соответствующей задачей плана через короткую `Note:`.

Используй `ai/decisions.md` только для устойчивых архитектурных, продуктовых, workflow-решений или решений по модели данных.

Не дублируй одно и то же решение одновременно в plan notes, `ai/decisions.md` и `ai/changelog.md`.

Правило выбора места:

- `docs/superpowers/plans/<plan>.md` — мелкие решения и локальные причины внутри конкретной задачи плана.
- `ai/decisions.md` — решения, которые будущие агенты должны помнить вне текущего плана.
- `ai/changelog.md` — заметные итоговые изменения, а не каждый микрошаг.

### Commit convention

Для plan-driven коммитов используй проверяемую конвенцию:

```text
Plan Task <N>: <short action>
```

Примеры:

```text
Plan Task 1: add app bundle wrapper
Plan Task 2: add Info.plist generation
Plan Task 3: add UI smoke test target
Plan Cleanup: update task handoff
```

Проверка без специальных инструментов:

```bash
git log --oneline --grep="Plan Task"
git log --oneline --grep="Plan Cleanup"
```

Если коммит закрывает несколько задач плана, в сообщении укажи диапазон:

```text
Plan Tasks 4-5: add bundle smoke checks
```

Но по умолчанию предпочитай один логический plan task на один коммит.

### Handoff между агентами

Если агент останавливается посреди plan-driven выполнения, он должен оставить быстрый handoff в конце плана или в `ai/current-task.md`:

- последний завершённый plan task;
- следующий plan task;
- известные блокеры;
- последние релевантные коммиты.

Не создавай отдельный progress-файл без явной причины. Прогресс плана живёт в самом `docs/superpowers/plans/<plan>.md`.

## Task switching

Use `task-switch` when `ai/current-task.md` contains an unfinished task and the user asks for a different task.

Do not overwrite `ai/current-task.md` automatically.

First show:

1. Current unfinished task.
2. New requested task.
3. Risk of switching.
4. Options:
   - continue current task;
   - pause current task and start a new one;
   - finish current task through `task-finish`;
   - discard current task and replace it.

Only update `ai/current-task.md` after explicit user confirmation.

### Как понять, что задача другая

Новый запрос считается другой задачей, если:

1. Меняется цель.
2. Меняется work mode.
3. Меняются основные файлы или область проекта.
4. Меняются Done criteria.
5. Новый запрос не помогает завершить текущую задачу.
6. Новый запрос создаёт отдельный результат.
7. Текущая задача останется незавершённой после нового запроса.

Новый запрос считается продолжением текущей задачи, если он уточняет, сужает, тестирует, ревьюит или завершает текущую цель.

Если агент не уверен, он не должен угадывать. Нужно спросить пользователя:

```text
Похоже, это новая задача, а текущая ещё не закрыта. Переключаемся или продолжаем текущую?
```

If the current task is paused, write a short entry to `ai/paused-tasks.md`.

Do not use `ai/paused-tasks.md` as a backlog.

## Обновление архитектуры

Если нужно изменить переиспользуемое правило, workflow, ограничение проекта, skill или архитектурный принцип, используй `architecture-update`.

Перед изменением файлов покажи:

1. Что меняем.
2. На что меняем.
3. Точные файлы.
4. Точную формулировку.
5. Влияние на токены.
6. Почему это должно храниться именно там.

Затем спроси: `Replace this?`

Не обновляй файлы архитектуры без явного подтверждения пользователя.

## Ритм ревизии

После каждой задачи:

- обнови `ai/changelog.md`, если было заметное изменение;
- обнови `ai/decisions.md`, если появилось важное решение;
- очищай `ai/current-task.md` только после подтверждения пользователя.

Раз в неделю:

- сократи `ai/changelog.md`;
- старые записи перенеси в `ai/archive/`.

Раз в месяц:

- пересмотри `AGENTS.md` и `CLAUDE.md`;
- для каждой строки спроси: «Если удалить эту строку, агент начнёт ошибаться?»;
- если ответ «нет», удали строку;
- пересмотри skills и убери устаревшие или дублирующие правила.

## Superpowers gated use

Superpowers may be installed and checked, but it is a controlled external methodology.

Use Superpowers only when:

- the user explicitly asks to use it;
- `ai/current-task.md` says `Use Superpowers: yes`;
- the task is large, vague, risky, or requires design, TDD, or subagent-driven development.

If a task matches Superpowers triggers, do not activate Superpowers automatically. First explain why it may help and ask the user: `Use Superpowers for this task?`

Superpowers triggers include:

- large or vague tasks;
- architecture design;
- choosing between technical options;
- data model changes;
- migrations;
- TDD;
- subagents;
- major refactoring;
- unclear blast radius.

Do not use Superpowers for:

- small bugfixes;
- copy changes;
- simple UI tweaks;
- narrow tasks with known relevant files;
- `task-finish`;
- `environment-check`;
- `architecture-update`, unless the user explicitly asks.

Superpowers must not override:

- work mode;
- `ai/current-task.md`;
- user confirmation rules;
- `task-finish` rules;
- `environment-check` rules;
- `architecture-update` rules;
- clean architecture principle;
- project-specific rules in `ai/project-context.md`.

If Superpowers suggests a heavier workflow, first propose it to the user and ask for confirmation.
