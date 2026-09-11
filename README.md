# AI-архитектура разработки

Personal AI Hub — единая точка входа для работы AI-агентов с несколькими проектами без потери контекста и без копирования общих правил в каждый репозиторий.

Архитектура помогает хранить канонические задачи и решения, переключаться между Codex/Claude Code, читать только нужный контекст, подтверждать изменения до записи и не смешивать память разных проектов.

## Поддерживаемая модель

Общие правила, маршрутизация, security gates и shared workflows принадлежат Hub. Каждый проект остаётся отдельным Git-репозиторием и хранит только свою локальную память и, при необходимости, knowledge.

Основной путь:

```text
install Hub → register/create/migrate project → work through Hub
```

Проекты Hub находятся в `_ai-hub/projects/<project-id>`. Реестр Hub определяет identity/path проекта. До подтверждения проектного scope Hub не должен читать его код, память или knowledge, кроме специально разрешённого read-only personal-assistant scope для канонических задач.

## Установка

Склонируйте этот репозиторий локально и запустите:

```bash
git clone https://github.com/zykovsrg/ai-dev-architecture-template.git
cd ai-dev-architecture-template
bash scripts/install.sh /path/to/_ai-hub
```

Явная форма эквивалентна:

```bash
bash scripts/install.sh --mode hub /path/to/_ai-hub
```

После установки используйте Hub workflows:

- `hub-project-register` — зарегистрировать уже находящийся в Hub проект;
- `hub-project-create` — создать новый проект;
- `hub-project-migrate` — безопасно перенести существующий проект;
- `hub-project-switch` — подтвердить переход в конкретный проект;
- `hub-task-intake`, `hub-task-switch`, `hub-task-finish` — вести задачи;
- `hub-knowledge-enable`, `hub-knowledge-capture`, `hub-knowledge-review` — optional knowledge по запросу.

Устаревший project-local режим больше не устанавливается и не обновляется. Старые проекты переводятся через `hub-project-migrate`; их проектная память и knowledge должны сохраняться.

## Обновление Hub

Работайте из локально скачанного репозитория. Сначала показывайте preview, затем применяйте только подтверждённый план:

```bash
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/ai-dev-architecture-template --dry-run
```

Точный content-addressed update flow дополнительно проверяется release-тестами. Не применяйте непоказанные изменения и не перезаписывайте пользовательскую память Hub.

## Канонические источники

- shared workflows и security — `hub-template/`;
- project identity/path — Hub registry;
- текущие/будущие/приостановленные задачи — `ai/current-task.md`, `ai/future-tasks.md`, `ai/paused-tasks.md` внутри проекта;
- ориентация по проекту — `ai/project-context.md`;
- долговечные решения — `ai/decisions.md`;
- семантическая история результата — `ai/changelog.md`;
- подробные повторно используемые материалы — optional `knowledge/`;
- точная история файлов и кода — Git.

Derived indexes и Obsidian-представления помогают искать и планировать, но не заменяют канонические записи.

## Проверки репозитория

Архитектурные проверки запускаются скриптами из `scripts/` и Python-тестами из `tests/`; Calendar policy имеет собственный pytest-suite в `calendar-policy/`.

Документация: `docs/`, быстрые инструкции: `getting-started/`.
