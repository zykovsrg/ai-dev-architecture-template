# Обновление Personal AI Hub

Обновляется только Personal AI Hub. Проекты не получают отдельные копии shared architecture.

## Безопасный порядок

1. Выберите одну source revision.
2. Сформируйте preview и сохраните `Plan SHA256`.
3. Проверьте conflicts и список create/replace/remove.
4. Примените только тот же plan hash из той же revision.
5. Повторно запустите Hub consistency/smoke checks.

### Локальная pinned source revision

```bash
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/pinned-repository --dry-run
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/pinned-repository --apply --confirm-plan <PLAN_SHA256>
```

### Remote branch/tag

Preview разрешает branch/tag один раз и печатает точный `Resolved revision: <COMMIT_SHA>`:

```bash
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --ref main --dry-run
```

Для apply используйте уже показанный commit SHA, а не символическое имя ветки:

```bash
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --ref <COMMIT_SHA> --apply --confirm-plan <PLAN_SHA256>
```

Так apply использует те же source bytes. Если plan hash не совпадает, update прекращается и требует новый preview.

Updater не должен молча перезаписывать изменённые managed files, существующую пользовательскую memory или другую remote revision. При ошибке во время apply уже заменённые файлы откатываются из operation backup.

Не используйте `curl ... | bash`: это не поддерживаемый release/update path.

Если проект всё ещё содержит старые общие rules/skills, используйте `hub-project-migrate`; не восстанавливайте их через retired updater.
