# Archiprojects

This is the canonical hub-owned archiproject group registry, not a parallel
task store. Project/task files remain canonical for project work.

## Schema

Use one human heading and one fenced YAML block for each group. A group
organizes projects and has no fake metrics. `parent:` is optional; when
present it must name another group in this file.

A group may set `calendar_name: <short lowercase Cyrillic name>` for calendar
event titles; without it the lowercased `name:` is used. Event titles show the
whole chain: `<group names from the root>/<project Calendar name>/<task>`.

A group may set `stage_template: <hub-relative path>`. When a project of that
group (or of a descendant group) is created, `scripts/seed_stage_template.py`
adds the template's stages to the project's `ai/future-tasks.md`.

## <archiproject-id>

```yaml
id: <archiproject-id>
name: <human name>
status: <status>
kind: group
parent: <parent-archiproject-id>
```
