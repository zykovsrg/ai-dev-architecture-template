# Инструкция по обновлению

## 1. Обновить репозиторий шаблона

```bash
cd ~/Documents/ai-dev-architecture-template
git pull origin main
```

## 2. Добавить новые файлы шаблона в проект

```bash
cd /path/to/project
rsync -av --ignore-existing ~/Documents/ai-dev-architecture-template/template/ ./
```

Эта команда копирует только те файлы, которых ещё нет в проекте. Она не перезаписывает существующие файлы.

После v6.0 проверь, появился ли новый файл:

```bash
test -f ai/future-tasks.md || cp ~/Documents/ai-dev-architecture-template/template/ai/future-tasks.md ai/future-tasks.md
```

## 3. Не перезаписывать файлы вслепую

Сначала сравни шаблон и проект:

```bash
diff -ru ~/Documents/ai-dev-architecture-template/template/AGENTS.md ./AGENTS.md
diff -ru ~/Documents/ai-dev-architecture-template/template/CLAUDE.md ./CLAUDE.md
diff -ru ~/Documents/ai-dev-architecture-template/template/ai/architecture.md ./ai/architecture.md
diff -ru ~/Documents/ai-dev-architecture-template/template/ai/external-tools.md ./ai/external-tools.md
diff -ru ~/Documents/ai-dev-architecture-template/template/ai/skills ./ai/skills
```

## 4. Protected architecture files

Эти файлы задают правила работы агентов. Обновляй их только через `architecture-update` и после подтверждения пользователя:

- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`

При обновлении существующего проекта не копируй их поверх текущих файлов без diff и ревью.

## 5. Controlled memory files

Эти файлы содержат память конкретного проекта. Не заменяй их шаблоном:

- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`

Их можно обновлять только как проектную память:

- `ai/current-task.md` — через текущую задачу, `task-switch` или `task-finish`;
- `ai/paused-tasks.md` — через `task-switch`;
- `ai/future-tasks.md` — для будущих задач, которые явно сохранены пользователем или подтверждены как future task candidates;
- `ai/project-context.md` — после подтверждения, если изменились стек, команды, структура, модель данных, инварианты или хрупкие зоны;
- `ai/decisions.md` — когда появилось устойчивое решение, которое будущие агенты не должны сломать;
- `ai/changelog.md` — для заметных изменений за последние 2–4 недели.

## 6. Правило безопасного обновления

Для уже существующего проекта:

1. Сравни файлы шаблона и проекта.
2. Отдели protected architecture files от controlled memory files.
3. Сохрани проектные добавления.
4. Попроси агента предложить точные изменения.
5. Применяй только одобренные изменения.
6. Перед коммитом запусти `release-check`.
7. После обновления запусти `environment-check` и проверь финальное меню доступных commands и skills.

Меню после `environment-check` справочное. Оно не означает, что агент должен автоматически запускать `task-switch`, `task-finish`, `architecture-update` или другие workflow.

## 7. Когда полезен code-review-graph

Предложи `code-review-graph`, если:

- непонятно, какие файлы связаны между собой;
- diff затрагивает несколько модулей;
- есть риск сломать соседние экраны или зависимости;
- нужно быстро понять радиус изменений;
- обновление затрагивает новые сервисы, резолверы, adapters или architecture-sensitive logic.

Если `code-review-graph` недоступен, это предупреждение, а не блокер по умолчанию.