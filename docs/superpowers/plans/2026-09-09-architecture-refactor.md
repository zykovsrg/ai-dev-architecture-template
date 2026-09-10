# Architecture Refactoring — Staged Implementation Plan

> Superseded as an execution entry point by [the complete implementation plan](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-complete.md). Keep this document as the historical programme outline; do not follow its former requirement to return to Astra between every package.

## Current execution contract — revised after user confirmation

The controlling specification is [hub consolidation and session learning](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/specs/2026-09-09-hub-refactor-design.md). The user now authorizes the refactoring programme, but explicitly assigns specification and planning to Astra and implementation to Terra/Luna. Do not implement until the user switches models. This section supersedes the earlier proposal-only wording and older self-audit design below.

The reviewer runs at EVERY task closure, using AI to assess agent behavior in the task's current session; it saves a separate project-local review document even when no issue is observed. Explicit user-selected session review uses the same shared procedure. Preserve existing task/calendar learning. Remove only the identified obsolete Codex self-audit schedule. Do not implement a background detector or periodic transcript sampling as a substitute for closure review.

Planning belongs to Astra. Terra may resolve routine implementation details and adapt exact line locations; a material new design decision returns to the planning stage. Luna is limited to approved mechanical changes and exact per-project migration manifests. No automatic model changes or new Codex tasks are created by this document.

Implementation entry: [first implementation package](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-first-package.md). The 24 rows remain a programme map; they are not all ready-made code patches. Detailed subsequent packages are prepared on Astra against the previous accepted result.

> **For agentic workers:** Use superpowers:executing-plans to execute one approved work package at a time. Do not spawn agents by default. Prepare the package's exact implementation and regression test before editing production files; this document is the programme breakdown, not a prewritten patch for every subsystem.

**Goal:** Consolidate shared architecture in the hub, resolve confirmed architectural defects, and introduce bounded, approval-gated self-improvement executable through Terra and Luna.

**Architecture:** Shared workflows have one maintained distribution source; the installed hub is its deployment, not a competing authoring source. Project memory and genuinely project-specific resources remain local. Deterministic checks select small evidence packets for semantic review; no scheduled Codex wakeups are required by the proposed pilot.

**Tech Stack:** Existing Markdown, Bash, Git, Python calendar-policy tests, local Calendar bridge and Obsidian adapters. No new database, daemon or model API is required by this proposal.

## Global Constraints

- The user authorized this programme; implementation begins after the user switches from Astra to Terra/Luna. New learned-rule proposals still require their own concrete confirmation.
- Application internals, product features and application acceptance tests are excluded. Architecture-owned scripts, adapters, project instructions and task-memory compatibility are included.
- Preserve current uncommitted edits. Read only registered and authorized projects. Never read or copy credential values into reports.
- Change shared rules, migration targets and external state only under the applicable approval procedure. One approval covers one fully described coherent package, not unrelated later actions.
- Persistent AI-facing rules and implementation briefs are English; user explanations remain Russian.
- Do not equate a passed static check with a successful live interaction. Report untested and blocked separately from passed.
- Do not introduce a second canonical task store, duplicate learning journal, or generic rule copies in projects.

## Как выполнять на Terra и Luna

Terra получает задачи с несколькими взаимодействующими частями: формат данных, обновление, перенос правил и подтверждение внешних изменений. Luna получает узкие исправления с заранее определённым результатом, тестом и списком файлов. Это распределение ответственности, а не гарантия качества конкретной модели.

Одна рабочая задача — один результат и один цикл проверки. Не передавать модели всю переписку, полный аудит или все 57 проектов. Стартовый пакет: границы этой программы, выбранная карточка ниже, относящиеся к ней находки аудита, конкретные входные файлы и результаты предыдущего шага. Начальный ориентир — до пяти исходных файлов; расширение чтения должно иметь названную причину. Тесты и необходимые зависимости не обрезать ради искусственного лимита.

Перед каждым пакетом Astra готовит его исполняемый план: точные пути, изменяемый блок, входы/выходы, регрессионный пример, команды запуска и ожидаемый результат. Terra реализует сложные пакеты, Luna — механические. Не поручать Luna «исправить архитектуру» или самостоятельно выбирать смысл спорных проектных задач.

Ниже намеренно нет заранее написанных исправлений для непроверенных будущих состояний файлов. Детальный исполняемый мини-план готовится непосредственно перед пакетом; иначе после первого обновления следующие готовые патчи устареют. Это обязательный подготовительный шаг, не скрытый пропуск реализации.

## Пути и ответственность

В таблицах H означает `/Users/zykovsrg/Documents/vibecode/_ai-hub`, P означает `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture`. Перед передачей отдельной карточки исполнителю раскрыть эти сокращения до абсолютных путей. Это не разрешение читать другие каталоги.

| Область | Файлы и ответственность |
| --- | --- |
| Правила и выпуск | `H/ai/architecture.md`, `H/AGENTS.md`; исходники `P/hub-template/`; `P/scripts/update-installed-hub.sh`, `install-hub.sh`, `install.sh` |
| Формат и представления задач | `H/scripts/generate-obsidian-projects-kanban.sh`, `obsidian-task-sync.sh`, `check-workflow-memory.sh`; соответствующие исходники выпуска; `P/scripts/*obsidian*test.sh` |
| Календарь | `P/calendar-policy/`, `P/scripts/apple-calendar-policy-test.sh`; `H/ai/skills/hub-calendar/SKILL.md`; `H/scripts/snapshot-calendar.sh`, `H/tests/test-snapshot-calendar.sh` |
| Общие процедуры | `H/ai/skills/hub-workflows/SKILL.md`, `hub-task-finish/SKILL.md`; соответствующие файлы `P/hub-template/` |
| Существующий аудит сессий | `P/knowledge/runbooks/session-audit-procedure.md`, `P/knowledge/research/session-inventory.md`, `P/scripts/refresh-session-inventory.sh`, `test-refresh-session-inventory.sh` |
| Проектная миграция | Только точные файлы выбранного зарегистрированного проекта из подтверждённого списка переноса; память и специальные ресурсы сохраняются |

## Общий цикл каждой карточки

- [ ] Проверить актуальные изменения и входные зависимости; сформировать мини-план с точными путями и тестовым примером. Нельзя применять старые номера строк вслепую.
- [ ] Для дефекта сначала воспроизвести ошибку на вымышленных данных. Для миграции сначала сформировать список изменений и проверку сохранности.
- [ ] Выполнить только согласованный пакет. Не исправлять соседние проблемы попутно.
- [ ] Запустить узкую проверку, затем проверки затронутых связей; сохранить команды, коды завершения и краткий результат.
- [ ] Проверить diff, отсутствие секретов и побочных изменений. Сохранить отдельный коммит только своих файлов, если фиксация входит в согласованный запуск; иначе оставить проверенный diff.
- [ ] Передать результат: пакет, изменённые файлы, проверка, ограничения, следующий разрешённый пакет. Не закрывать пакет при непроверенной приёмке.

При несовпадении входов, двух неудачных попытках одного исправления, необходимости поменять согласованный формат или выйти за список файлов остановить реализацию и вернуть конкретную проблему Terra. Terra может расширить диагностику, но не согласованный объём записи без основания. Повторный полный аудит не является запасным шагом.

## Этап 1. Стабильная основа и узкие исправления

| ID / исполнитель | Вход и изменение | Проверяемый результат / зависимость |
| --- | --- | --- |
| 01 / Terra | A01, A08, A10, A11; сравнить живые правила, шаблон и updater. Составить точный список полезных расхождений, устаревших правил и происхождения файлов. | По каждому расхождению указано сохранить/заменить/уточнить и тест. Ни одно живое улучшение не теряется; спорные решения не принимаются молча. |
| 02 / Terra | После 01: `P/scripts/update-installed-hub.sh` и тесты выпуска. Сделать содержимое выпуска проверяемым; dry-run должен показывать все изменения, включая `.gitignore`; незнакомые локальные изменения не перезаписывать. | На временной установке одинаковая версия с разным содержимым распознаётся; локальная правка защищена; apply соответствует preview; повторное обновление ничего не меняет. |
| 03 / Luna | A04: `H/scripts/snapshot-calendar.sh`, `H/tests/test-snapshot-calendar.sh`; после 01 определить соответствующие файлы выпуска. Разделить дату расписания и фактическое время создания; убрать коллизии имён. | Два снимка за минуту сохраняются отдельно. Планирование будущего дня не удаляет свежие снимки. Удаляется только устаревший кэш по реальному времени. |
| 04 / Luna | A12: `H/scripts/check-workflow-memory.sh`, `H/tests/test-check-workflow-memory.sh`. Проверять существование календарной даты, не только форму строки. | `2026-99-99` и `2026-02-30` отклонены, `2028-02-29` принят. Существующие корректные записи проходят. |
| 05 / Terra | A05, A07: `H/ai/skills/hub-workflows/SKILL.md` и исходник выпуска. Разделить «наблюдение прочитано» и «предложение принято». | Отклонённое/прерванное предложение не теряется, принятый эпизод не предлагается повторно; исходные наблюдения остаются доступны до решения. Проверка на трёх вымышленных эпизодах. |
| 06 / Luna | A09, A17: `P/scripts/apple-calendar-policy-test.sh`, `calendar-policy-install-test.sh`, `hub-smoke-test.sh`. Сделать подготовку тестового окружения явной и перечень безопасных проверок воспроизводимым. | Отсутствующее окружение даёт точную инструкцию, а не неясный сбой. Изолированный запуск не пишет события, реальные ключи или данные приложений. |

## Этап 2. Единый формат без потери задач

| ID / исполнитель | Вход и изменение | Проверяемый результат / зависимость |
| --- | --- | --- |
| 07 / Terra | A02, A13: инструкции intake/switch/finish, генератор и обратный sync. Зафиксировать единый формат ID, статуса, срока, паузы и связей. | Старые варианты читаются явно либо попадают в список неоднозначностей; новая запись создаётся только в канонической форме. Нельзя молча пропустить непонятную запись. После 01. |
| 08 / Terra | После 07: генератор, обратный sync, тесты `P/scripts/obsidian-projects-kanban-test.sh`, `obsidian-task-sync-test.sh`. Реализовать совместимое чтение и единую запись срока. | `Due:`/`due:` не дают двух сроков; старые open/paused и списковые записи либо представлены, либо явно требуют решения. Проверки включают реальные обезличенные варианты A13. |
| 09 / Terra | A03: обратный sync и календарная процедура. Спроектировать один подтверждаемый пакет задача+событие с проверкой актуальности и восстановлением после частичного сбоя. | Сначала тест с подменённым календарём: отказ, повторный запуск, изменённый исходник, сбой второй записи. Нет скрытого календарного изменения или ложного сообщения об успехе. Живой тест — отдельное согласованное действие. |
| 10 / Luna + Terra для смысла | После 08: по одному проекту, только `ai/current-task.md`, `ai/future-tasks.md`, `ai/paused-tasks.md`; A13, A15, A16. Luna нормализует однозначное, Terra классифицирует спорное. | Все исходные смысловые записи сохранены или имеют явное решение. Выполнение приложения не выводится из старой записи: неподтверждённое остаётся неподтверждённым. Общие дубли получают владельца и ссылки, не исчезают. |

Пакет 10 — повторяемая карточка, а не один запуск на 57 проектов. Большой бэклог разбивается по ID или заголовкам с контрольной суммой исходника. Один проект закрывается только после общей сверки всех его частей. Архивные проекты не активируются ради миграции.

## Этап 3. Общие правила только в хабе

| ID / исполнитель | Вход и изменение | Проверяемый результат / зависимость |
| --- | --- | --- |
| 11 / Terra | A14, A19: установщики и существующие процедуры регистрации/миграции. Составить алгоритм переноса уже зарегистрированного проекта. | Preview перечисляет каждый удаляемый/переносимый файл, различия и способ восстановления, включая неотслеживаемые файлы. Сравниваются ресурсы навыков, не только SKILL.md. После 02 и 07. |
| 12 / Terra | Три пилота: простой проект с копиями; проект с нестандартной памятью; проект со специальными навыками. Имена выбрать из актуальной инвентаризации до записи. | Общие инструкции работают из хаба, проектная память и специальные ресурсы сохранены. Прямое открытие проекта проверено; если необходим указатель на хаб, он минимален и не копирует правила. После 10 для выбранных проектов, 11. |
| 13 / Luna | После успешных пилотов: по одному остальному проекту по точному утверждённому списку файлов. Отличие от списка — остановка, не импровизация. | Сверка каждой из 57 строк: перенесён / уже соответствует / согласованное исключение. 34 старых комплекта проверены; целые `.claude` и `ai/skills` вслепую не удаляются. |
| 14 / Terra | После пилотов: `P/scripts/install.sh`, `install-hub.sh`, `update-installed-architecture.sh`, документация и smoke tests. Закрыть штатный путь standalone и возвращение удалённых копий. | Новая установка и повторное обновление не создают независимые правила в управляемом проекте. Ошибочный старый вызов даёт безопасное объяснение без записи. |
| 15 / Luna | A08, A10, A16: память архитектуры и документы по точному списку решений этапов 1–3. | Выполненные задачи закрыты с доказательством; заменённые решения связаны с новыми; специальных правил Git для памяти нет без объяснения. Не переписывать историю как будто новый порядок существовал всегда. |

## Этап 4. Экономная самопроверка всей архитектуры

Запуск: ИИ-ревью при закрытии каждой задачи и дополнительная проверка выбранной сессии по запросу. Ревью сохраняется в `ai/session-reviews/` выбранного проекта. Простые программные проверки дополняют анализ поведения агента. Текущее самообучение по задачам и календарю сохраняется.

| ID / исполнитель | Вход и изменение | Проверяемый результат / зависимость |
| --- | --- | --- |
| 16 / Terra | A06: существующий runbook, индекс сессий и документация запуска. Во время реализации найти точный существующий Codex self-audit automation и удалить только его через штатное управление. | Сохранены параметры для восстановления; удалено именно старое расписание самоаудита, прочие автоматизации не затронуты. Документы не обещают запуск по расписанию. Сейчас ничего не отключено. |
| 17 / Terra | A06, A07: расширить существующий механизм аудита вместо второго независимого журнала. Перед кодом согласовать поля: ID эпизода, тип источника, доказательство, состояние, ссылка на единственную задачу-владельца, результат проверки эффекта. | Один эпизод не считается несколькими повторениями. Принятое правило связано с причиной и проверкой; отклонённое предложение не возвращается без новых данных. После 05, 15. |
| 18 / Terra | После 17: добавить shared `hub-session-review`, шаблон и вызов из `hub-task-finish`. Сохранять обзор в `ai/session-reviews/` проекта до очистки задачи. | Есть ревью каждого закрытия, ссылка в результате, защита от повторной записи; при ошибке сохранения контекст задачи остаётся. Текущая сессия анализируется содержательно, даже без ошибки программного валидатора. |
| 19 / Terra | Самопроверка рабочих сценариев: выбор проекта → чтение задачи → предложение → подтверждение → запись → повторное чтение. Подменённые внешние сервисы и вымышленные проекты. | Фиксированные сценарии: неверный проект, отказ пользователя, устаревший preview, повтор применения, потеря календарного доступа, нестандартная задача. Локальные тесты запускаются без модели; живая модель проверяет только изменённую процедуру. После 09, 17. |
| 20 / Terra | После 18: явный запрос на проверку выбранной сессии использует ту же процедуру. Проверить доступность выбранной истории и отметить полноту. | Доступен ручной запуск; недоступная история отмечена, не придумана; правила сверяются с периодом разговора. Предложения сохраняются, изменения требуют подтверждения. |
| 21 / Luna | По подготовленным Astra примерам 18–20 собрать проверки; Terra проверяет смысл. | Правильная работа, непонимание, новая просьба, ложный успех, неполная история, повтор закрытия и отказ записи различаются. Проверять поведение на вымышленных разговорах, не только наличие слов в инструкции. |
| 22 / Terra | Провести ограниченный пилот: формат задачи, ошибка выпуска/правила, нарушение процедуры подтверждения. | Есть исходное поведение, предложенная правка, подтверждение, проверка эффекта и расход, когда среда его показывает. Отсутствие новых событий не создаёт семантический обзор. |

Ограничение расходов: использовать доступный контекст текущей задачи и читать дополнительные материалы только для проверки конкретного вывода. Обычное ревью — около 40 строк, без потери существенных замечаний ради лимита. Проверка происходит при каждом закрытии и потребляет токены; размер текста не гарантирует стоимость. Первичную разработку учитывать отдельно. Если фактический расход недоступен, так и указать.

Более строгая альтернатива — полностью автономный локальный запуск по событиям/времени с журналом сбоев. Он потребует отдельного механизма установки, прав доступа и обслуживания. Для первого пилота предлагается более дешёвый ручной/событийный вариант; постоянный фон не считается согласованным и не включён скрыто в задачи.

## Этап 5. Связи и итоговая приёмка

| ID / исполнитель | Вход и изменение | Проверяемый результат |
| --- | --- | --- |
| 23 / Terra | Реестр связей в `P/docs/audits/2026-09-09-service-inventory.md`. Проверять по одной связи, сначала без записи. | У каждой связи отдельно указаны доступность, безопасный тест и непроверенный живой участок. Создание событий, экспорт аудио и публикация репозиториев не используются как невидимая диагностика. |
| 24 / Terra | Аудит A01–A19, все карточки программы, 57 строк инвентаризации. | Каждая находка имеет исправление с проверкой либо явное исключение согласованного объёма. A18 передана пользователю как отдельный риск, а не автоматически отозванный ключ. Нет объявления приложений проверенными. |

Итог: общие правила едины, задачи не теряются, обновление обратимо, дубли удалены с сохранением полезного, самопроверка не меняет архитектуру без подтверждения. Неизвестные ошибки и прикладной долг не называются устранёнными.

## Порядок и передача исполнителю

01 → 02; 03–06 отдельными пакетами; 07 → 08 → 09 → 10; 11 → 12 → 13 и 14 → 15; 16 → 17 → 18–21 → 22; 23 → 24. Связь с более ранним этапом, указанная в карточке, обязательна. Не запускать 57 миграций одновременно. Не создавать новые задачи в Codex автоматически по этому документу.

Каждая передача исполнителю включает этот английский контракт с уже заполненными конкретными значениями, без шаблонных пропусков:

> Execute only the selected approved package. Read its exact input files and relevant audit findings, not the full project history. Preserve unrelated edits. First reproduce the defect or validate the migration preview, then make the smallest scoped change and run the specified checks. Do not change application code, credentials, external services, or other packages. If inputs differ or the required change exceeds the approved scope, stop with evidence. Return changed files, commands and results, remaining uncertainty, and the next dependency. Never claim a live integration works based only on a mock test.

Этот план использует пошаговую методику: отдельные проверяемые результаты, тест до исправления и контроль перехода между пакетами. Он не требует дорогой модели для каждого шага и не выдаёт распределение по моделям за измеренную оценку стоимости.
