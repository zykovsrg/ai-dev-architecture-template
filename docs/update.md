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

## Transactional safety

Apply выполняется как транзакция:

- новые managed files сначала staging'ятся;
- заменяемые и удаляемые targets имеют rollback backup;
- замена выполняется атомарно;
- `installed.json` обновляется внутри той же rollback boundary;
- при ошибке уже выполненные изменения откатываются;
- локально изменённый retired managed file не удаляется молча, а превращается в conflict.

Это не отменяет preview: transactional rollback защищает от сбоя apply, но не заменяет проверку самого плана.

## После обновления

Сначала проверьте версию установленного Hub:

```bash
grep '^Version:' /path/to/_ai-hub/ai/architecture.md
```

Затем проверьте registry и project boundaries:

```bash
bash /path/to/_ai-hub/scripts/check-hub-registry.sh /path/to/_ai-hub
```

Если source repository доступен локально, из него можно дополнительно запустить architecture-focused проверки репозитория:

```bash
bash scripts/check-consistency.sh
bash scripts/hub-smoke-test.sh
bash scripts/architecture-test.sh
bash scripts/assistant-workflows-test.sh
python3 -m unittest discover -s tests -v
```

Calendar policy имеет отдельный suite:

```bash
(
  cd calendar-policy
  python3 -m pytest -q
)
```

Repo-only tests запускайте из source repository, а не из установленного Hub, если соответствующих test files там нет.

## Если проект всё ещё содержит старые общие rules/skills

Используйте `hub-project-migrate`. Не восстанавливайте retired project-local architecture через старый updater.

## Чего не делать

Не используйте для обычного Hub update:

- retired `scripts/update-installed-architecture.sh` как updater;
- удалённый `template/`;
- `--mode standalone`;
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
