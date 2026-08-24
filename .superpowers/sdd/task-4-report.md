# Task 4 report — preserve the registry in installers and updaters

## Что сделано

- Добавил проверку, что свежая установка хаба создаёт `ai/archiprojects.md`.
- Добавил проверку, что updater:
  - не трогает уже существующий `ai/archiprojects.md` с `USER_ARCHIPROJECT_MUST_SURVIVE`;
  - восстанавливает `ai/archiprojects.md`, если файла нет.
- Обновил только логику копирования отсутствующих файлов в `scripts/update-installed-hub.sh`.

## Изменённые файлы

- `scripts/hub-smoke-test.sh`
- `scripts/update-installed-hub.sh`

## Проверка

- `bash scripts/hub-smoke-test.sh` — passed.

## Итог

Registry-файл теперь создаётся при установке и может быть восстановлен updater'ом только если его нет. Уже существующий файл не перезаписывается.
