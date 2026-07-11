# AI Dev Architecture Template

Готовая архитектура для разработки с AI-агентами: Codex, Claude Code и другими coding agents. Подходит для одиночной работы над проектом.

## Что это решает

AI-агент забывает контекст между чатами. Эта архитектура хранит контекст в файлах репозитория, поэтому:

- задачу можно продолжить в новом чате или в другом агенте без пересказа;
- текущая задача, будущие идеи и принятые решения лежат в разных файлах и не смешиваются;
- агент тратит меньше токенов: читает только нужные файлы, а не всю историю;
- правила проекта не теряются и не превращаются в скрытый технический долг.

## С чего начать

Впервые здесь — откройте [docs/start-here.md](docs/start-here.md). Там пошаговые сценарии: новый проект, обновление старой версии, первая задача, работа с Superpowers, закрытие задачи, работа без GitHub.

Непонятные термины объясняются в [docs/concepts.md](docs/concepts.md).

## Установка в проект

Самый простой путь — [универсальный стартовый промт](prompt/README.md). Скопируйте его в AI-агента, открытого в папке проекта. Агент сам установит или обновит архитектуру.

Ручной способ:

1. Склонируйте репозиторий шаблона (один раз):

   ```bash
   cd ~/Documents
   git clone git@github.com:zykovsrg/ai-dev-architecture-template.git
   ```

2. Перейдите в свой проект:

   ```bash
   cd /path/to/project
   ```

3. Скопируйте файлы шаблона. Команда не перезаписывает уже существующие файлы:

   ```bash
   rsync -av --ignore-existing ~/Documents/ai-dev-architecture-template/template/ ./
   ```

   То же самое делает скрипт `scripts/install.sh`.

4. Заполните `ai/project-context.md` (что за проект) и `ai/current-task.md` (текущая задача). Остальные файлы памяти — `ai/decisions.md`, `ai/changelog.md`, `ai/paused-tasks.md`, `ai/future-tasks.md` — можно оставить пустыми шаблонами.

Подробности — в [docs/install.md](docs/install.md). Удаление — в [docs/uninstall.md](docs/uninstall.md).

## Обновление в уже используемом проекте

Безопасный способ: скачать скрипт, посмотреть его глазами, затем запустить:

```bash
curl -fsSL https://raw.githubusercontent.com/zykovsrg/ai-dev-architecture-template/main/scripts/update-installed-architecture.sh -o /tmp/update-installed-architecture.sh
less /tmp/update-installed-architecture.sh
bash /tmp/update-installed-architecture.sh --check
```

`--check` печатает версии и dry-run, ничего не меняя. Дальше:

```bash
bash /tmp/update-installed-architecture.sh --dry-run   # показать, что изменится
bash /tmp/update-installed-architecture.sh --apply --commit   # применить и закоммитить
```

Скрипт обновляет файлы архитектуры и base skills, но не трогает рабочую память проекта: `ai/project-context.md`, `ai/current-task.md`, `ai/decisions.md`, `ai/changelog.md`, `ai/paused-tasks.md`, `ai/future-tasks.md`.

Подробная инструкция — в [docs/update-installed-projects.md](docs/update-installed-projects.md).

## Как устроены файлы

Входные файлы — их агент читает всегда:

- `AGENTS.md` — входной файл для Codex.
- `CLAUDE.md` — входной файл для Claude Code.

Файлы памяти проекта — их агент читает по необходимости:

- `ai/current-task.md` — текущая задача.
- `ai/paused-tasks.md` — задачи, поставленные на паузу через `task-switch`.
- `ai/future-tasks.md` — идеи и будущие задачи вне текущей работы.
- `ai/project-context.md` — что за проект: стек, структура, хрупкие места.
- `ai/decisions.md` — устойчивые решения, которые будущие агенты не должны сломать.
- `ai/changelog.md` — последние заметные изменения.
- `ai/external-tools.md` — ожидаемые внешние tools и методологии.

Skills — переиспользуемые процедуры в `ai/skills/*/SKILL.md`. Всего 11 base skills:

- `task-intake` — принимает новую задачу и записывает её в `ai/current-task.md`.
- `task-switch` — безопасно переключает незавершённые задачи.
- `task-finish` — проверяет, можно ли закрыть задачу, и чистит контекст после подтверждения.
- `environment-check` — проверяет установку архитектуры и внешние tools, показывает меню.
- `start-screen` — короткий стартовый экран по запросу.
- `architecture-update` — меняет правила разработки только после явного подтверждения.
- `ui-review` — проверка UI-задач.
- `write-tests` — тесты для рискованных изменений.
- `security-review` — проверка безопасности.
- `release-check` — проверка перед merge или релизом.
- `copy-review` — проверка текстов.

Полные списки защищённых файлов и controlled memory — в [docs/file-roles.md](docs/file-roles.md).

## Структура репозитория

```text
template/   — то, что копируется в ваш проект (AGENTS.md, CLAUDE.md, ai/)
prompt/     — универсальный стартовый промт
docs/       — документация: установка, обновление, понятия, сценарии
scripts/    — install.sh, update-installed-architecture.sh, check-consistency.sh
```

Этот GitHub-репозиторий — источник правды для архитектуры.

## Как агент работает с задачами

- Новая сессия или новый чат: агент запускает `environment-check` и показывает меню. Меню ничего не запускает само.
- Перед реальной работой: `task-intake` записывает задачу в `ai/current-task.md`.
- Новый запрос по умолчанию считается другой задачей. Он остаётся в текущей задаче, только если попадает в записанные Done criteria. Иначе агент задаёт вопрос: расширить задачу, переключиться через `task-switch` или записать в `ai/future-tasks.md`.
- Незавершённая задача не перезаписывается молча — только через `task-switch` с подтверждением.
- Закрытие задачи — через `task-finish`. Если настроен GitHub remote, результат обязательно коммитится и пушится; без GitHub — сохраняется локально с объяснением.
- Баги, регрессии, краши и сложные задачи: агент использует Superpowers, если он доступен.

Режимы работы: `implementation`, `review`, `task-finish`, `architecture-update`. Порядок приоритета правил — в `ai/architecture.md`, раздел «Skill precedence».
