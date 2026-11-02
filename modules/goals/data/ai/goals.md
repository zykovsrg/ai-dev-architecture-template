# Цели

Канонический реестр числовых целей Хаба. Каждая цель ссылается на группу
`ai/archiprojects.md` через `group`; `ai/archiprojects.md` никогда не ссылается
на цели. `ai/goal-log.md` записывает продвижение по `id` цели отсюда.

## Schema

Используйте один читаемый заголовок и один блок YAML для каждой цели.
`group` должен назвать известную группу `ai/archiprojects.md`.

## <goal-id>

```yaml
id: <goal-id>
name: <human name>
status: <status>
group: <archiproject-group-id>
target: <target>
unit: <unit>
due: YYYY-MM-DD or none
```
