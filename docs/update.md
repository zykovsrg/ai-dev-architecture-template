# Инструкция по обновлению

## Обновить репозиторий шаблона

```bash
cd ~/Documents/ai-dev-architecture-template
git pull origin main
```

## Добавить новые файлы шаблона в проект

```bash
cd /path/to/project
rsync -av --ignore-existing ~/Documents/ai-dev-architecture-template/template/ ./
```

Эта команда копирует только те файлы, которых ещё нет в проекте.

## Обновить уже существующие файлы

Не перезаписывай существующие `AGENTS.md`, `CLAUDE.md` или `ai/skills/*/SKILL.md` вслепую.

Сначала сравни шаблон и проект:

```bash
diff -ru ~/Documents/ai-dev-architecture-template/template/AGENTS.md ./AGENTS.md
diff -ru ~/Documents/ai-dev-architecture-template/template/CLAUDE.md ./CLAUDE.md
diff -ru ~/Documents/ai-dev-architecture-template/template/ai/skills ./ai/skills
```

Проектные файлы нельзя перезаписывать без отдельной проверки:

- `ai/project-context.md`
- `ai/current-task.md`
- `ai/decisions.md`
- `ai/changelog.md`

## Правило безопасного обновления

Для уже существующего проекта:

1. Сравни файлы шаблона и проекта.
2. Сохрани проектные добавления.
3. Попроси агента предложить точные изменения.
4. Применяй только одобренные изменения.
5. Перед коммитом запусти ревью.

- непонятно, какие файлы связаны между собой;
- diff затрагивает несколько модулей;
- есть риск сломать соседние экраны или зависимости;
- нужно быстро понять радиус изменений.
