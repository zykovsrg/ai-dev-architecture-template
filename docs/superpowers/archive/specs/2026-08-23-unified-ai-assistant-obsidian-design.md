# Unified AI Assistant with Obsidian — Design

Date: 2026-08-23

## Purpose

Prepare one staged master prompt for designing a unified personal AI assistant
that joins the existing AI Development Architecture, Obsidian, Codex, Claude
Code, and Apple Calendar. The prompt asks for a detailed concept and an
implementation roadmap. It does not authorize implementation, migration,
deletion, or architecture changes.

The system should reduce information loss across many projects and tasks while
preserving manual control, explicit routing, and safe project isolation.

## Confirmed design principles

- The AI architecture is the source of truth for projects and tasks.
- Obsidian is the unified human interface, Kanban view, and knowledge workspace.
- Apple Calendar provides availability and calendar events through a suitable MCP integration.
- The agent proposes every write, destination, deadline, move, and calendar change before applying it.
- Project knowledge belongs to its project. Shared knowledge is stored once in a common knowledge base.
- One note may link to several projects, but a link does not grant automatic access to them.
- Cross-project search starts from compact indexes. Full reads require confirmation of the selected scope.
- Existing files are inventoried before any move. Nothing is deleted or moved without separate confirmation.
- Obsidian must not hold a second independent copy of project tasks.
- New entities and fields are allowed only when their benefit justifies the added complexity.
- `Inbox` is a fallback for ambiguous or deferred information, not a mandatory entry path.

## Information model

The work hierarchy is:

```text
Archiproject
└── Projects
    └── Tasks
        └── Subtasks
```

An archiproject groups projects around one measurable result and deadline. A
project has one primary archiproject. It may have secondary links to other
archiprojects, but its progress is counted only in the primary one.

The knowledge structure uses selected PARA and Zettelkasten ideas:

```text
Knowledge base
├── Areas
├── Resources
│   └── Meetings
├── Inbox
└── Archives
```

PARA supplies the high-level organization. Lightweight Zettelkasten practices
help keep notes focused, sourced, and linked. Existing notes are not split into
atomic notes automatically.

## Core scenarios

### Daily planning

The assistant reads permitted active tasks, deadlines, waiting states,
archiproject priorities, and Apple Calendar. It proposes a realistic day plan.
Task and calendar writes require confirmation.

### Fast capture and meeting processing

The user provides text, audio, or a transcript. The assistant proposes:

1. a concise summary;
2. linked projects;
3. tasks, owners, and possible deadlines;
4. one canonical knowledge destination;
5. calendar changes where useful.

One multi-project meeting note is stored once under shared `Resources/Meetings`.
Each project receives only its own tasks and a reference to the shared note.

### Project Kanban

Obsidian displays one common board where one card represents one project. A
card shows the goal, project status, nearest deadline, blockers, waiting count,
review dates, and three to seven next actions. These values are views of the AI
architecture data, not copied task records.

Suggested project columns are `Incoming`, `Planned`, `Active`, `Waiting`,
`Paused`, and `Completed`. A project enters `Waiting` only when no useful work
can continue. Individual tasks can wait while their project remains active.

### Waiting for an external response

A task waiting for a person or organization needs at least:

- who or what is awaited;
- waiting start date;
- follow-up date;
- next action after the response.

The project card shows waiting tasks and the nearest follow-up without treating
the whole project as stopped.

### Daily review

A 15-minute end-of-day review covers completed work, carry-over, waiting items,
follow-ups, tomorrow's calendar, and the next day's three main actions.

### Weekly review

A 30-minute Sunday review starts at the archiproject level: target versus
actual progress, forecast, completed and stalled projects, deadlines, waiting
items, and the next projects needed to reach the shared result. It then drills
into individual projects only where necessary.

### Knowledge search

The assistant supports requests such as finding recipes, quotes by topic or
author, meeting decisions, and comparisons across projects. It searches compact
indexes first. Before opening full content from several projects, it names the
projects and asks the user to confirm the read scope.

### Architecture self-audit

Every few days the assistant may offer, but never start automatically, a review
of several recent chats. After confirmation it uses the latest approved method
from the registered `hub-session-audit` project. Findings require evidence. If
there is no proven systemic problem, no architecture change is proposed. Any
change goes through a separate confirmed `architecture-update` workflow.

The current audit runbook is still `draft` and has been used on zero sessions.
The future design must validate it on a small sample before treating it as an
established procedure.

## Required work stages in the master prompt

1. Inventory the current architecture and copied Obsidian vault without changes.
2. Design the minimum data model and justify every new entity and field.
3. Design routing, access confirmation, personal/work separation, rollback, and secret handling.
4. Design Obsidian structure, Kanban, metadata, links, and a safe migration map.
5. Specify daily, weekly, capture, waiting, search, and self-audit workflows.
6. Research and include Obsidian, Codex, Claude Code, and Apple Calendar MCP integrations.
7. Produce a staged, reversible implementation roadmap with verification and approval gates.

## Required outputs

The prompted agent must deliver:

1. current-state map and verified problems;
2. unified assistant concept;
3. entity and relationship model;
4. routing and access model;
5. Kanban and review design;
6. Obsidian adaptation and migration plan;
7. Apple Calendar MCP integration plan;
8. architecture self-audit plan;
9. staged implementation roadmap;
10. open decisions requiring user confirmation.

## Master prompt

```text
Мы проектируем единого персонального AI-ассистента для управления проектами,
задачами, временем и знаниями. Нужно объединить существующую AI Development
Architecture, текущее хранилище Obsidian, Codex, Claude Code и Apple Calendar
через подходящий MCP.

Проблема: проектов много, внутри них ещё больше задач. Информация забывается,
сроки и ожидания теряются, ручной контроль требует слишком много внимания.
Нужна система, которая помогает быстро вносить и находить информацию,
планировать день, следить за проектами и архипроектами, разбирать встречи,
вести базу знаний и регулярно проверять качество самой AI-архитектуры.

Твоя задача — провести исследование, подготовить подробную концепцию системы и
поэтапный план внедрения. Ничего не реализуй, не переноси и не удаляй. Не меняй
архитектуру, Obsidian, календарь или проектные файлы. Все спорные решения вынеси
на подтверждение пользователя.

Соблюдай следующие принципы:

1. AI-архитектура остаётся единственным источником правды для проектов и задач.
2. Obsidian становится единым ручным интерфейсом, Kanban и базой знаний, но не
   хранит независимую копию задач.
3. Apple Calendar используется для чтения занятости и, после подтверждения,
   создания или изменения событий.
4. Агент сначала показывает предлагаемое действие, точное место записи, срок и
   затрагиваемые данные. Запись выполняется только после подтверждения.
5. Сохрани строгую маршрутизацию хаба. Ссылка на другой проект не даёт
   автоматического доступа к его полным данным.
6. Разреши гибкий поиск по коротким индексам всех проектов. Для полного чтения
   или сравнения нескольких проектов сначала назови найденные проекты и запроси
   подтверждение области чтения.
7. Проектные знания принадлежат проекту. Общие знания хранятся один раз в общей
   базе. Материал может ссылаться на несколько проектов без создания копий.
8. `Inbox` используется только для неоднозначных, отложенных или неразобранных
   материалов. Если место понятно, агент сразу предлагает правильный маршрут.
9. Старые файлы сначала инвентаризируются. Ничего не перемещай и не удаляй без
   отдельного подтверждения и плана отката.
10. Не добавляй новую сущность или обязательное поле без доказанной пользы.

Используй рабочую иерархию:

Archiproject → Projects → Tasks → Subtasks.

Архипроект объединяет проекты общей измеримой целью и сроком. У проекта один
основной архипроект. Дополнительные связи разрешены, но прогресс учитывается
только в основном архипроекте, чтобы избежать двойного подсчёта.

Для общей базы знаний исследуй гибрид PARA и лёгкого Zettelkasten:

- Areas — постоянные области жизни и работы;
- Resources — справочные материалы, цитаты, рецепты, статьи и встречи;
- Inbox — временный запасной буфер;
- Archives — завершённое и неактуальное.

Не превращай каждую смысловую коллекцию в проект. Проект — работа с целью и
критерием завершения. Коллекция знаний — материалы для хранения и поиска.
Предложи минимальные типы заметок только после изучения реального vault.

Обязательно спроектируй следующие сценарии:

- план дня с учётом задач, сроков, ожиданий, архипроектов и Apple Calendar;
- обработка текста, аудио и транскрипта встречи;
- определение нескольких связанных проектов;
- выделение задач, ответственных и возможных сроков;
- одна каноническая запись встречи в `Resources/Meetings` и ссылки из проектов;
- единая Kanban-доска Obsidian: одна карточка — один проект;
- внутри карточки цель, статус, ближайший срок, блокеры, ожидания, даты ревью и
  три–семь ближайших действий;
- статус задачи `waiting`: кого ждём, с какой даты и когда напомнить;
- проект остаётся активным, если другие задачи можно выполнять;
- 15-минутное ревью дня;
- 30-минутное воскресное ревью с проверкой прогресса прежде всего по архипроектам;
- поиск рецептов, цитат, решений встреч и знаний по нескольким проектам;
- предложение самоаудита архитектуры раз в несколько дней.

Самоаудит запускается только после подтверждения. Он использует последнюю
утверждённую методику зарегистрированного проекта `hub-session-audit`, читает
несколько свежих чатов в режиме только чтения и ищет доказанные нарушения
маршрутизации, режимов, skills, обновления памяти, границ и незакрытые хвосты.
Если системных проблем нет, не предлагай изменения. Если проблемы есть,
предложи их отдельно; изменение архитектуры возможно только через подтверждённый
`architecture-update`. Учти, что текущая методика аудита пока имеет статус
`draft` и сначала должна быть проверена на небольшой выборке сессий.

Работай по этапам:

Этап 1. Только чтение и инвентаризация AI-архитектуры, реестра проектов,
проектной памяти, текущего Obsidian vault, его плагинов, Kanban-досок и
метаданных. Отдели проверенные факты от гипотез.

Этап 2. Предложи минимальную модель данных для архипроектов, проектов, задач,
подзадач, ожиданий, знаний, встреч, связей и календарных событий. Обоснуй каждое
новое поле и сущность.

Этап 3. Спроектируй маршрутизацию, поиск по индексам, подтверждение полного
чтения, разделение личных и рабочих данных, обработку секретов, журналирование,
ошибки и откат.

Этап 4. Предложи целевую структуру Obsidian, способ показать файлы разных
проектов, Kanban, минимальные метаданные, правила Inbox и карту безопасной
адаптации старого vault. Не планируй перенос ради эстетической чистоты.

Этап 5. Опиши точные пользовательские процессы: план дня, ревью дня, ревью
недели, обработка встречи, создание задач, ожидание ответа, поиск знаний,
обновление Kanban и самоаудит.

Этап 6. Исследуй актуальные способы интеграции Obsidian, Codex, Claude Code и
Apple Calendar через MCP. Для Apple Calendar проверь возможности чтения и
записи, права доступа, безопасность, поддержку macOS и подтверждение изменений.
Не выбирай инструмент только по названию.

Этап 7. Составь поэтапный обратимый план внедрения. Для каждого этапа укажи
результат, изменяемые файлы и данные, риски, проверку, откат и точку
подтверждения пользователя.

Итог должен содержать:

1. карту текущего состояния и подтверждённых проблем;
2. подробную концепцию единого AI-ассистента;
3. схему сущностей, хранения и связей;
4. модель маршрутизации и доступа;
5. проект Kanban и регулярных ревью;
6. план адаптации существующего Obsidian vault;
7. план интеграции Apple Calendar через MCP;
8. план безопасного самоаудита архитектуры;
9. поэтапный план внедрения;
10. список открытых решений, требующих подтверждения.

Сначала покажи результаты обследования и вопросы. Не переходи к реализации,
пока пользователь отдельно не одобрит концепцию и план.
```

## Validation criteria for the prompt

- The result clearly separates verified facts, assumptions, and proposals.
- No implementation starts from this prompt.
- Existing routing remains stronger than links and search convenience.
- Project and task records have one source of truth.
- Multi-project notes do not create duplicate canonical content.
- Project waiting and task waiting are not confused.
- Archiproject progress cannot be counted twice.
- Every write or migration has an approval gate and rollback path.
- The roadmap includes tests or checks for routing, data integrity, Kanban views,
  calendar writes, cross-project search, and failed/partial operations.
