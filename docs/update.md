# Инструкция по обновлению

Для уже используемых проектов основной способ обновления — автоматический updater:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --dry-run
```

Если diff нормальный:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --apply --commit
```

Подробная инструкция — в `docs/update-installed-projects.md`.

## Что делает updater

Updater обновляет protected architecture files:

```text
AGENTS.md
CLAUDE.md
ai/architecture.md
ai/external-tools.md
ai/skills/*
```

Controlled memory files не перезаписываются:

```text
ai/current-task.md
ai/paused-tasks.md
ai/future-tasks.md
ai/project-context.md
ai/decisions.md
ai/changelog.md
```

Если controlled memory file отсутствует, updater создаёт его из шаблона. Если файл уже есть, он остаётся как есть.

## 1. Обновить репозиторий шаблона вручную

Если используешь локальный клон шаблона:

```bash
cd ~/Documents/ai-dev-architecture-template
git pull origin main
```

## 2. Запустить updater из локального клона

```bash
cd /path/to/project
bash ~/Documents/ai-dev-architecture-template/scripts/update-installed-architecture.sh --source ~/Documents/ai-dev-architecture-template --dry-run
```

Применить и закоммитить:

```bash
bash ~/Documents/ai-dev-architecture-template/scripts/update-installed-architecture.sh --source ~/Documents/ai-dev-architecture-template --apply --commit
```

## 3. Если updater недоступен

Можно вручную добавить новые файлы шаблона без перезаписи существующих файлов:

```bash
cd /path/to/project
rsync -av --ignore-existing ~/Documents/ai-dev-architecture-template/template/ ./
```

Эта команда копирует только те файлы, которых ещё нет в проекте. Она не перезаписывает существующие файлы.

После v6.0 проверь, появился ли новый файл:

```bash
test -f ai/future-tasks.md || cp ~/Documents/ai-dev-architecture-template/template/ai/future-tasks.md ai/future-tasks.md
```

## 4. Не перезаписывать файлы вслепую

Сначала сравни шаблон и проект:

```bash
diff -ru ~/Documents/ai-dev-architecture-template/template/AGENTS.md ./AGENTS.md
diff -ru ~/Documents/ai-dev-architecture-template/template/CLAUDE.md ./CLAUDE.md
diff -ru ~/Documents/ai-dev-architecture-template/template/ai/architecture.md ./ai/architecture.md
diff -ru ~/Documents/ai-dev-architecture-template/template/ai/external-tools.md ./ai/external-tools.md
diff -ru ~/Documents/ai-dev-architecture-template/template/ai/skills ./ai/skills
```

## 5. Protected architecture files и controlled memory files

Полные списки защищённых файлов и controlled memory — в [file-roles.md](file-roles.md).

При обновлении существующего проекта не копируй protected architecture files поверх текущих файлов без diff и ревью. Controlled memory files не заменяй шаблоном.

Их можно обновлять только как проектную память:

- `ai/current-task.md` — через текущую задачу, `task-switch` или `task-finish`;
- `ai/paused-tasks.md` — через `task-switch`;
- `ai/future-tasks.md` — для будущих задач, которые явно сохранены пользователем или подтверждены как future task candidates;
- `ai/project-context.md` — после подтверждения, если изменились стек, команды, структура, модель данных, инварианты или хрупкие зоны;
- `ai/decisions.md` — когда появилось устойчивое решение, которое будущие агенты не должны сломать;
- `ai/changelog.md` — через подтверждённый `task-finish` или approved `architecture-update`.

## 7. Правило безопасного обновления

Для уже существующего проекта:

1. Запусти updater в `--dry-run`.
2. Сравни protected architecture files и controlled memory files.
3. Убедись, что проектные добавления не будут потеряны.
4. Применяй обновление только если diff понятен.
5. Перед merge или релизом запусти `release-check`.
6. После обновления запусти `environment-check` и проверь финальное меню доступных commands и skills.

Меню после `environment-check` справочное. Оно не означает, что агент должен автоматически запускать `task-switch`, `task-finish`, `architecture-update` или другие workflow.

## 8. Когда полезен code-review-graph

Предложи `code-review-graph`, если:

- непонятно, какие файлы связаны между собой;
- diff затрагивает несколько модулей;
- есть риск сломать соседние экраны или зависимости;
- нужно быстро понять радиус изменений;
- обновление затрагивает новые сервисы, резолверы, adapters или architecture-sensitive logic.

Если `code-review-graph` недоступен, это предупреждение, а не блокер по умолчанию.
