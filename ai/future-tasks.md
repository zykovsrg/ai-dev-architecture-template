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

### FT-20260827-001 — Три улучшения knowledge-слоя по мотивам статьи о personal brain

Status: promoted

Priority: medium

Source: разбор статьи braintools.ru/article/34725, сессия 2026-08-27

Created: 2026-08-27

Context:

Статья описывает личную систему памяти для агентов на Markdown-карточках. Большая
часть её идей у нас уже есть: карточки, индекс, Git-история, статусы `stale` и
`superseded`, запрет секретов, skills `knowledge-capture` и `knowledge-review`.
Полезны три вещи, которых у нас нет. Перечислены по убыванию пользы, каждую можно
делать отдельно.

Proposed task:

1. Поле `origin` в шаблоне записи знаний. Значения: `stated` (пользователь сказал
   прямо), `inferred` (модель вывела из контекста), `observation` (слабый сигнал).
   Даёт возможность отличить факт от догадки модели при чтении старой записи.
   Правки: `knowledge/record-template.md`, раздел про формат в `knowledge/README.md`,
   skills `knowledge-capture` и `knowledge-review` (заполнять и проверять поле).

2. Корзина входящих для слабых сигналов. Отдельное место, куда `knowledge-capture`
   складывает неподтверждённые наблюдения вместо записи их как знания или потери.
   `knowledge-review` разбирает корзину: повысить до записи, оставить, выбросить.
   Сначала решить, новый ли это файл или расширение `ai/cross-project-signals.md`.

3. Поле `valid_from` в шаблоне записи. Дата, с которой правило действует, отдельно
   от `created`. Нужно для записей типа `decisions`, где процесс менялся во времени.

Acceptance criteria:

- В `record-template.md` есть `origin` с перечисленными тремя значениями и
  `valid_from`; оба описаны в `knowledge/README.md`.
- `knowledge-capture` заполняет `origin` осознанно, а не ставит `stated` по умолчанию.
- `knowledge-review` показывает записи с `origin: inferred` отдельно от `stated`.
- Определено место корзины входящих и правило её разбора.
- Изменения синхронизированы между корнем и `template/`; `bash scripts/check-consistency.sh` проходит.

Promotion notes:

Пункты 1–3 независимы. Если делать что-то одно, делать пункт 1 — остальные два
дают заметно меньше. Перед пунктом 2 проверить, не покрывает ли задачу уже
`ai/cross-project-signals.md`, чтобы не плодить сущность. Пункт 3 не начинать
раньше пункта 1, чтобы не править шаблон дважды.

Promotion status: promoted to `ai/current-task.md` on 2026-08-28; user selected the full three-part implementation.

### FT-20260826-002 — Безопасный read-only пилот Apple Calendar MCP

Status: idea

Priority: medium

Source: утверждённая дорожная карта unified assistant, сессия 2026-08-26

Created: 2026-08-26

Context:

Calendar следует после рабочих workflows и требует отдельного разрешения:
EventKit читает календарные данные с широким доступом. MCP сам по себе не
заменяет policy wrapper и пользовательское подтверждение.

Proposed task:

После завершения FT-20260826-001 предложить установку и настройку Apple
Calendar MCP только для выбранного тестового календаря. Сначала реализовать
read-only preview событий и доступных слотов; create/update — отдельный этап,
delete остаётся выключен.

Acceptance criteria:

- Пользователь отдельно подтвердил установку, доступ и тестовый календарь.
- Read-only путь показывает timezone и точный источник данных.
- Нет создания, изменения или удаления Calendar-событий.
- Ошибки недоступного календаря и отсутствия разрешения проверены тестами.

Promotion notes:

Не начинать без отдельного явного подтверждения установки MCP и доступа к
Calendar. Сначала закончить workflows из FT-20260826-001.

### FT-20260822-002 — Привести текущее хранилище Obsidian к формату архитектуры

Status: idea

Priority: medium

Source: запрос пользователя, сессия 2026-08-22

Created: 2026-08-22

Context:

У пользователя уже есть vault Obsidian со своей структурой. Она не совпадает с
форматом памяти архитектуры, поэтому синхронизация без уборки даст кашу.

2026-08-26: read-only инвентарь завершён. Рабочая локальная копия находится в
`obsidian-vault/` и исключена из Git. Проверены новая Kanban-доска задач и
таблица проектов; старые экспериментальные `Projects-Kanban.*` заменены новыми
видами. Перенос заметок, медиа и старых Kanban ещё не начинался.

Proposed task:

Постепенно переносить существующие материалы vault небольшими
content-aware-пакетами. Для каждого пакета сначала классифицировать каждый
файл: оставить на месте, поместить в общую базу знаний, связать с одним
проектом или отправить в архив. Только после показа точного diff и отдельного
подтверждения выполнять запись. Старые чекбоксы и карточки Kanban не считать
каноническими задачами без ручной классификации.

Acceptance criteria:

- Есть карта «что где лежит сейчас» и «куда переезжает».
- Структура vault соответствует формату памяти архитектуры.
- Исходные заметки сохранены (архив или история), потери данных нет.
- Каждый шаг переноса подтверждён отдельно.
- Для каждого перенесённого пакета есть явная классификация и проверка ссылок.

Promotion notes:

Перенос отложен по решению пользователя. Когда пользователь вернётся к нему,
начать с небольшого read-only разбора датированных заметок встреч в корне vault.

### FT-20260815-003 — Три мелких замечания финального ревью правок аудита

Status: idea

Priority: low

Source: финальное ревью ветки hub-audit-fixes, сессия 2026-08-15

Created: 2026-08-15

Context:

Финальное ревью всей ветки признало шесть правок корректными, но нашло три
мелких недочёта. Их сознательно не чинили в той же ветке, чтобы не расширять
область: ревьюер оценил их как «можно выпускать как есть».

1. `--commit` не коммитит правку `.gitignore`. Файл не входит в `PROTECTED_FILES`
   и не попадает в `UPDATE_PATHS`, поэтому после `--commit` строка `/projects/`
   дописана на диске, но не закоммичена. Следующий `--apply` без `--allow-dirty`
   упрётся в «Working tree is not clean» из-за изменения, которое сам обновлятор
   и сделал. Разово и с понятным сообщением, но противоречит обещанию
   «коммитим только то, чем управляет обновлятор».
2. `--dry-run` не показывает предстоящее дописывание `.gitignore`. То есть
   `--apply` выполняет запись, которую предпросмотр не анонсировал. Ровно та
   нечестность, против которой затевалась вся ветка, только в мелком масштабе.
3. Предупреждение о незарегистрированной папке сравнивает имя папки с ID
   реестра, а не с basename зарегистрированного `Path`. Валидатор нигде не
   требует их совпадения. Запись `## foo` с `Path: <hub>/projects/foo-dir`
   пройдёт проверку и получит ложное предупреждение про `foo-dir`.

Proposed task:

Починить все три. Первые два — в `scripts/update-installed-hub.sh`: добавлять
`.gitignore` в `UPDATE_PATHS`, когда строка была дописана, и упоминать
предстоящее дописывание в выводе dry-run. Третий — в
`scripts/check-hub-registry.sh`: сравнивать имя папки с basename
зарегистрированного пути, а не с ID.

Acceptance criteria:

- После `--commit` рабочее дерево хаба чистое.
- `--dry-run` перечисляет дописывание `/projects/`, если оно предстоит.
- Проект с ID, не совпадающим с именем папки, не даёт ложного предупреждения.
- На каждое из трёх — мутационный тест: сломать, увидеть падение, вернуть.

Promotion notes:

Ни одно из трёх сегодня не проявляется: в живом хабе все 29 ID совпадают с
именами папок, а `.gitignore` уже содержит нужную строку. Это работа на
предупреждение, а не на исправление симптома.

### FT-20260815-001 — Почистить проекты под новую архитектуру

Status: ready

Priority: medium

Source: решение пользователя, сессия 2026-08-15

Created: 2026-08-15

Context:

В 15 проектах хаба лежат legacy standalone-копии архитектуры: собственные
`ai/architecture.md`, `AGENTS.md`, `CLAUDE.md` и наборы `ai/skills/`. Они
устарели — установлены версии 5.2, 6.9, 6.13 и 6.14 при шаблоне 7.1:

- 6.14: `hadassah-seo-audits`, `medscan-yauza-seo-editor`, `personal-finance`, `seo-content-creator`
- 6.13: `hadassah-analytics`, `hadassah-content-oncology`, `hadassah-content-pediatric-surgery`,
  `hadassah-content-weight-metabolism`, `hadassah-seo-audit-jul`, `hadassah-seo-tech-contractor`,
  `hadassah-yandex-doctor-feed`, `simracing-setup`
- 6.9: `analytics-seo`, `horizon-task-tracker`
- 5.2: `hadassah-seo-planner` (установка неполная: не было `task-intake`)

Пользователь подтвердил 2026-08-15, что работа идёт только через хаб и обновлять
эти копии не нужно. Правильный шаг — не обновление, а удаление. Сам хаб при этом
актуален: `hub-template` и живая установка совпадают побайтово на версии 1.3.

Отдельно: у четырёх из этих проектов имена скиллов `environment-check`,
`task-intake`, `task-switch`, `task-finish` больше не конфликтуют с хабовыми —
хабовые получили префикс `hub-` (v6.16). Коллизии нет, но дубликаты остались.

Proposed task:

Удалить legacy standalone-файлы из проектов хаба: `ai/architecture.md`,
`ai/external-tools.md`, `AGENTS.md`, `CLAUDE.md`, `ai/skills/`, `.claude/`.
Память задач (`ai/current-task.md` и остальные пять файлов) и `knowledge/`
не трогать — они остаются каноничными и проверяются `check-hub-registry.sh`.

Выполнять только после [[FT-20260813-001]], которая решает судьбу
standalone-режима в целом: без этого решения непонятно, удаляем мы дубликаты
или ломаем поддерживаемый режим работы.

Acceptance criteria:

- Ни один проект хаба не содержит собственных копий архитектуры и скиллов.
- Шесть файлов памяти и `knowledge/` в каждом проекте целы;
  `bash scripts/check-hub-registry.sh` проходит.
- Каждое удаление подтверждено отдельно по проекту, с показом списка файлов до удаления.
- Изменения закоммичены в репозитории каждого проекта, история сохранена.

Promotion notes:

Проверить, не ссылается ли что-то в памяти проекта на его локальные скиллы —
такие ссылки станут битыми. Начать с одного проекта и убедиться, что хабовый
поток работы (`hub-environment-check`, `hub-task-intake`) полностью его
покрывает, прежде чем чистить остальные 14.

### TASK-ai-dev-architecture-20260814-002 — Решить судьбу собственной памяти `ai/` в этом репозитории

Status: idea

Priority: medium

Source: сессия 2026-08-14, попытка закоммитить новый спек

Created: 2026-08-14

Context:

Локальный файл `.git/info/exclude` исключает `/AGENTS.md`, `/CLAUDE.md` и `/ai/`.
При этом 11 файлов внутри `ai/` отслеживаются, включая два спека и план в
`ai/superpowers/`. Состояние противоречивое: правило говорит «не хранить», факт
говорит «частично храним». Каждый новый файл в `ai/` упирается в этот вопрос.

Proposed task:

Выбрать один режим и привести репозиторий к нему: либо `ai/` полностью вне
репозитория (тогда убрать 11 отслеживаемых файлов из индекса и решить, где живут
спеки), либо `ai/` внутри (тогда убрать `/ai/` из `.git/info/exclude`).

Acceptance criteria:

- В репозитории нет файлов, попадающих под собственное исключение, либо
  исключение снято.
- Место хранения спеков и планов определено и не требует `git add -f`.

Promotion notes:

Учесть, что репозиторий раздаёт шаблоны `template/` и `hub-template/`; собственная
рабочая память может путать тех, кто его клонирует. Спек
`ai/superpowers/specs/2026-08-14-hub-skill-namespace-and-nested-projects-design.md`
существует только на диске и в историю не попал — при выборе режима решить его судьбу.

### TASK-ai-dev-architecture-20260814-001 — Проверка автоматического создания приватного репозитория

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

### TASK-ai-dev-architecture-20260726-002 — Настроить самопроверку архитектуры по запросу

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
