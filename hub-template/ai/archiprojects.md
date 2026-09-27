# Archiprojects

This is the canonical hub-owned archiproject group registry, not a parallel
task store. Project/task files remain canonical for project work. Goals live
in `ai/goals.md`, not here.

## Schema

Use one human heading and one fenced YAML block for each group. A group
organizes projects and has no fake metrics. `parent:` is optional; when
present it must name another group in this file.

## <archiproject-id>

```yaml
id: <archiproject-id>
name: <human name>
status: <status>
kind: group
parent: <parent-archiproject-id>
```
