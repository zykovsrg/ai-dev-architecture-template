# Обновление архитектуры в уже используемых проектах

Эта инструкция нужна для проектов, где архитектура уже установлена.

Цель обновления: быстро подтянуть актуальные правила и base skills из `zykovsrg/ai-dev-architecture-template`, не затирая рабочую память конкретного проекта.

## Что обновляется автоматически

Updater обновляет protected architecture files:

```text
AGENTS.md
CLAUDE.md
ai/architecture.md
ai/external-tools.md
ai/skills/*
```

Если в шаблоне появятся `.claude/` или `.codex/`, updater также сможет подтянуть файлы из этих директорий.

## Что не перезаписывается

Updater не затирает controlled memory files проекта:

```text
ai/project-context.md
ai/current-task.md
ai/decisions.md
ai/changelog.md
ai/paused-tasks.md
ai/future-tasks.md
```

Если memory-файла нет, updater создаст его из шаблона. Если файл уже есть, он останется как есть.

## Быстрый безопасный запуск

Перейди в проект:

```bash
cd /path/to/project
```

Сначала запусти dry run:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --dry-run
```

Dry run ничего не меняет. Он только показывает diff.

Если diff нормальный, примени обновление и сразу закоммить:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --apply --commit
```

Коммит будет называться:

```text
chore: update AI development architecture
```

## Если проект не в чистом состоянии

По умолчанию updater не применяет изменения, если в проекте уже есть незакоммиченные изменения.

Сначала лучше сохранить текущую работу:

```bash
git status
git add .
git commit -m "wip: save current work"
```

Если ты сознательно хочешь применить обновление поверх незакоммиченных изменений, добавь флаг:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --apply --commit --allow-dirty
```

Используй `--allow-dirty` только если понимаешь, какие изменения уже есть в проекте.

## Локальное обновление из клона архитектуры

Если репозиторий архитектуры уже скачан локально:

```bash
cd /path/to/project
bash /path/to/ai-dev-architecture-template/scripts/update-installed-architecture.sh --source /path/to/ai-dev-architecture-template --dry-run
```

Применить и закоммитить:

```bash
bash /path/to/ai-dev-architecture-template/scripts/update-installed-architecture.sh --source /path/to/ai-dev-architecture-template --apply --commit
```

## Обновление нескольких проектов

Создай список проектов:

```bash
cat > ~/ai-projects.txt <<'EOF'
/Users/zykovsrg/projects/project-a
/Users/zykovsrg/projects/project-b
/Users/zykovsrg/projects/project-c
EOF
```

Сначала проверь dry run по каждому проекту:

```bash
while read project; do
  echo "=== $project ==="
  cd "$project" && curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --dry-run
done < ~/ai-projects.txt
```

Если всё ок, применяй:

```bash
while read project; do
  echo "=== $project ==="
  cd "$project" && curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh | bash -s -- --apply --commit
done < ~/ai-projects.txt
```

## После обновления

После обновления открой проект в Codex или Claude Code и попроси агента:

```text
Run environment-check.
```

Финальное меню после `environment-check` — справочное. Оно не означает, что агент должен автоматически запускать `task-switch`, `task-finish`, `architecture-update` или другие workflow.

## Внимание: --apply перезаписывает защищённые файлы целиком

`--apply` копирует свежие версии защищённых файлов (`AGENTS.md`, `CLAUDE.md`, скиллы) поверх текущих. Если вы вручную меняли эти файлы под свой проект и закоммитили, ваши правки будут затёрты. Проверка чистоты дерева ловит только незакоммиченные изменения, не закоммиченные.

Поэтому всегда сначала `--dry-run` и читайте diff. Контролируемая память проекта (`ai/current-task.md`, `ai/decisions.md` и т.д.) при этом не трогается.

## Когда не использовать updater

Не используй updater вместо полноценного review, если:

- проект сильно поменял собственные `AGENTS.md` или `CLAUDE.md`;
- в `ai/skills/` есть локальные изменения base skills;
- ты не уверен, какие правила проекта были изменены вручную;
- проект сейчас находится в середине рискованного refactor.

В таких случаях сначала запускай `--dry-run`, затем проси агента провести `architecture-update` review diff.
