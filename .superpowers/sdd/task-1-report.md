# Task 1 report — stable task IDs and manifest v3

## Изменения

- `scripts/generate-obsidian-projects-kanban.sh`
  - Future records возвращают ID из заголовка `FT-YYYYMMDD-NNN`.
  - Рендеримые current и paused records требуют ровно один непустой `Task ID:`.
  - Карточки используют Obsidian block ID: `- [ ] Title ^TASK-ID`.
  - Дублирующиеся ID рендеримых задач блокируют генерацию.
  - Manifest обновлён до v3 и содержит `tasks` с `task_id`, `project_id`, `source_file`, `source_sha256`.
  - Запись поверх manifest v2 отклоняется с сообщением о fresh confirmed rebuild.
- `scripts/obsidian-projects-kanban-test.sh`
  - Добавлены stable-ID fixtures и проверки block ID / manifest v3.
  - Добавлены проверки отказа для manifest v2 и paused task без ID.

## TDD evidence

1. RED: после добавления контрактной проверки выполнено:

   ```text
   bash scripts/obsidian-projects-kanban-test.sh
   FAIL: expected '<!-- ai-task-id: TASK-20260826-001 -->' in .../preview.txt
   ```

2. Во время self-review добавлен тест отказа paused task без ID. До исправления propagation статуса выполнено:

   ```text
   bash scripts/obsidian-projects-kanban-test.sh
   FAIL: paused task without ID did not block preview
   ```

3. GREEN / финальная проверка:

   ```text
   bash -n scripts/generate-obsidian-projects-kanban.sh scripts/obsidian-projects-kanban-test.sh
   bash scripts/obsidian-projects-kanban-test.sh
   PASS: Obsidian task Kanban and project overview contract
   git diff --check
   ```

## Совместимость Obsidian

По проверенной корректировке дизайна от ведущего использован block ID (`^TASK-ID`) вместо HTML-комментария. Установленный `obsidian-kanban` v2.0.51 удаляет HTML-комментарии при move/edit, а block ID сохраняет связанный с карточкой устойчивый идентификатор.

## Commit

`45eb730 feat: add stable IDs to generated task cards`

## Concerns

- Для обновления существующей v2 проекции пользователь должен выполнить fresh confirmed rebuild: генератор намеренно не перезаписывает v2 manifest.

## Fix

- RED: после добавления проверок фактического количества задач и прямого `source_sha256` выполнено `bash scripts/obsidian-projects-kanban-test.sh`; тест остановился на `FAIL: manifest source hash is not the source file hash`.
- GREEN: генератор теперь принимает для current/paused только `TASK-YYYYMMDD-NNN`, отклоняет пустые/некорректные/дублирующиеся ID и записывает SHA-256 содержимого исходного файла. `bash scripts/obsidian-projects-kanban-test.sh` завершился `PASS: Obsidian task Kanban and project overview contract`.
- Дополнительно проверено: `bash -n scripts/generate-obsidian-projects-kanban.sh scripts/obsidian-projects-kanban-test.sh` и `git diff --check` завершились успешно.

## Вторая волна ревью

- RED: после добавления fixture с внешними пробелами вокруг current/paused `Task ID:` выполнено `bash scripts/obsidian-projects-kanban-test.sh`; генератор отклонил корректный ID с ошибкой `invalid Task ID`.
- GREEN: current и paused ID теперь обрезают внешние пробелы перед строгой проверкой и рендерятся как чистые `TASK-YYYYMMDD-NNN`. Добавлены проверки прямых `source_sha256` для future и paused, дублей future/paused ID, а также строгого future heading: принимается только `FT-[0-9]{8}-[0-9]+` (включая однозначный суффикс), заголовок с буквами игнорируется.
- Финальная проверка:

  ```text
  bash scripts/obsidian-projects-kanban-test.sh
  PASS: Obsidian task Kanban and project overview contract
  bash -n scripts/generate-obsidian-projects-kanban.sh scripts/obsidian-projects-kanban-test.sh
  git diff --check
  ```
