# Обновление Personal AI Hub

Обновляется только Personal AI Hub. Проекты не получают отдельные копии shared architecture, а их локальная память, knowledge и project-specific данные не должны перезаписываться этим процессом.

Канонический updater — `scripts/update-installed-hub.sh`. Он использует `scripts/hub_release.py` как единый preview/apply engine.

## Безопасный порядок

1. Выберите одну source revision.
2. Сформируйте preview и сохраните `Plan SHA256`.
3. Проверьте conflicts и список create/replace/remove.
4. Примените только тот же plan hash из той же source revision.
5. После apply повторно проверьте Hub.

Preview обязателен. Не переходите сразу к `--apply`.

## Перед обновлением

Убедитесь, что:

- известен путь к установленному Hub;
- в Hub есть `AGENTS.md` и `ai/architecture.md`;
- source repository доступен локально или через GitHub;
- если Hub сам является Git-репозиторием, незакоммиченные изменения просмотрены заранее.

Если updater сообщает, что Hub working tree dirty, нормальный путь — сначала commit/stash/review. `--allow-dirty` используйте только как осознанный override, а не как стандартный способ обновления.

## Рекомендуемый вариант: локальная pinned source revision

Это самый простой и предсказуемый путь.

Сначала перейдите в локальный clone source repository и зафиксируйте нужную revision. Если требуется обновить clone, делайте это безопасно, не уничтожая локальные изменения.

Preview:

```bash
bash scripts/update-installed-hub.sh \
  --hub /path/to/_ai-hub \
  --source /path/to/pinned-repository \
  --dry-run
```

Проверьте вывод и сохраните `Plan SHA256`.

Если conflicts нет и план ожидаемый, примените именно его:

```bash
bash scripts/update-installed-hub.sh \
  --hub /path/to/_ai-hub \
  --source /path/to/pinned-repository \
  --apply \
  --confirm-plan <PLAN_SHA256>
```

Если source bytes или план изменились между preview и apply, подтверждение не должно совпасть, и update должен быть остановлен.

## Remote branch/tag

Если локального clone нет, можно сделать preview напрямую из remote ref.

```bash
bash scripts/update-installed-hub.sh \
  --hub /path/to/_ai-hub \
  --ref main \
  --dry-run
```

Preview один раз разрешает branch/tag в immutable commit и печатает, в частности:

```text
Resolved revision: <COMMIT_SHA>
Plan SHA256: <PLAN_SHA256>
Source SHA: <COMMIT_SHA>
```

Для apply используйте именно подтверждённый commit SHA из preview:

```bash
bash scripts/update-installed-hub.sh \
  --hub /path/to/_ai-hub \
  --ref <COMMIT_SHA> \
  --apply \
  --confirm-source-sha <COMMIT_SHA> \
  --confirm-plan <PLAN_SHA256>
```

`--confirm-source-sha` обязателен для remote `--apply`. Mutable branch вроде `main` не должен молча разрешаться заново в другой commit после preview. Если source SHA или plan hash не совпадают с подтверждёнными значениями, updater должен отказаться продолжать.

## Что означает preview

В preview используются операции release engine:

- `keep` — managed file уже соответствует выбранному release;
- `create` — managed file будет создан;
- `replace` — managed file будет заменён новой версией;
- `remove` — ранее managed file больше не входит в release и будет удалён безопасно;
- `conflict` — локальное состояние не позволяет автоматически выполнить операцию без риска.

Перед apply особенно внимательно проверяйте `replace`, `remove` и `conflict`.

Если есть conflict, не используйте force overwrite. Сначала определите, что это за файл: пользовательская кастомизация, намеренное локальное изменение или устаревшая managed copy. Сохраните нужное состояние и выполните новый preview.

Другие флаги:

- `--check` — только сравнить: код выхода 0, если Hub совпадает с выбранным release; 1 и план, если есть отличия;
- `--commit` — после apply сделать commit в Git самого Hub;
- `--allow-dirty` — разрешить apply при незакоммиченных изменениях Hub (см. выше).

## Модули

Модули `core`, `projects`, `tasks` стоят всегда. Остальные можно выключить и включить обратно. Выключить модуль — значит убрать его файлы из Hub обычным обновлением; данные пользователя при этом не удаляются.

| Модуль | Что убирается | Что остаётся | Что перестаёт работать |
| --- | --- | --- | --- |
| knowledge | `ai/rules/knowledge.md`; навыки `hub-knowledge-enable`, `hub-knowledge-capture`, `hub-knowledge-review`, `hub-info-update` | папки `knowledge/` в проектах | включение и ведение `knowledge/`; заготовка `knowledge/` у новых проектов; предложение проверить knowledge при закрытии задачи; предложения по заметкам встречи для одного проекта |
| goals | `ai/rules/goals.md`; навык `hub-goal-progress`; `scripts/count-goal-progress.sh` | `ai/goals.md`, `ai/goal-log.md` | подсчёт и запись прогресса целей; цифры целей в планах и обзорах |
| learning | `ai/rules/learning.md`; навык `hub-session-review`; `scripts/workflow_friction.py`, `scripts/check-session-review.py`, `scripts/check-workflow-memory.sh` | `ai/workflow-observations.md`; разборы в `ai/session-reviews/` проектов | разбор сессии при закрытии задачи; журнал трудностей в вечернем и недельном обзоре |
| calendar | `ai/rules/calendar.md`; навык `hub-calendar`; после apply — `tools/apple-calendar-policy` и запись `hub_calendar` в `.mcp.json` | `.local/apple-calendar/allowlist.json`; снимки `ai/tmp/calendar-snapshots/`; другие записи `.mcp.json` | чтение и изменение календаря. Выключается только вместе с `planning` |
| planning | `ai/rules/planning.md`; навык `hub-workflows`; `scripts/snapshot-calendar.sh`, `scripts/calendar-context.py`, `scripts/calendar_task_sync.py`, `scripts/validate-day-plan-output.py` | `ai/workflow-context.md` | план дня, вечерний и недельный обзор; общее подтверждение «задача + событие календаря» при записи задачи с датой |
| obsidian | `ai/rules/obsidian.md`; `scripts/obsidian-task-sync.sh`, `scripts/generate-obsidian-projects-kanban.sh` | vault `projects/ai-dev-architecture/obsidian-vault` | доски перестают обновляться; правки на досках больше не превращаются в предложения |

Выключение модуля ничего не удаляет в `projects/` и `.local/`. Если файл модуля изменён вручную, preview покажет `conflict`, и apply не выполнится. Файл `ai/modules.md` пересобирается: выключенный модуль и его подписки на события из него пропадают.

Зависимости:

- `planning` требует `calendar`. `--without calendar` без `--without planning` отклоняется с ошибкой `module planning requires calendar`.
- `planning` использует `goals` и `learning`, только если они стоят. Их можно выключить и при включённом `planning`.
- Включить модуль, которому нужен выключенный модуль, тоже нельзя: `--with planning` без `calendar` отклоняется.
- `core`, `projects`, `tasks` переключить нельзя: `module cannot be switched`.

Команды — обычный preview и apply с флагами `--without <id>` или `--with <id>` (флаги можно повторять):

```bash
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/pinned-repository --dry-run --without obsidian
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/pinned-repository --dry-run --without planning --without calendar
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/pinned-repository --dry-run --with obsidian
```

Preview покажет строку `Modules:`, строку `Module change:` (например `-obsidian` или `+obsidian`) и файлы модуля в `remove`/`create`. Apply — с теми же флагами и тем же `--confirm-plan`. Выбор модулей запоминается: следующее обновление без флагов сохранит текущий набор.

Сервер календаря. Preview всегда печатает строку `Extra step:`: `refresh calendar server (...)`, если `calendar` выбран, и `remove calendar server (...)`, если нет. После успешного apply updater вызывает `modules/calendar/scripts/sync-calendar-policy.sh`. Если `calendar` выбран, шаг обновляет `tools/apple-calendar-policy`, пересобирает мост на macOS и добавляет запись `hub_calendar` в `.mcp.json`, только если её там нет; существующую запись он не перезаписывает. Если не выбран, шаг удаляет `tools/apple-calendar-policy` и только запись `hub_calendar` из `.mcp.json`.

## Что updater сохраняет

Hub update не является миграцией проектов и не должен изменять проектные репозитории.

В частности, процесс не должен удалять или перезаписывать пользовательскую project memory и knowledge, включая:

- `ai/current-task.md`;
- `ai/paused-tasks.md`;
- `ai/future-tasks.md`;
- `ai/project-context.md`;
- `ai/decisions.md`;
- `ai/changelog.md`;
- `ai/session-reviews/`;
- project-local `knowledge/`;
- реальные project-specific extensions.

Hub-side memory с create-if-missing semantics также сохраняется: существующий пользовательский файл не заменяется только потому, что source release содержит шаблон для его первоначального создания.

Пользовательские файлы Hub, не входящие в managed manifest, не должны затрагиваться release engine.

## Rollback safety

Apply staging'ит новые managed files, сохраняет backup заменяемых и удаляемых targets и обновляет `installed.json` внутри той же операции. Если во время apply возникает обработанная runtime-ошибка, release engine откатывает уже выполненные изменения из этих backup'ов.

Эта гарантия не распространяется на жёсткое завершение процесса, аварийное завершение ОС или потерю питания: в таких случаях код rollback может не выполниться. После такого прерывания не запускайте apply вслепую повторно. Сначала снова выполните preview для той же source revision и проверьте текущее состояние, особенно conflicts и `installed.json`. Если состояние оказалось частично обновлённым, сначала восстановите или согласуйте затронутые managed files, затем сформируйте новый preview и только после этого выполняйте apply.

Дополнительно:

- замена отдельного файла выполняется атомарно через `os.replace`;
- `installed.json` также заменяется атомарно после staging;
- локально изменённый retired managed file не удаляется молча, а превращается в conflict.

Rollback защищает от обработанных ошибок внутри apply, но не заменяет preview и не является журналируемым crash-recovery механизмом.

## После обновления

Сначала проверьте версию установленного Hub:

```bash
grep '^Version:' /path/to/_ai-hub/ai/architecture.md
```

Затем проверьте registry и project boundaries:

```bash
bash /path/to/_ai-hub/scripts/check-hub-registry.sh /path/to/_ai-hub
```

Проверки самого репозитория (как в CI) описаны в [README](../README.md#проверки-репозитория). Запускайте их из source repository, а не из установленного Hub.

## Если проект всё ещё содержит старые общие rules/skills

Используйте `hub-project-migrate`. Не восстанавливайте retired project-local architecture через устаревший механизм обновления.

## Чего не делать

Для обычного Hub update не используйте:

- устаревший updater старой project-local архитектуры;
- удалённое дерево распространения старой project-local архитектуры;
- устаревший режим установки старой project-local архитектуры;
- `curl ... | bash`;
- force overwrite локальных conflicts;
- `git reset --hard` ради обновления;
- новый apply без нового preview, если source или plan изменились;
- ручное удаление project memory.

## Короткая инструкция для AI-агента

Этот блок можно скопировать агенту:

```text
Обнови установленный Personal AI Hub по инструкции из docs/update.md.
Рабочий Hub: <HUB_PATH>.
Сначала выполни только preview и покажи create/replace/remove/conflicts, Plan SHA256 и Source SHA, если update remote.
Не применяй изменения при conflict.
После безопасного preview примени ровно подтверждённый plan из той же source revision.
Не меняй project memory, knowledge или project-specific data.
После apply проверь Hub version, registry и доступные architecture-focused checks.
Если source или plan изменились после preview, остановись и сделай новый preview.
```
