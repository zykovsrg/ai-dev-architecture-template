# Установка Personal AI Hub

Поддерживается один путь установки: Personal AI Hub.

## 1. Получите локальную копию репозитория

```bash
git clone https://github.com/zykovsrg/ai-dev-architecture-template.git
cd ai-dev-architecture-template
```

## 2. Установите Hub

```bash
bash scripts/install.sh /path/to/_ai-hub
```

Явно указать режим можно так:

```bash
bash scripts/install.sh --mode hub /path/to/_ai-hub
```

Скрипт создаёт/обновляет только Hub. Устаревший project-local дистрибутив не устанавливается.

## 3. Подключите проект через Hub

Используйте подходящий workflow:

- `hub-project-create` — новый проект;
- `hub-project-register` — проект уже лежит в разрешённом Hub root;
- `hub-project-migrate` — существующий проект нужно перенести/очистить от старых общих правил.

Перемещение, регистрация и очистка требуют своих preview/confirmation gates. Не копируйте shared rules вручную в проект.

## Что остаётся в проекте

Проект хранит собственную каноническую память (`ai/current-task.md`, `ai/future-tasks.md`, `ai/paused-tasks.md`, `ai/project-context.md`, `ai/decisions.md`, `ai/changelog.md`) и optional `knowledge/`. Общие workflows и security rules принадлежат Hub.

## Проверка

После установки запустите Hub environment/registry checks через поддерживаемые Hub workflows. Если проект переносится со старой схемы, сначала используйте `hub-project-migrate`; не восстанавливайте удалённые generic rule copies.
