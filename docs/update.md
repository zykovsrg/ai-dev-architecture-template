# Обновление Personal AI Hub

Обновляется только Personal AI Hub. Проекты не получают отдельные копии shared architecture.

## Безопасный порядок

1. Получите локальную source-копию нужной revision репозитория.
2. Сформируйте preview для установленного Hub.
3. Проверьте conflicts и точный plan hash.
4. Примените только этот подтверждённый план из той же source revision.
5. Повторно запустите Hub consistency/smoke checks.

Для локальной source-копии:

```bash
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/ai-dev-architecture-template --dry-run
```

Updater не должен молча перезаписывать изменённые managed files, существующую пользовательскую memory или повторно разрешать другую remote revision между preview и apply.

Если проект всё ещё содержит старые общие rules/skills, используйте `hub-project-migrate`; не восстанавливайте их через legacy updater.
