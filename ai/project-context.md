# Project Context

## Latest handoff — 2026-09-10

The audit/refactor branch was merged into main (fbd4c1d). The combined hub
release ends at d40ab25 and was installed into the parent personal hub.
See `ai/refactor-handoff-2026-09-10.md` for the actual outcome, limitations,
user decisions, and document map. Read it before claiming full verification
or starting another architecture update. The current-task template is empty;
this does not mean the conversation's work or closure review never happened.

## Что это за проект

Локальная рабочая копия `zykovsrg/ai-dev-architecture-template`.

Проект содержит переиспользуемую архитектуру одиночной AI-разработки:
документацию, шаблонные entry files, рабочую память `ai/*`, базовые skills и
скрипты установки/обновления.

Эта папка использует архитектуру для доработки самой архитектуры. Поэтому в
корне есть установленная рабочая копия (`AGENTS.md`, `CLAUDE.md`, `ai/*`), а
канонический шаблон для пользователей лежит в `hub-template/`.

`knowledge/` хранит долговечные подтверждённые сведения; содержимое записей
здесь не дублируется.

## Стек

- Markdown для правил, документации, skills и рабочей памяти.
- Bash для install и проверочных скриптов.
- Git/GitHub как основной способ сохранять и распространять изменения.

## Как запустить локально

Это не приложение с dev-сервером. Основная работа — редактирование Markdown и
Bash-файлов.

Для проверки локальной установки использовать:

```bash
bash scripts/install.sh /tmp/ai-dev-architecture-install-check
```

## Как собрать

Сборки нет. Репозиторий распространяется как набор файлов шаблона и скриптов.

## Как запустить тесты

Основные проверки:

```bash
bash scripts/check-consistency.sh
```

## Главные папки и файлы

- `hub-template/` — файлы, которые устанавливаются в Hub.
- `hub-template/ai/skills/*/SKILL.md` — базовые workflow skills архитектуры.
- `calendar-policy/` — исходники calendar MCP; устанавливаются через `scripts/sync-calendar-policy.sh`.
- `docs/` — документация для установки, обновления и использования.
- `docs/superpowers/plans/`, `docs/superpowers/specs/` — планы и спеки для сложных изменений архитектуры.
- `scripts/install.sh` — установка Hub.
- `scripts/hub_release.py` — preview/apply/drift сборка релиза Hub.
- `scripts/check-consistency.sh` — проверка canonical lists.
- `AGENTS.md`, `CLAUDE.md`, `ai/*` в корне — установленная рабочая память для доработки самой архитектуры.

## Главные экраны или модули

Экранов нет. Главные модули — entry files, controlled memory files, skills,
docs и updater/install scripts.

## Модель данных или ключевые сущности

- Protected architecture files — правила и базовые skills, которые меняются только через подтверждённый architecture-update workflow.
- Controlled memory files — текущая задача, будущие задачи, changelog, decisions и проектный контекст.
- Current task — ровно одна активная рабочая задача.
- Future tasks — backlog идей, не активная работа.
- Paused tasks — только временно прерванная активная работа.
- Canonical lists — списки protected files и controlled memory, проверяемые `scripts/check-consistency.sh`.

## Инварианты проекта

Правила, которые нельзя ломать.

- `hub-template/` остаётся источником файлов, устанавливаемых пользователям.
- Корневые `ai/*` описывают работу над этим репозиторием, а не являются частью устанавливаемого шаблона.
- Не смешивать активную задачу, paused tasks и future tasks.
- Изменения правил архитектуры делать через `architecture-update` и проверять consistency/smoke tests.
- Не перезаписывать controlled memory в установленных проектах через updater.
- Если меняются canonical lists, запускать `scripts/check-consistency.sh`.

## Хрупкие зоны

- Синхронность дублирующихся правил между `hub-template/AGENTS.md`, `hub-template/CLAUDE.md`, `hub-template/ai/architecture.md`, docs и skills.
- Updater может затрагивать пользовательские проекты; любые изменения protected/controlled file lists требуют осторожной проверки.
- Bash-скрипты должны оставаться совместимыми с macOS `/bin/bash` 3.2.
- Корневая установленная архитектура и `hub-template/` похожи по структуре, но имеют разные роли.
