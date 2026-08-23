# Минимальная модель работы

## Статус решения

Это документирует одобренное решение. **AI architecture** — `source of truth`
для проектов и задач. Obsidian — только человеческое представление и
проекция этих данных; он не хранит независимую изменяемую базу задач.

### Основание

Проверенные факты из инвентаря:

- В каждом проекте уже есть один `ai/current-task.md` для текущей задачи,
  `ai/future-tasks.md` для будущих задач и `ai/paused-tasks.md` для прерванной
  незавершённой работы.
- Карточки проектов уже содержат стабильный `Project ID` и ссылку на
  `ai/current-task.md`.
- Утверждённая иерархия: `archiproject -> project -> task -> subtask`.
- Obsidian Kanban и Markdown-checkbox'ы не были подтверждены как канонические
  записи задач.

Вывод из этих фактов: связи archiproject и состояние ожидания должны быть
машиночитаемыми в архитектурных записях; отдельный редактируемый реестр задач
для этого не нужен.

## Единственная стратегия совместимости

Выбрана только **стратегия 1: расширить существующие
`ai/current-task.md` и `ai/future-tasks.md` машиночитаемыми полями**.

`ai/current-task.md` остаётся единственной канонической записью текущей задачи
проекта. В нём может быть ровно один объект `task`. Его подзадачи вложены в
этот объект и не образуют отдельный реестр. Будущие задачи остаются только в
`ai/future-tasks.md`; после продвижения запись копируется в текущую задачу по
существующему правилу шаблона.

Стратегия 2 (производный компактный индекс) отклонена: при ручном обновлении
она создаёт второй изменяемый слой задач. Стратегия 3 (новое каноническое
хранилище с миграцией) отклонена: она заменяет совместимые файлы без
подтверждённой необходимости.

Машиночитаемые блоки — канонические значения внутри уже существующих файлов.
Заголовки и пояснительный текст не должны повторять эти значения как отдельные
изменяемые поля. Маршрутизация, Obsidian и рабочие представления читают эти
файлы или их производные представления и не записывают задачи в другом месте.

## Таблица полей и контрактов

Метка `existing` означает уже имеющееся поле или контейнер. `new-required`
означает поле, которое нужно добавить при внедрении. `rejected` означает, что
поле или способ хранения запрещён этой минимальной моделью.

| Сущность | Поле | Статус | Контракт |
| --- | --- | --- | --- |
| archiproject | `id` | new-required | Стабильный slug; уникален в реестре archiproject. |
| archiproject | `name` | new-required | Человеческое название. |
| archiproject | `status` | new-required | Состояние archiproject, не состояние проекта или задачи. |
| archiproject | `target` | new-required | Числовая целевая величина. |
| archiproject | `unit` | new-required | Единица `target`; должна совпадать с учитываемым вкладом проектов. |
| archiproject | `due` | new-required | Срок в ISO-формате `YYYY-MM-DD`. |
| archiproject | сохранённое `completed` | rejected | Прогресс вычисляется из первичных вкладов проектов, чтобы не расходиться с ними. |
| archiproject | список задач | rejected | Задачи остаются в файлах своих проектов. |
| project | `Project ID` | existing | Уникальный идентификатор из карточки проекта. |
| project | `Name`, `Type`, `Status`, `Last updated`, `Purpose`, `Typical tasks`, `Memory entry point` | existing | Текущий минимум карточки проекта. |
| project | `primary_archiproject` | new-required | Машиночитаемый ID или `none`; ссылается на существующий `archiproject.id`. |
| project | `archiproject_contribution` | new-required | Неотрицательное число в единице основного archiproject либо `none`; единственный вклад проекта в его прогресс. |
| project | `related_archiprojects` | new-required | Уникальные ID через запятую либо `none`; ни один не равен primary ID. |
| project | сохранённый `work_state: waiting` | rejected | Project-level waiting вычисляется, а не дублируется в карточке. |
| project | самостоятельный список задач | rejected | Карточка ссылается на существующий файл текущей задачи. |
| task | один контейнер `task` в `ai/current-task.md` | existing | Сохраняет правило одной текущей задачи на проект. |
| task | `id` | new-required | Уникален в пределах проекта; будущая запись сохраняет этот ID после продвижения. |
| task | `title` | new-required | Короткое название для списка и представления. |
| current task record | верхнее `Status` | existing | Жизненный статус текущей записи: `empty`, `active`, `review`, `blocked`, `done`, `paused`; в схеме это `record_status`. |
| future task record | верхнее `Status` записи | existing | Статус бэклога: `idea`, `ready`, `blocked`, `promoted`, `done`, `dropped`; в схеме это `backlog_status`. |
| task | `execution_state` | new-required | Состояние исполнения только текущей задачи: `active`, `waiting`, `blocked` или `done`. |
| task | `stage`, `mode`, `goal`, `relevant_files`, `done_criteria`, `agent_handoff` | existing | Поля текущего шаблона; в машинном блоке используются один раз, без второй копии. |
| current task | `use_superpowers` | existing | Сохраняет существующее поле `Use Superpowers` без изменения значения. |
| future task | `priority`, `source`, `created`, `context`, `promotion_notes` | existing | Поля шаблона будущих задач. |
| future task | `goal`, `done_criteria` | existing | Канонические значения существующих `Proposed task` и `Acceptance criteria`. |
| future task | `use_superpowers` | new-required | Будущая задача получает это поле при миграции; в старом шаблоне его нет. |
| task | `subtasks` | new-required | Единственный вложенный массив подзадач этой задачи. |
| task | `project_id` | rejected | Проект однозначно задаёт путь файла и его карточка; дублировать ID не нужно. |
| task | отдельный task index | rejected | Индекс может быть только производным, неизменяемым представлением. |
| subtask | `id` | new-required | Уникален в массиве `task.subtasks`. |
| subtask | `title` | new-required | Короткое действие. |
| subtask | `execution_state` | new-required | `pending`, `active`, `waiting` или `done`. |
| subtask | `done_criteria` | new-required | Проверяемый результат. |
| task/subtask | `waiting` | new-required | Вложенный объект; допустим только при `execution_state: waiting`. |
| subtask | отдельный файл или глобальный ID | rejected | Подзадача не является самостоятельной текущей задачей или вторым хранилищем. |
| waiting | `waiting_for` | new-required | Внешняя сторона, событие или ответ, которого ждут. |
| waiting | `waiting_since` | new-required | Дата начала ожидания в ISO-формате. |
| waiting | `follow_up` | new-required | Ближайшая дата проверки или напоминания в ISO-формате. |
| waiting | `next_after_response` | new-required | Следующее действие после ответа. |
| waiting | отдельная waiting-база | rejected | Ожидание остаётся атрибутом задачи либо подзадачи. |

## Контракт archiproject

Канонический реестр archiproject — новый hub-owned controlled-memory файл
`ai/archiprojects.md`. Он содержит только archiproject, а не копии проектов и
задач. Каждая запись — Markdown-заголовок с fenced YAML-блоком; `id` —
единственная стабильная ссылка из карточки проекта:

```yaml
---
id: august-32-pages
name: Выпустить 32 страницы за август
status: active
target: 32
unit: pages
due: 2026-08-31
---
```

Прогресс archiproject вычисляется как сумма поля `archiproject_contribution`
всех карточек с тем же `primary_archiproject` и единицей `unit`. Связи из
`related_archiprojects` никогда не участвуют в этой сумме. Это сохраняет одну
primary-связь проекта и исключает двойной учёт.

## Контракт project

В карточку проекта добавляются три машинно-читаемых plain-text поля, не
изменяющие существующие обязательные поля валидатора:

```text
primary_archiproject: august-32-pages
archiproject_contribution: 0
related_archiprojects: none
```

`primary_archiproject` получает ID или `none`; он не может ссылаться на
отсутствующую запись. `archiproject_contribution` — неотрицательное число в
единице основного archiproject либо `none`. `related_archiprojects` —
уникальные дополнительные ID через запятую либо `none`; они не равны primary
ID и не дают вклад в прогресс. Существующий `Status` карточки остаётся
жизненным состоянием проекта; ожидание не заменяет и не расширяет это поле.

## Контракт task и subtask

Новая текущая задача использует один канонический машинный блок в
`ai/current-task.md`:

```yaml
task:
  id: T-20260823-001
  title: Подготовить минимальную модель работы
  execution_state: active
  stage: spec
  mode: architecture-update
  use_superpowers: yes
  goal: Зафиксировать минимальные контракты работы.
  relevant_files:
    - docs/superpowers/specs/2026-08-23-work-model-design.md
  done_criteria:
    - Спецификация содержит все пять контрактов.
  agent_handoff:
    last_agent: null
    what_changed: null
    open_risks: null
    next_agent_should_check: null
  subtasks:
    - id: ST-001
      title: Проверить обязательные поля
      execution_state: pending
      done_criteria: Все обязательные поля есть в спецификации.
```

Пустой `ai/current-task.md` остаётся машиночитаемым: верхнее поле
`Status: empty` означает `record_status: empty`, а объекта `task` в нём нет.
Если `Status` не `empty`, объект `task` обязателен.

`ai/future-tasks.md` хранит отдельный YAML-блок каждой будущей записи под её
существующим заголовком. Его верхний `Status` имеет только смысл
`backlog_status` и сохраняет существующий словарь бэклога. Блок сохраняет
`id`, `title`, `goal`, `done_criteria`, `priority`, `source`, `created`,
`context`, `promotion_notes` и `use_superpowers`; до продвижения у него нет
`execution_state`. Миграция разбирает существующий заголовок
`FT-YYYYMMDD-001 — Task title`: часть до тире переходит без изменения в `id`,
часть после тире — без изменения в `title`. Она также сопоставляет
`Proposed task` с `goal`, `Acceptance criteria` с `done_criteria`, а
`Use Superpowers` с `use_superpowers` без потери текста; отсутствующее у
старых future-задач `use_superpowers` получает явное значение `no` до ручного
изменения. Продвижение не создаёт новую задачу: тот же `id`, `title`, `goal`,
`done_criteria` и `use_superpowers` переходят в единственный объект `task`
текущего файла.

Подзадача не может быть второй текущей задачей проекта. Подзадача с
`execution_state: waiting` не переводит родительскую задачу в `waiting`, пока
у родителя есть другая выполнимая подзадача или действие.

## Контракт waiting

Ожидание хранится только во вложенном объекте `waiting` у task или subtask с
`execution_state: waiting`:

```yaml
execution_state: waiting
waiting:
  waiting_for: contractor
  waiting_since: 2026-08-23
  follow_up: 2026-08-26
  next_after_response: Review the contractor's answer
```

Все четыре поля объекта `waiting` обязательны при `execution_state: waiting`
и отсутствуют при любом другом состоянии. `waiting` означает внешний ожидаемый ответ или событие с
назначенной проверкой. `blocked` сохраняет существующий смысл препятствия,
которое нельзя снять только ожиданием внешнего ответа.

Task-level waiting относится к одной task или subtask и не меняет статус
проекта. Project-level waiting — только вычисляемое представление. Оно верно,
только когда есть хотя бы один открытый task/subtask с
`execution_state: waiting` и нет другого открытого действия со состоянием
`pending` или `active`. Пустой, завершённый или только `blocked` проект не
считается ожидающим. Наличие ожидающей подзадачи при другой активной работе не
делает проект ожидающим.

## Совместимость и rollback

Совместимость сохраняется по путям и ролям файлов: существующие маршрутизаторы
по-прежнему открывают `ai/current-task.md`, а будущая работа остаётся в
`ai/future-tasks.md`. Переход построчный и обратимый: сначала добавляется
машиночитаемый блок в тот же файл и сопоставляются `Use Superpowers`,
`Proposed task` и `Acceptance criteria`; только затем валидатор подтверждает
равенство старых и новых значений. Никакие задачи не копируются в Obsidian или
в отдельный индекс.

В первом совместимом релизе `ai/archiprojects.md` и три новых поля карточки
проекта только добавляются. `scripts/check-hub-registry.sh` валидирует
существование primary и related ID, отсутствие дублей, неотрицательный вклад и
совпадение единицы с archiproject; `scripts/hub-smoke-test.sh` получает
позитивные и негативные fixtures для каждого нарушения. Старые обязательные
поля карточки не изменяются. Отдельный коммит `feat: add archiproject metadata`
содержит только `ai/archiprojects.md`, `ai/project-cards/*.md`,
`scripts/check-hub-registry.sh`, `scripts/hub-smoke-test.sh` и связанные docs.
Его rollback — `git revert <that-commit>` с повторным запуском
`bash scripts/hub-smoke-test.sh`; он удаляет только новые файлы/поля и оставляет
прежние required fields и task-файлы нетронутыми.

После миграции task-файлов rollback выполняется Git-ревертом того же формата;
старый текст восстанавливается из пары «старое поле — новое каноническое
поле». При ошибке представления Obsidian откатывается только представление;
архитектурные записи задач, проектов и archiproject остаются единственным
источником данных.

## Контрольные проверки будущей реализации

```bash
rg -n 'Use Superpowers|Proposed task|Acceptance criteria|use_superpowers|goal|done_criteria' template/ai/current-task.md template/ai/future-tasks.md
rg -n 'primary_archiproject|archiproject_contribution|related_archiprojects' hub-template/ai/project-registry.md hub-template/ai/project-cards
rg -n 'archiprojects.md|execution_state|record_status|backlog_status|waiting_for|follow_up' docs/superpowers/specs/2026-08-23-work-model-design.md
```

Будущий валидатор обязан отклонить missing archiproject ID, duplicate related
ID, primary ID в related списке, отрицательный вклад, `waiting` без всех четырёх
полей и non-waiting объект с объектом `waiting`.
