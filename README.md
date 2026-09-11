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

Безопасный вариант — одна локальная source revision для preview и apply:

```bash
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/pinned-repository --dry-run
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/pinned-repository --apply --confirm-plan <PLAN_SHA256>
```

Для remote branch/tag preview дополнительно печатает `Resolved revision: <COMMIT_SHA>`. При apply передавайте именно этот SHA как `--ref <COMMIT_SHA>` вместе с подтверждённым plan hash. Если source bytes или план изменились, apply откажется продолжать.

Updater не перезаписывает изменённые managed files без baseline, не заменяет существующую пользовательскую Hub memory и делает rollback уже заменённых файлов при ошибке apply. Инструкции вида `curl ... | bash` не являются поддерживаемым update path.

## Source Of Truth / Канонические источники

- shared workflows, routing и security policy — установленный Hub; distributable source — `hub-template/`;
- project identity, status и exact path — `ai/project-registry.md` в Hub;
- текущее/приостановленное/будущее task state — `ai/current-task.md`, `ai/paused-tasks.md`, `ai/future-tasks.md` внутри проекта;
- project orientation — `ai/project-context.md`;
- долговечные решения — `ai/decisions.md`;
- семантическая история результатов — `ai/changelog.md`;
- подробные повторно используемые references — optional `knowledge/`, только по запросу;
- точная история файлов и кода — Git конкретного проекта.

Project cards, compact indexes и Obsidian — производные представления для навигации и планирования. Они не заменяют реестр, task memory, knowledge или Git как канонические источники.

## Проверки репозитория

Архитектурные проверки запускаются скриптами из `scripts/` и Python-тестами из `tests/`; Calendar policy имеет собственный pytest-suite в `calendar-policy/`.

Документация: `docs/`, быстрые инструкции: `getting-started/`.
