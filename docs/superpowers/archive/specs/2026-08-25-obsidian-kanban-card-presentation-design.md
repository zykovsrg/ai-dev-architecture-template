# Obsidian Kanban Card Presentation — Design

## Goal

Make the generated project board concise and usable in the existing
`obsidian-kanban` plugin without creating a second task database.

## Card format

Each project remains one Kanban card:

```markdown
- [ ] Project name
  - [ ] Derived next action
  - [ ] Derived next action
  - 📅 2026-08-26
```

- The project checkbox is required by the Kanban card format. Checking it is a
  proposal only; it never updates architecture records automatically.
- Only safely derived, real next actions are rendered as checkboxes.
- When a project has no safe next action, no action row is rendered.
- The date is rendered only from an explicit canonical architecture due date,
  using `📅 YYYY-MM-DD`. There is no guessed date and no manual Obsidian date
  synchronization.
- `id`, `purpose`, `status`, and placeholder text such as `нет следующего
  действия` are not shown in the card body.

## Board format and safety

- Keep only frontmatter and the seven real Kanban columns. Remove the Markdown
  title and explanatory paragraph that the plugin treated as an empty column.
- Keep the existing source scope, classification, manifest, path guards, and
  manual-edit detection unchanged.
- Any manual checkbox, title, action, or date edit changes the board hash.
  The next confirmed rebuild stops with `proposal pending`; no architecture
  file, task, deadline, or Calendar entry changes automatically.

## Verification

- Test no empty title column is rendered.
- Test real actions render as nested unchecked checkboxes.
- Test no placeholder or technical fields are rendered.
- Test an explicit fixture due date renders as `📅 YYYY-MM-DD`.
- Retain tests for 35-card preview, valid manifest, and manual-edit blocking.

## Write boundary

Implementation may update generator and tests on the isolated branch. A later
preview and fresh explicit confirmation are required before replacing only
`Projects-Kanban.md` and `Projects-Kanban.manifest.json` in the copied vault.
