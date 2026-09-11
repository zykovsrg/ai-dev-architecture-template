# Обновление подключённых проектов

Shared architecture больше не обновляется отдельно внутри каждого проекта. Общие rules, skills и workflows обновляются один раз в Personal AI Hub.

Проектные репозитории сохраняют только свою память, код, конфигурацию и optional knowledge. Hub update не должен перезаписывать существующие project memory files.

## Обновите Hub

Используйте локальную копию source repository и сначала получите preview:

```bash
bash scripts/update-installed-hub.sh --hub /path/to/_ai-hub --source /path/to/ai-dev-architecture-template --dry-run
```

Применяйте только тот план, который был показан и подтверждён. Content-addressed update path должен использовать одну и ту же source revision для preview и apply.

## Старые проекты

Если в проекте сохранились общие rule/skill copies от прежней схемы, не обновляйте и не восстанавливайте их. Используйте `hub-project-migrate`: он должен сохранить каноническую project memory и optional knowledge, а удаление устаревших общих файлов показывать отдельным diff до подтверждения.
