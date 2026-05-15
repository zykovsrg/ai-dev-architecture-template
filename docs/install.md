# Инструкция по установке

## 1. Склонировать репозиторий шаблона

```bash
cd ~/Documents
git clone git@github.com:zykovsrg/ai-dev-architecture-template.git
```

## 2. Перейти в проект

```bash
cd /path/to/project
```

Пример:

```bash
cd /Users/zykovsrg/Desktop/goal-planner-macos
```

## 3. Безопасно скопировать шаблон

```bash
rsync -av --ignore-existing ~/Documents/ai-dev-architecture-template/template/ ./
```

Эта команда:

- копирует новые файлы в проект;
- не перезаписывает существующие файлы;
- снижает риск потерять проектные данные.

## 4. Проверить установленные файлы

```bash
ls AGENTS.md CLAUDE.md
find ai -maxdepth 4 -type f | sort
```

Ожидаемые файлы:

```text
AGENTS.md
CLAUDE.md
ai/architecture.md
ai/changelog.md
ai/external-tools.md
ai/current-task.md
ai/paused-tasks.md
ai/decisions.md
ai/project-context.md
ai/skills/architecture-update/SKILL.md
ai/skills/environment-check/SKILL.md
ai/skills/bugfix-workflow/SKILL.md
ai/skills/copy-review/SKILL.md
ai/skills/release-check/SKILL.md
ai/skills/security-review/SKILL.md
ai/skills/task-finish/SKILL.md
ai/skills/task-switch/SKILL.md
ai/skills/ui-review/SKILL.md
ai/skills/write-tests/SKILL.md
```

## 5. Заполнить проектные файлы

Для каждого проекта нужно отдельно заполнить:

- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md
ai/external-tools.md`
- `ai/current-task.md
ai/paused-tasks.md`

Готовые промты есть в `docs/prompts.md`.
