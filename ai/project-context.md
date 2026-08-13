# Project Context

Этот файл уникален для проекта. Заполни его после установки шаблона в реальный проект.

## Что это за проект

Локальная рабочая копия `zykovsrg/ai-dev-architecture-template`.

Проект содержит переиспользуемую архитектуру одиночной AI-разработки:
документацию, шаблонные entry files, рабочую память `ai/*`, базовые skills и
скрипты установки/обновления.

Эта папка использует архитектуру для доработки самой архитектуры. Поэтому в
корне есть установленная рабочая копия (`AGENTS.md`, `CLAUDE.md`, `ai/*`), а
канонический шаблон для пользователей лежит в `template/`.

`knowledge/` хранит долговечные подтверждённые сведения; содержимое записей
здесь не дублируется.

## Стек

- Markdown для правил, документации, skills и рабочей памяти.
- Bash для install/update/smoke-test скриптов.
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
bash scripts/smoke-test.sh
```

## Главные папки и файлы

- `template/` — файлы, которые устанавливаются в пользовательские проекты.
- `template/ai/skills/*/SKILL.md` — базовые workflow skills архитектуры.
- `docs/` — документация для установки, обновления и использования.
- `ai/superpowers/plans/` — планы для сложных изменений архитектуры.
- `scripts/install.sh` — установка шаблона в проект.
- `scripts/update-installed-architecture.sh` — обновление архитектуры в уже установленном проекте.
- `scripts/check-consistency.sh` — проверка canonical lists.
- `scripts/smoke-test.sh` — smoke tests установки и обновления.
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

- `template/` остаётся источником файлов, устанавливаемых пользователям.
- Корневые `ai/*` описывают работу над этим репозиторием, а не являются частью устанавливаемого шаблона.
- Не смешивать активную задачу, paused tasks и future tasks.
- Изменения правил архитектуры делать через `architecture-update` и проверять consistency/smoke tests.
- Не перезаписывать controlled memory в установленных проектах через updater.
- Если меняются canonical lists, запускать `scripts/check-consistency.sh`.

## Хрупкие зоны

- Синхронность дублирующихся правил между `template/AGENTS.md`, `template/CLAUDE.md`, `template/ai/architecture.md`, docs и skills.
- Updater может затрагивать пользовательские проекты; любые изменения protected/controlled file lists требуют осторожной проверки.
- Bash-скрипты должны оставаться совместимыми с macOS `/bin/bash` 3.2.
- Корневая установленная архитектура и `template/` похожи по структуре, но имеют разные роли.
