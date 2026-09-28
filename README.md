# AI-архитектура разработки

Personal AI Hub — одна точка входа для AI-агентов (Claude Code и Codex), которые работают с несколькими проектами. Общие правила живут в Hub один раз, а каждый проект хранит только свою память.

Hub помогает вести задачи, читать только нужный контекст, подтверждать изменения до записи и не смешивать память разных проектов.

## Как это устроено

Hub — папка `_ai-hub`. Проекты лежат внутри неё: `_ai-hub/projects/<project-id>`. Каждый проект — отдельный Git-репозиторий. Реестр Hub (`ai/project-registry.md`) знает имя и точный путь каждого проекта. До подтверждения проекта Hub не читает его код и память; исключение — сводка задач по всем активным проектам (только файлы задач).

Основной путь:

```text
установить Hub → создать / зарегистрировать / перенести проект → работать через Hub
```

## Модули

Hub собран из модулей. Каждый модуль лежит в `modules/<id>/` и описан паспортом `module.md`.

| Модуль | Что делает | Можно выключить |
| --- | --- | --- |
| core | базовые правила, вход в Hub, выбор проекта | нет |
| projects | реестр, создание, регистрация, перенос и переключение проектов | нет |
| tasks | задачи проекта: поставить, переключить, закрыть; сводка задач | нет |
| knowledge | папка `knowledge/` в проекте; предложения по заметкам встречи для одного проекта | да |
| goals | числовые цели и журнал прогресса | да |
| learning | разбор сессии при закрытии задачи, журнал трудностей | да |
| calendar | безопасное чтение и изменение Apple Calendar | да |
| planning | план дня, вечерний и недельный обзор (нужен calendar) | да |
| obsidian | доски проектов в Obsidian | да |
| release | установка, обновление, проверки; в Hub не ставится | — |

Как включать и выключать модули и что при этом сохраняется — [`docs/update.md`](docs/update.md#модули). Как модули связаны между собой — [`docs/concepts.md`](docs/concepts.md#modules).

## Установка

```bash
git clone https://github.com/zykovsrg/ai-dev-architecture-template.git
cd ai-dev-architecture-template
bash scripts/install.sh /path/to/_ai-hub
```

Подробно: [`docs/install.md`](docs/install.md). После установки проекты подключаются через Hub: `hub-project-create` (новый), `hub-project-register` (уже лежит в `_ai-hub/projects`), `hub-project-migrate` (перенести старый).

## Обновление

Обновляется только Hub: сначала просмотр плана, потом применение ровно этого плана. Команды, модули и откат: [`docs/update.md`](docs/update.md).

## Source Of Truth / Канонические источники

- общие правила, маршрутизация и безопасность — установленный Hub; исходник для установки — `modules/`;
- имя, статус и точный путь проекта — `ai/project-registry.md` в Hub;
- текущая, приостановленная и будущие задачи — `ai/current-task.md`, `ai/paused-tasks.md`, `ai/future-tasks.md` внутри проекта;
- описание проекта — `ai/project-context.md`;
- важные решения — `ai/decisions.md`;
- история результатов — `ai/changelog.md`;
- справочные материалы — необязательная папка `knowledge/`, только по запросу;
- точная история файлов и кода — Git проекта.

Карточки проектов, compact-индексы и Obsidian — только удобные представления. Они не заменяют реестр, файлы задач, knowledge или Git.

## Проверки репозитория

Те же проверки, что в CI (`.github/workflows/hub-architecture-tests.yml`), из корня репозитория:

```bash
bash scripts/check-consistency.sh
bash scripts/hub-smoke-test.sh
bash scripts/architecture-test.sh
bash scripts/assistant-workflows-test.sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s modules/obsidian/tests -v
python3 -m unittest discover -s modules/planning/tests -v
```

`architecture-test.sh` включает строгую проверку границ модулей: `python3 scripts/check-module-boundaries.py --strict`.

Тесты сервера календаря — отдельно, им нужен Python 3.11+ и pytest:

```bash
python3 -m pip install -e ./modules/calendar/policy pytest pytest-asyncio
(cd modules/calendar/policy && python3 -m pytest -q)
```

CI использует Python 3.11. Скрипты, которые ставятся в Hub, должны работать и на системном Python 3.9 в macOS; синтаксис аннотаций для этого проверяет `tests/test_python39_compat.py`.

Документация: `docs/`, короткая памятка: `getting-started/help.md`, история изменений: `CHANGELOG.md`.
