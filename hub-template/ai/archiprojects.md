# Archiprojects

This is the canonical hub-owned archiproject registry, not a parallel task
store. Project/task files remain canonical for project work.

## Schema

Use one human heading and one fenced YAML block for each concrete entry. A
`group` organizes projects and has no fake metrics; a `goal` tracks a numeric
target.

## <archiproject-id>

```yaml
id: <archiproject-id>
name: <human name>
status: <status>
kind: group
```

## <archiproject-id>

```yaml
id: <archiproject-id>
name: <human name>
status: <status>
kind: goal
target: <target>
unit: <unit>
due: YYYY-MM-DD or none
```
