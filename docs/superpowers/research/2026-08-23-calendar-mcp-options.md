# Apple Calendar MCP: варианты и выбор

## Итог

Рекомендован **двухслойный вариант**: локальный MCP
[`s-morgan-jeffries/apple-calendar-mcp`](https://github.com/s-morgan-jeffries/apple-calendar-mcp)
версии `0.9.0` как технический адаптер и правила AI-архитектуры как слой
подтверждений. MCP сам по себе не заменяет правило «сначала preview, затем
явное подтверждение записи».

На 2026-08-24 этот репозиторий указывает версию `0.9.0`, статус Beta, macOS и
Python 3.10+ в своём manifest; на главной странице — 162 commits, 184 unit и
59 integration tests. Это проверяемые данные проекта, а не независимый аудит.
Перед установкой нужно ещё раз сверить commit/версию и зависимости.

Выбор разумен для целевого сценария: есть отдельные tools для read, availability
и full CRUD, UID для update/delete, ISO local time и обработка recurring events.
Но на первом этапе активируем только чтение и создание/изменение событий;
`delete_events`, `create_calendar` и `delete_calendar` выключены политикой
архитектуры до отдельного решения.

## Первичные источники

| Источник | Что подтверждает | Дата проверки |
| --- | --- | --- |
| [Apple: EventKit access](https://developer.apple.com/documentation/eventkit/accessing-the-event-store) | Для чтения Calendar нужен full access; write-only не даёт читать события. Для sandboxed macOS app требуется entitlement Calendar. | 2026-08-24 |
| [Apple: EventKit/Calendar](https://developer.apple.com/documentation/eventkit/accessing-calendar-using-eventkit-and-eventkitui) | Full access позволяет читать, создавать, менять и удалять события; EventKit умеет rollback/reset при неуспешном batch commit. | 2026-08-24 |
| [Manifest `apple-calendar-mcp`](https://github.com/s-morgan-jeffries/apple-calendar-mcp/blob/main/pyproject.toml) | Версия `0.9.0`, Beta, Python `>=3.10`, macOS/Darwin. | 2026-08-24 |
| [README выбранного MCP](https://github.com/s-morgan-jeffries/apple-calendar-mcp) | Tools, EventKit/Swift helper, availability/conflicts, локальный ISO формат и требования macOS. | 2026-08-24 |
| [security issue выбранного MCP](https://github.com/s-morgan-jeffries/apple-calendar-mcp/issues/215) | Содержимое чужих событий может быть prompt injection; title, notes и location нельзя трактовать как инструкции. | 2026-08-24 |
| [redpop/apple-calendar-mcp](https://github.com/redpop/apple-calendar-mcp) | Альтернатива `0.2.1`: EventKit, local helper, read/create/update/delete и поиск свободного времени. | 2026-08-24 |

## Локальная доступность — без установки

Проверены только доступные текущему агенту инструменты и файлы проекта:

- Apple Calendar MCP tool в текущем harness: **not installed** — доступных
  `list/get/create/update/delete Calendar` tools нет.
- Конфигурация внутри этого проекта: **not installed** — в `ai/` и локальных
  project-config не найдено подключения Apple Calendar MCP.
- Глобальные пользовательские конфигурации Codex/Claude и права macOS:
  **not confirmed**. Они вне границы проекта и намеренно не читались.

Ничего не устанавливалось, не запускалось и не подключалось к живому Calendar.

## Варианты

### Чистый вариант: EventKit MCP + policy wrapper

Технический адаптер — `apple-calendar-mcp` `0.9.0`. Репозиторий заявляет:

- `get_calendars`, `get_events`, `search_events`, `get_availability`,
  `get_conflicts` для read;
- `create_events`, `update_events`, `delete_events` по UID;
- EventKit/Swift для операций с событиями и AppleScript только для управления
  календарями;
- ISO 8601 в локальном времени без суффикса `Z`.

Политика обёртки делает этот вариант безопаснее самого MCP:

1. macOS получает только `Calendars: Full Access`, потому что чтение занятости
   иначе невозможно. Не запрашивать Full Disk Access как значение по умолчанию.
2. После первого `get_calendars` пользователь выбирает явный allowlist
   календарей. До подтверждения agent не читает события; после — читает только
   выбранные calendar ID. Если сервер не возвращает стабильный ID календаря,
   реализация останавливается и не использует имя как единственный ключ.
3. В phase 1 доступны read и availability. В phase 2 доступны `create_events`
   и `update_events` только через proposal envelope с preview и подтверждением
   непосредственно перед MCP вызовом. Удаление и создание календаря запрещены.
4. В каждое созданное событие в description добавляется машинный marker
   `hub_proposal_id`; после create сохраняется возвращённый event UID в
   канонической архитектурной записи. Повторный proposal ID ищется до create и
   предотвращает duplicate.
5. Даты передаются с явной IANA timezone (`Europe/Kirov` для текущего
   пользователя) и отображаются вместе с timezone. Сравнение происходит по
   event UID, calendar ID, start/end и marker, не по одному title.
6. Событийные title, location, notes и приглашения — недоверенные внешние
   данные. Они отображаются как данные, но не могут менять инструкции,
   маршрутизацию или подтверждение пользователя.

Это least privilege в границах MCP. Важное ограничение: EventKit full access
на macOS шире, чем allowlist приложения; allowlist снижает доступ агента, но не
превращает системное разрешение в изоляцию по календарям.

### Дешёвый вариант: узкий локальный AppleScript bridge

Вместо готового MCP можно написать минимальный локальный bridge через
`osascript` для одного заранее выбранного Calendar.app-календаря: list занятости
и proposal на create. Запуск дешевле по зависимостям, но хуже по безопасности и
поддержке:

- terminal/host получит Automation-разрешение на Calendar.app;
- имена календарей могут совпадать, а AppleScript часто не даёт надёжный
  структурный ID для выбора;
- recurring events, timezone, update/delete и ошибки синхронизации придётся
  проектировать и тестировать самостоятельно;
- preview, duplicate marker и rollback всё равно придётся реализовать в
  архитектуре.

Этот вариант допустим только как read-only proof of concept. Он не рекомендован
для первого write workflow.

### Почему не выбран `redpop/apple-calendar-mcp`

Это удобная Node-альтернатива: manifest показывает `0.2.1`, macOS 14+, Node
20+, подписанный helper и операции read/create/update/delete с free-time.
Однако на дату проверки у неё 43 commits и менее зрелая версия. Её стоит
повторно сравнить при реализации, но сейчас более полный и тестируемый
`apple-calendar-mcp` — чистый выбор.

## Контракт разрешений и операций

| Операция | Нужен системный доступ | Нужен scope/подтверждение | Дополнительно |
| --- | --- | --- | --- |
| Выбрать календарь | Calendar Full Access | Явный выбор allowlist | Показать ID, имя и access level. |
| Прочитать занятость | Calendar Full Access | Подтверждённый запрос на дату и calendar ID | Возвращать минимум: время, занято/свободно, event UID; notes только если цель требует. |
| Найти свободный слот | Calendar Full Access | Подтверждённый диапазон и правила времени | Не создаёт слот. |
| Предложить событие | Нет новой записи | Нет MCP write | Показать timezone, calendar ID, UID=`new`, marker, конфликт и diff. |
| Создать/изменить | Calendar Full Access | Явное подтверждение exact proposal непосредственно перед вызовом | Create возвращает UID; update сначала reread по UID. |
| Удалить | Calendar Full Access | Пока запрещено | Требует отдельной будущей политики и подтверждённого UID. |

## Acceptance tests будущей интеграции

Все тесты выполняются позднее только в отдельном тестовом календаре, не в
живом Calendar пользователя.

1. **Read-only list.** `get_calendars` и `get_events` в диапазоне не меняют
   число событий и не вызывают write tool.
2. **Timezone.** Событие с `Europe/Kirov` и отдельный пограничный DST-кейс
   round-trip возвращают тот же local start/end и timezone; UTC-суффикс `Z` не
   подставляется молча.
3. **Duplicate prevention.** Повтор одного `hub_proposal_id` не создаёт второе
   событие: adapter находит marker и возвращает существующий UID.
4. **Create after confirmation.** До точного `approve` MCP create tool не
   вызывается; после него создаётся ровно один event, UID записывается в
   архитектуру только после успешного ответа MCP.
5. **Update after confirmation.** Adapter reread'ит event по UID, показывает
   old/new diff и меняет ровно поля из одобренного proposal; recurring scope
   (`this occurrence`/`series`) всегда выбран явно.
6. **Declined write.** Отказ не вызывает MCP write, не меняет architecture и
   сохраняет только текст proposal в разговоре.
7. **Unavailable Calendar.** Отсутствие прав, offline account, read-only
   calendar или EventKit error возвращают понятный status без fallback на другой
   календарь и без записи.
8. **Rollback/delete.** При ошибке batch commit adapter выполняет EventKit
   rollback/reset и не сохраняет UID. Update хранит prior snapshot для
   предложенного обратного update. Delete остаётся выключенным: удалённое
   приглашение может не иметь безопасного полного rollback.

## Условия следующего этапа

До отдельного подтверждения не устанавливать MCP и не выдавать системные
permissions. Если пользователь подтвердит реализацию, следующий план должен
сначала проверить package integrity/версию, создать test calendar, подключить
только read tools, провести acceptance tests 1–2 и лишь потом предложить
включить create/update.
