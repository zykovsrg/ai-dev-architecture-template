# Current Task

Status: active

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: intake

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

architecture-update

## Goal

Устранить шесть находок аудита архитектуры Personal AI Hub от 2026-08-15.
Четыре правки в скриптах: разворачивать `--source` в абсолютный путь до `cd` и
запрещать источник, совпадающий с целью; обратная сверка «папка → реестр» в
`check-hub-registry.sh` как предупреждение с кодом выхода 0; честный текст
`--check`, говорящий, что сравнивались номера версий, а не файлы; гарантия
строки `/projects/` в `.gitignore` хаба без перезаписи файла. Две правки в
protected-файлах: назвать `hub-project-router`, `hub-registry-check` и
`hub-local-router-install` в `hub-template/ai/architecture.md` и закрыть
регрессию новой проверкой в `check-consistency.sh`; заменить «each allowed
root» на единственный корень в `hub-registry-check/SKILL.md`.

Правки вносятся в репозиторий-источник, затем отдельно подтверждённым шагом
доставляются в живой хаб через `update-installed-hub.sh --apply`.

## Use Superpowers

yes

## Relevant files

- `scripts/update-installed-hub.sh`
- `scripts/update-installed-architecture.sh`
- `scripts/check-hub-registry.sh`
- `scripts/check-consistency.sh`
- `hub-template/ai/architecture.md`
- `hub-template/ai/skills/hub-registry-check/SKILL.md`

## Done criteria

- Относительный `--source` разворачивается до `cd`; источник, совпадающий с целью, отвергается с ошибкой.
- Незарегистрированная папка в `projects/` даёт предупреждение в stderr и не меняет код выхода 0.
- Вывод `--check` и `--help` не допускают чтения «файлы совпадают».
- `.gitignore` хаба получает недостающую строку `/projects/` без перезаписи существующего содержимого.
- Три скилла названы в `hub-template/ai/architecture.md`; новая проверка ловит скилл, не упомянутый ни в одном слое правил.
- В `hub-registry-check/SKILL.md` нет формулировки про несколько разрешённых корней.
- Каждая новая проверка подтверждена мутационным тестом с восстановлением и чистым `git status`.
- `check-consistency.sh`, `hub-smoke-test.sh`, `smoke-test.sh`, `check-hub-registry.sh` проходят.
- Изменения protected-файлов внесены только после показа точных формулировок и подтверждения пользователя.
- Живой хаб обновлён отдельно подтверждённым `--apply`; `check-hub-registry.sh` на хабе проходит.

## Agent handoff

Last agent: Opus 5, сессия 2026-08-15

What changed: задача записана через task-intake после аудита и утверждённого дизайна.

Open risks: правки затрагивают шлюз, от которого зависят четыре hub-скилла;
находка 5 требует дописывания, а не перезаписи `.gitignore`.

Next agent should check: дизайн утверждён пользователем 2026-08-15 (предупреждение
вместо ошибки для находки 2; имена скиллов плюс защитная проверка для находки 4).
