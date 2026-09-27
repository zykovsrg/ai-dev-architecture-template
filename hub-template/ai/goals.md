# Goals

Canonical hub-owned numeric goal registry. Each goal references a group in
`ai/archiprojects.md` via `group`; `ai/archiprojects.md` never references
goals. `ai/goal-log.md` records progress against a goal's `id` here.

## Schema

Use one human heading and one fenced YAML block for each goal. `group` must
name a known group in `ai/archiprojects.md`.

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
