# Unified Assistant Architecture

## Goals and non-goals

Цель — единый личный AI-ассистент для проектов, задач, времени и знаний: он
помогает планировать день, разбирать встречи, показывать Kanban, хранить знания
и не терять ожидания. Пользователь сохраняет ручной контроль: agent сначала
показывает предложение, а запись делает только после явного подтверждения.

Не входит в этот этап: перенос текущего Obsidian vault, удаление старых заметок,
запись в Apple Calendar, установка MCP, фоновое чтение чатов или создание второй
базы задач. Обнаружено 715 Markdown-файлов вне `.trash`, 3 792 checkbox-строки
и 632 wiki-link occurrences; это агрегаты, не список готовых задач или связей.

## Requirement-to-design matrix

| Подтверждённое требование | Точное решение |
| --- | --- |
| Одна правда о проектах и задачах | `ai/current-task.md` и `ai/future-tasks.md` остаются каноническими; Obsidian — производная витрина. |
| Архипроекты без двойного счёта | Один `primary_archiproject`, optional related links без вклада, реестр `ai/archiprojects.md`. |
| Ожидание не останавливает проект автоматически | `waiting` принадлежит task/subtask; проектная колонка Waiting вычисляется только при отсутствии другой выполнимой работы. |
| Гибкий поиск без утечки | `metadata-search` читает только ID, name, tags, status, purpose; полный доступ — только confirmed scope. |
| Общая Kanban-доска | Один project-card на проект, generated Markdown view, колонки Incoming/Planned/Active/Waiting/Paused/Completed. |
| Знания и несколько проектов | Project-local knowledge остаётся в проекте; shared material один раз в Areas/Resources/Meetings/Inbox/Archives; ссылка не даёт доступ. |
| Встречи, аудио и быстрый capture | Одна canonical meeting record, независимые project-task proposals, неизвестные owner/due не угадываются. |
| Дневное и недельное управление | План дня и 15-minute review; Sunday 30-minute review начинается с archiproject target/progress/forecast. |
| Apple Calendar | EventKit MCP только с policy wrapper: selected calendar allowlist, preview, отдельное write confirmation, delete выключен. |
| Самодоработка | Только offer; транскрипты читаются после подтверждения точных IDs; pilot из 3 сессий и 8 точек runbook. |

## Source-of-truth boundaries

| Область | Каноническое место | Что может быть проекцией |
| --- | --- | --- |
| Project/task/subtask/waiting | Существующие проектные `ai/` файлы | Kanban, day plan, review, compact index. |
| Archiproject | Предлагаемый hub-owned `ai/archiprojects.md` и primary metadata project card | Прогресс, weekly dashboard. |
| Shared knowledge/meeting | Общая Obsidian knowledge area | Ссылки из проектов и search result. |
| Calendar event | Apple Calendar по event UID | Proposal envelope и сохранённая ссылка UID. |
| Audit finding | Краткий evidence-backed summary | future-task или architecture proposal после подтверждения. |

Ни Obsidian-карточка, ни Calendar-событие, ни ссылка не меняют каноническую
запись сами. Любая запись требует отдельного подтверждения непосредственно
перед конкретным diff.

## Work model

Иерархия: `archiproject → project → task → subtask`.

- Archiproject хранит ID, name, status, target, unit и due. Прогресс вычисляется
  только из primary contribution проектов.
- Project получает `primary_archiproject`, `archiproject_contribution` и
  `related_archiprojects`; related links не влияют на подсчёт.
- Current task остаётся единственной активной task проекта. Future task не
  имеет execution state до продвижения.
- Task имеет стабильный `id`, `title`, `due` (`YYYY-MM-DD` или `none`) и
  `subtasks`. `owner` исключён: task — действие пользователя; чужое обещание —
  контекст встречи или waiting.
- Waiting существует только вместе с `waiting_for`, `waiting_since`,
  `follow_up`, `next_after_response`.

## Knowledge model

Гибрид PARA и лёгкого Zettelkasten:

```text
Obsidian
├── AI-архитектура/Projects/    # generated project views
├── Areas/                      # постоянные сферы
├── Resources/Meetings/         # общие материалы и встречи
├── Inbox/                      # только неясное/отложенное
└── Archives/                   # завершённое по решению
```

Коллекции вроде рецептов и цитат — Resources, не проекты. Project-local
knowledge не переносится в общую базу без причины. Одна multi-project meeting
record хранится в `Resources/Meetings` один раз, перечисляет project IDs и
связана с отдельными задачами проектов.

## Routing and search

Три scope:

1. `metadata-search` — безопасная проекция пяти полей всех зарегистрированных
   проектов.
2. `confirmed-project` — один названный project ID, путь, цель и knowledge
   boundary.
3. `confirmed-set` — именованный набор для одного сравнения или generated
   aggregate view; при weekly review включает только заранее показанные записи
   нужных archiproject.

Link — discovery hint. Полное чтение проверяет ID, registered path, allowed
roots, отсутствие symlink escape и подтверждённую цель. Новый запрос снова
маршрутизируется; постоянного глобального доступа нет.

## Obsidian projection

Выбран чистый вариант: generated Markdown view, совместимый с Obsidian Kanban.
Последовательность всегда такая:

1. metadata-only план набора и целевого файла;
2. подтверждение чтения точного `confirmed-set`;
3. in-memory preview без записи;
4. отдельное подтверждение write-diff для Markdown и manifest;
5. запись и возможность восстановить только generated view.

Одна карточка показывает цель, primary archiproject, ближайший срок, blockers,
waiting count/follow-up, review fields и три–семь мест ближайших действий.
Ручное изменение карточки становится proposal/diff, а не синхронизацией. Пока
поля `last_reviewed_at` и `next_review_at` не одобрены в canonical project card,
витрина честно показывает `не записано`.

## Assistant workflows

Все возможные записи используют proposal envelope: action, target kind/project/
path, summary, due, source и `requires_confirmation`.

- План дня выводит контекст, три главных действия, остальные действия,
  waiting/follow-up, риски, Calendar proposal и точные решения.
- Вечернее 15-minute review: сделано, перенос, ожидания, follow-up, завтрашний
  Calendar, три действия и пакет подтверждений.
- Sunday 30-minute review: target, actual progress, forecast, project
  contribution, waiting и risks archiproject, затем только нужный drill-down.
- Capture текста/аудио/transcript сначала даёт разбор и proposals. Связанная
  task не создаётся без canonical meeting record; неизвестные сроки остаются
  `due: none` до решения.
- Missed follow-up — рекомендация, не автоматическое сообщение/изменение.

## Calendar integration

Рекомендованный технический адаптер — локальный
[`apple-calendar-mcp` 0.9.0](https://github.com/s-morgan-jeffries/apple-calendar-mcp),
но не безусловная установка. EventKit требует full Calendar access для чтения;
write-only доступа недостаточно. Поэтому сначала test calendar и read-only
path, затем отдельное решение о create/update. Delete, create/delete calendar
на первом этапе выключены.

MCP не является политикой безопасности: confirmation, preview, timezone,
duplicate marker, UID и compensating update реализуются в архитектурной
обёртке. Уже сохранённое или синхронизированное событие не имеет обещанного
автоматического rollback.

## Session audit integration

Каждые несколько дней assistant может предложить audit. После запроса на список
он показывает только metadata; чтение каждого transcript начинается лишь после
подтверждения точных session IDs.

Pilot: три малые, свежие, подтверждённо non-sensitive sessions; все восемь
проверок draft runbook; никаких чужих файлов. Возможны только `no systemic
issue`, `candidate future task` и `architecture change candidate`. Для обычной
кандидатуры нужно evidence минимум из двух независимых сессий; protected
change всегда ждёт `architecture-update`.

## Error handling and rollback

- Неизвестный ID, archived project, путь вне roots или symlink escape блокируют
  полное чтение и запись.
- Неясный маршрут → proposal Inbox, не автоматический перенос.
- Неподтверждённая или устаревшая proposal истекает без side effect.
- Migration начинается с backup/list, малыми batch и explicit diff; `.trash` не
  равен Archive; checkbox не равен task.
- Obsidian rollback восстанавливает generated view/manifest, но не канонические
  данные.
- Calendar update имеет prior snapshot и explicit compensating proposal; delete
  выключен до отдельной политики.

## Test strategy

Foundation проверяет: schema task/archiproject, invalid primary/related links,
due/waiting combinations, compact-index field leak, read-scope expiry, migration
compatibility, updater preservation и negative routing cases.

Дальнейшие планы добавят: generated board не содержит writable task copy,
manual edit → proposal, meeting dependency, daily/weekly workflow examples,
Calendar test calendar (timezone, duplicate, declined write, unavailable
calendar, UID update) и audit pilot privacy/evidence tests.

## Delivery sequence

1. **Foundation:** canonical work fields, archiproject registry, compact index,
   validators, template/updater preservation and tests.
2. **Obsidian:** read-only generated project board and empty structure; no vault
   migration.
3. **Workflows:** day/week reviews, waiting and capture/meeting proposals.
4. **Calendar:** test-calendar read path, then separately approved write path.
5. **Audit:** confirmed pilot, then only approved offer workflow.
6. **Vault migration:** small previewed reversible batches after content review.

## Decisions still requiring approval

### Architecture-update scope

Foundation needs the following protected/controlled changes. They are **not
applied by this document**:

| Class | Exact proposed files | Purpose |
| --- | --- | --- |
| Protected rules | `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, `ai/external-tools.md`, `ai/skills/architecture-update/SKILL.md`, `ai/skills/release-check/SKILL.md`, `docs/file-roles.md` | Add the archiproject/task/index contracts and update the canonical memory lists/rules. |
| Template parity | `template/AGENTS.md`, `template/CLAUDE.md`, `template/ai/architecture.md`, `template/ai/current-task.md`, `template/ai/future-tasks.md`, `template/ai/skills/architecture-update/SKILL.md`, `template/ai/skills/release-check/SKILL.md` | Preserve the same contracts for new installations. |
| New controlled memory | `ai/archiprojects.md`, `template/ai/archiprojects.md` | Canonical archiproject records; adding it requires synchronising controlled-memory lists. |
| Hub scaffold | `hub-template/ai/archiprojects.md`, `hub-template/ai/project-registry.md`, `hub-template/ai/project-cards/*` | Supply registry/card fields only; no live project card is changed in foundation. |
| Validators/updaters/tests | `scripts/check-hub-registry.sh`, `scripts/hub-smoke-test.sh`, `scripts/check-consistency.sh`, `scripts/install.sh`, `scripts/update-installed-architecture.sh` | Validate contracts and preserve user memory during install/update. |

Exact files may narrow after a preflight; no unlisted protected or controlled
file may be changed without a new confirmation.

### Separate later approvals

- Install and grant permission to Apple Calendar MCP, then select allowed
  calendars and test calendar.
- Write generated views into the live Obsidian vault.
- Migrate, move, delete or classify existing vault content.
- Run any session-audit pilot on exact chat IDs.
