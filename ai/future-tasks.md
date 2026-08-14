# Future Tasks

Use this file for ideas and future implementation tasks that are not part of the current task scope.

This is a backlog, not active work.

## Rules

- Do not implement these tasks unless the user explicitly promotes one to the current task.
- Do not use this file for paused active work. Use `ai/paused-tasks.md` for interrupted unfinished tasks.
- Do not use this file for completed change history. Use `ai/changelog.md` for what changed.
- Do not use this file for durable architecture or product decisions. Use `ai/decisions.md` for rules future agents must not break.
- Keep entries short, actionable, and linked to the context where they appeared.
- If a future task becomes active, copy it into `ai/current-task.md` and mark the original entry as `promoted`. When that task is closed through `task-finish`, its entry is deleted from this file; the trace stays in `ai/changelog.md`.

## Statuses

```text
idea / ready / blocked / promoted / done / dropped
```

## Template

### FT-YYYYMMDD-001 — Task title

Status: idea

Priority: low / medium / high

Source: where the idea appeared

Created: YYYY-MM-DD

Context:

Short context: why this may be useful later.

Proposed task:

What should be implemented later.

Acceptance criteria:

- How to know this future task is done.

Promotion notes:

What to check before moving this task to `ai/current-task.md`.

## Future tasks

### FT-20260814-001 — Проверка автоматического создания приватного репозитория

Status: ready

Priority: medium

Source: решение пользователя, сессия 2026-08-14

Created: 2026-08-14

Context:

Новые проекты должны получать отдельный локальный Git и, при доступной авторизации GitHub, приватный репозиторий с именем project ID.

Proposed task:

Проверить обновлённый project-create на следующем одобренном новом проекте.

Acceptance criteria:

- При авторизованном gh создаются локальный Git, приватный GitHub-репозиторий и push main.
- При недоступном GitHub результат явно содержит pending-sync и не заявляет об успешной синхронизации.

Promotion notes:

Проверить статус Git и remote после создания.

### FT-20260813-001 — Отказ от legacy standalone-режима

Status: ready

Priority: medium

Source: решение пользователя при проектировании knowledge layer, сессия 2026-08-13

Created: 2026-08-13

Context:

Рабочая архитектура использует единственную точку входа — Personal AI Hub. Standalone-режим остаётся в шаблоне как legacy-совместимость, но не является частью повседневного маршрута.

Proposed task:

Спроектировать и отдельно согласовать отказ от legacy standalone-режима: влияние на шаблон, installer/updater, документацию, существующие установки и миграцию пользователей.

Acceptance criteria:

- Есть подтверждённый план миграции и обратимости.
- Не нарушены project routing, изоляция памяти и сохранность существующих проектов.
- Удаление или архивирование legacy-файлов требует отдельных явных подтверждений.

Promotion notes:

Сначала провести инвентаризацию актуальных standalone-потребителей без чтения их проектных данных.

### FT-20260812-001 — Провести локальную миграцию в Personal AI Hub

Status: ready

Priority: high

Source: реализация Personal AI Hub, сессия 2026-08-12

Created: 2026-08-12

Context:

Шаблон hub выпущен, но локальная папка проектов ещё не инвентаризирована и не подключена к `_ai-hub`.

Proposed task:

Создать `_ai-hub`, выполнить только инвентаризацию имён прямых папок в согласованном корне, предложить регистрацию каждого проекта и отдельно preview миграции standalone-проектов. Не перемещать, не архивировать и не удалять папки.

Acceptance criteria:

- `_ai-hub` установлен с явно подтверждённым allowed root.
- Ни один проект не прочитан или зарегистрирован без отдельного подтверждения.
- Для каждого standalone-проекта показан отдельный read-only preview миграции.

Promotion notes:

Подтвердить путь allowed root и решить, с каких папок начать регистрацию.

### FT-20260726-002 — Настроить самопроверку архитектуры по запросу

Status: idea

Priority: medium

Source: пожелание пользователя, сессия 2026-07-26

Created: 2026-07-26

Context:

Нужен механизм, который по явному запросу анализирует диалог и помогает понять, что следует скорректировать в архитектуре разработки.

Proposed task:

Спроектировать и реализовать workflow самопроверки: анализировать диалог, выявлять повторяющиеся проблемы, несоответствия текущим правилам и пробелы в архитектуре, а затем выдавать понятные рекомендации по корректировкам.

Acceptance criteria:

- Есть явная команда или запрос для запуска самопроверки.
- Результат содержит найденные наблюдения, связанные с конкретными правилами или файлами архитектуры.
- Для каждой рекомендации указаны приоритет, обоснование и предложенное изменение.
- Самопроверка не изменяет архитектурные файлы автоматически без подтверждения пользователя.

Promotion notes:

Перед началом определить формат отчёта, границы анализируемого диалога и список архитектурных файлов, которые можно рекомендовать к изменению.

### FT-20260712-001 — Сделать интерфейс под macOS для архитектуры

Status: idea

Priority: medium

Source: пожелание пользователя, сессия 2026-07-12

Created: 2026-07-12

Context:

Сейчас архитектура — это только текстовые файлы (markdown) и командная строка/AI-агент. Пользователь хочет нативный macOS-интерфейс для работы с ней.

Proposed task:

Спроектировать и реализовать нативное macOS-приложение (или lightweight UI) для просмотра/редактирования файлов памяти (`ai/current-task.md`, `ai/future-tasks.md`, `ai/decisions.md`, `ai/changelog.md`), запуска ключевых workflow (`environment-check`, `task-intake`, `task-finish`) и, возможно, визуализации текущего состояния задачи без обязательного захода в AI-агента.

Acceptance criteria:

- Определена область: просмотр только / просмотр+редактирование / запуск команд.
- Есть базовый прототип, показывающий текущую задачу и меню доступных команд.

Promotion notes:

Нужно сначала уточнить с пользователем объём (просмотр vs полноценное приложение) и стек (SwiftUI vs Electron vs web-обёртка) перед стартом реализации — это архитектурное решение, требует отдельного планирования.
