# Current System Inventory

## Scope and safety

This is a read-only inventory for the unified AI-assistant design. It covers:

- the AI Development Architecture project context and registered project map;
- the copied Obsidian vault at `tmp/obsidian-vault-copy/Obsidian`;
- the approved design in `docs/superpowers/specs/2026-08-23-unified-ai-assistant-obsidian-design.md`.

The copied vault was treated as read-only. The inventory uses file paths,
extensions, directory counts, plugin IDs, and aggregate syntax counts. It does
not reproduce note bodies, raw frontmatter values, configuration values, or
personal, secret, or client-confidential content. No move, deletion, migration,
or write to the vault was performed.

Repository state at inspection time contained pre-existing changes to
`ai/current-task.md` and `ai/future-tasks.md`; they are outside this task and
were not modified.

## Verified AI architecture facts

- The project is a reusable AI Development Architecture based on Markdown,
  Bash, and Git/GitHub. It contains template files, documentation, skills,
  working-memory files, and install/update scripts.
- The architecture defines the AI architecture as the source of truth for
  projects and tasks. Obsidian is intended to be the human interface, Kanban
  view, and knowledge workspace; it must not become a second independent task
  database.
- The approved design uses the hierarchy `Archiproject -> Projects -> Tasks ->
  Subtasks`. A project has one primary archiproject and may have secondary
  links without double-counting progress.
- The approved knowledge model is `Knowledge base -> Areas, Resources /
  Meetings, Inbox, Archives`, with selected PARA and lightweight Zettelkasten
  practices.
- Cross-project search is designed to begin with compact indexes. Full reads
  require naming and confirming the selected scope.
- Every proposed write, destination, deadline, move, and calendar change needs
  user confirmation. Existing files must be inventoried before any move, and
  migration must be reversible.
- The current project context defines `ai/current-task.md` as one current task,
  `ai/future-tasks.md` as a backlog of ideas, and `ai/paused-tasks.md` as a
  holding area for unfinished paused work. These are architecture records, not
  facts about the Obsidian vault.

## Verified Obsidian facts

### File and folder inventory

- The copied vault contains 716 Markdown files in total. A scan excluding
  `.trash` finds 715 Markdown files; one additional Markdown file is in
  `.trash`.
- The main notes folder is `1. База знаний/2. Заметки` and contains 457
  Markdown files.
- The archive folder is `1. База знаний/4. Архив` and contains 95 Markdown
  files.
- Other visible Markdown-bearing areas include the vault root, links and
  summaries under `1. База знаний`, and Kanban folders under `3. Канбан`.
- The vault also contains non-Markdown material: 128 JPG, 77 JSON, 58 JPEG,
  38 PNG, 26 DS_Store, 18 PDF, 18 Canvas, 3 JS, 3 DOCX, 3 CSS, 2 WEBP, and 1
  MP4 file by extension. Extension counts are inventory facts only; their
  contents were not included in this report.
- Obsidian configuration metadata includes standard application, appearance,
  workspace, graph, daily-notes, templates, core-plugin, and community-plugin
  files. Several sync-conflict workspace/configuration filenames are present.

### Aggregate link and task syntax counts

- The copied vault contains 632 wiki-link syntax occurrences matching `[[...]]`.
  This is a count of syntax occurrences, not a count of unique targets or
  verified working links.
- It contains 3,792 Markdown checkbox syntax occurrences. These are syntax
  occurrences, not a count of active tasks, and no task status was inferred
  from them.

## Existing project and task model

### Verified structure

- The AI architecture has an explicit project/task model in its rules and
  working memory, with one current task and separate paused/future work.
- The copied vault has a distinct Kanban area at `3. Канбан`. Its observed
  Markdown distribution includes 80 files in two dated Kanban subfolders, 1
  file in another named Kanban subfolder, and 3 files directly in the Kanban
  root. The subfolder names are intentionally redacted because they identify
  projects or clients.
- The vault has many checkbox lines spread across Markdown files, but the
  inventory did not treat every checkbox as a task record.

### Not yet verified

- A one-to-one mapping between Kanban cards and architecture projects was not
  established.
- Ownership, stable IDs, status vocabulary, deadlines, blockers, waiting
  dates, and parent-child task links were not inferred from note contents.
- It is not yet verified whether Kanban cards are generated views, manually
  maintained notes, or a mixture of both.

## Existing knowledge model

### Verified structure

- The main knowledge area is grouped into `1. База знаний/2. Заметки`,
  `1. База знаний/1. Связки`, `1. База знаний/3. Итоги`, and
  `1. База знаний/4. Архив`.
- The observed summaries area has dated subfolders from 2024 through 2025.
- The vault root and knowledge area both contain Markdown files, so the
  current storage layout is not a single flat note directory.
- Wiki links are used in the vault, with 632 observed syntax occurrences.

### Not yet verified

- The existing folders do not by themselves prove a canonical PARA class,
  Zettelkasten ID, source field, project relation, or retention rule for each
  note.
- Duplicate notes, orphan links, stale links, and notes that belong to several
  projects require a separate content-aware review with an approved scope.

## Existing plugins and views

- The installed community plugin IDs are exactly:
  `calendar`, `obsidian-hider`, and `obsidian-kanban`.
- The presence of `obsidian-kanban` and the `3. Канбан` folder verifies that
  Kanban is part of the current surface area. It does not prove how many boards
  are active or how cards are rendered.
- The presence of `calendar` verifies an installed calendar plugin. It does not
  prove a connection to Apple Calendar or any external calendar write path.
- The presence of `obsidian-hider` verifies an installed display/layout plugin.
  Its active rules and hidden areas were not inferred.
- Workspace and plugin configuration files exist, including historical
  sync-conflict variants. Their raw values were intentionally not copied into
  this report.

## Data quality risks

- The total Markdown count and the non-`.trash` count differ by one because a
  Markdown file is present in `.trash`. Any migration count must define whether
  `.trash` is in scope.
- The 95 archived files are in a named archive folder, while `.trash` is a
  separate disposal area. These states must not be merged automatically.
- Checkbox syntax is over-inclusive for task discovery: 3,792 lines may include
  checklists, templates, historical records, or completed work.
- Wiki-link syntax is over-inclusive for knowledge graph claims: 632
  occurrences may repeat targets or point to missing/ambiguous notes.
- Multiple sync-conflict configuration files create a risk of reading stale or
  divergent workspace state.
- Mixed formats and media require a separate policy for indexing, previews,
  ownership, and retention. File extensions alone do not establish semantic
  roles.
- The current folder names mix broad knowledge areas, dated summaries, Kanban
  boards, and project-like names. Folder structure alone is not a safe source
  of project or task truth.
- No migration should assume that a note is safe to expose across projects just
  because it links to one of them.

## Hypotheses requiring validation

The following are hypotheses, not verified facts:

- The Kanban area may be a human-facing projection of project state, but its
  cards may currently contain independent task data.
- The main notes folder may contain the largest share of durable knowledge, but
  its 457 files may include captures, project material, historical notes, and
  duplicates.
- Dated summaries may be useful inputs for daily and weekly review, but their
  fields and completeness are unknown.
- The installed calendar plugin may support local planning views, but it is not
  evidence of Apple Calendar integration.
- The existing wiki-link graph may support compact indexes, but link health and
  access boundaries must be measured before relying on it for routing.
- Some checkbox lines may represent actionable tasks, but task extraction needs
  explicit rules and review rather than a count-based migration.
- The architecture's current project/task records and Obsidian's Kanban records
  may overlap. A field-level comparison is required before designing a
  projection or migration.

## Constraints carried into design

- Keep the AI architecture as the single source of truth for projects and
  tasks; Obsidian task displays must be views or projections, not a second
  canonical task store.
- Preserve the distinction between archiprojects, projects, tasks, and
  subtasks; do not count secondary links as additional progress.
- Preserve the distinction between active knowledge, dated summaries,
  archives, and `.trash` until each state has an approved migration rule.
- Treat the 3,792 checkbox count as syntax evidence only. Require validation
  before converting any line into a task.
- Treat the 632 wiki-link count as syntax evidence only. Validate targets,
  duplicates, orphans, and cross-project access before using links for search or
  routing.
- Keep the installed plugin set as a compatibility constraint; any new plugin
  or integration needs a separate decision and permission review.
- Do not read or move full note bodies during discovery. Full reads require an
  explicitly named scope and confirmation.
- Require approval before every write, destination change, deadline change,
  move, deletion, or calendar change, with a rollback path.
- Keep shared multi-project knowledge canonical in one place and give projects
  references plus their own tasks, without duplicating the shared note.
- Validate the current audit runbook on a small approved sample before treating
  it as an established procedure.
