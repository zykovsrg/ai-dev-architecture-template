# Modular Architecture Design

Task: TASK-ai-dev-architecture-20260926-001
Status: approved in chat 2026-09-26 (sections 1–4); stage 4 details approved 2026-09-27.

## Problem

The Hub works, but its structure is implicit:

- Modules exist only by meaning. Nothing records which modules exist, what each
  owns, or what it may depend on.
- Rules are duplicated. The route-then-confirm rule lives in the Hub entry file,
  twice in `architecture.md` (`Local Router`, `Context-Loading Budget`), and in
  `hub-project-router`.
- `architecture.md` (~32 KB) is loaded as one piece; its `Guarded Apple
  Calendar` section alone is ~126 of ~530 lines and only matters for planning.
- Planning is spread over `architecture.md`, `hub-workflows`, `hub-calendar`,
  `hub-goal-progress`, `scripts/`, `calendar-policy/`, and Obsidian sync. It
  cannot be switched off.
- Mandatory workflows call optional ones directly: `hub-task-intake` runs the
  Obsidian refresh and builds calendar previews itself.
- The calendar MCP (`evening_review.py`) handles evening-review snapshots and
  workflow-friction state, which are not calendar concerns. Snapshots in
  `ai/tmp/calendar-snapshots` have two writers (`snapshot-calendar.sh` and the
  MCP).
- The live Hub and `hub-template/` diverge in 10 skill files in both
  directions, and three planning scripts are installed in the Hub but absent
  from `RUNTIME_SCRIPTS` in `scripts/hub_release.py`. `calendar_task_sync.py`
  exists only in the live Hub; this repository has no source for it.
- Dead weight: `vendor/apple-calendar-mcp` (~11k lines, used only by a checksum
  test), the retired `update-installed-architecture.sh` stub, the legacy Obsidian
  bridge scripts, `project_rule_consolidation.py` (used only by its test), the
  unread `release/hub-files.json`, and doc references to the removed
  `template/` directory. The empty `archiproject_contribution` card field is
  `none` in all 71 cards.

## Goals

Clear module boundaries and ownership; explicit interfaces; explicit allowed
and forbidden dependencies; new features extend existing modules; planning is a
separate module that can be switched off; archiprojects support group-wide work
and nesting; fewer tokens per session; no dead code.

## Decisions

### Modules

| Module | Owns | Required | Depends on |
|---|---|---|---|
| core | entry files, core rules, security, registry validation, project routing | yes | — |
| projects | create/register/migrate/switch, registry check, local router, archiproject groups | yes | core |
| tasks | task format, intake/switch/finish, environment check, task checks, capture of supplied text, cross-project task overview | yes | core, projects |
| knowledge | knowledge enable/capture/review, info update | no | core, projects |
| calendar | guarded Apple Calendar read/preview/apply only | no | core |
| planning | day plan, evening and weekly review, task↔event sync, calendar snapshots | no | core, projects, tasks, calendar (hard) |
| goals | numeric goals and goal log | no | core, projects |
| obsidian | read-only projection of projects and tasks; proposals back | no | core, projects, tasks |
| learning | session review, workflow friction, learning lifecycle | no | core |
| release | install, update, tests (repository-only, never installed) | — | module passports only |

Dependency rules:

- A module may reference only itself, core, and its declared dependencies.
- core, projects, and tasks never reference an optional module.
- calendar knows nothing about tasks, planning, reviews, or learning.
- obsidian never writes canonical task memory; its edits stay proposals.
- A module may declare `uses_if_present` modules. It uses them only when they
  are installed (planning → goals in weekly review; planning → learning for
  friction notes). This replaces the current mandatory learning lifecycle in
  plans and reviews: it applies only when `learning` is installed.
- planning cannot be installed without calendar.

### Interfaces

1. **Module passport** (`module.md` in each module): id, purpose, required,
   `depends`, `uses_if_present`, commands (skills and scripts), reads, writes,
   event subscriptions, and the rules file. Other modules and the installer see
   a module only through its passport.
2. **Single data owner.** Only the owner writes; others read through the
   owner's command.

   | Data | Owner | Read by others via |
   |---|---|---|
   | registry, cards, `ai/archiprojects.md` | projects | compact project index; group index script |
   | project task files | tasks | `task_records.py` (scripts); documented format (agent) |
   | `ai/goals.md`, `ai/goal-log.md` | goals | goal progress script |
   | Apple Calendar | calendar | MCP tools only |
   | calendar snapshots | planning | planning script only |
   | workflow-friction notes | learning | one folder, format in passport |

3. **Events instead of direct calls.** tasks declares two extension points:
   `before-task-confirmation` (planning adds the calendar preview, so the user
   still confirms task and event on one screen) and `after-task-write`
   (obsidian refreshes the board; planning writes the `Событие:` link). The
   installer writes `ai/modules.md` in the Hub: installed modules and their
   subscriptions. Task skills read that short file and call subscribers; a
   missing module means no call.
4. **Rules load per module.** `architecture.md` keeps core rules only. Each
   module's rules live in its folder and are read only by that module's skills.
   The route-then-confirm rule lives only in `hub-project-router`; other places
   keep a one-line pointer.
5. **Boundary check.** A script verifies that each module's files reference only
   allowed modules (paths, skill names, script names). It starts as a warning
   and becomes a failing test once all modules are migrated.

### Archiprojects

- Groups stay in `ai/archiprojects.md` (owner: projects) and gain optional
  `parent:`. Registry validation rejects cycles and missing parents; maximum
  depth is 3.
- A project belongs to exactly one group, the most specific one, via the
  existing card field `primary_archiproject`. A project in a subgroup is also a
  member of every ancestor group.
- Goals move to `ai/goals.md` (owner: goals). A goal references a group; groups
  never reference goals. Card fields `related_archiprojects` and
  `archiproject_contribution` are removed.
- The compact project index gains a sixth field, `group`. A group index script
  prints the group tree with member projects.
- Group-wide work: "что горит по <группе>" (tasks module) and "план дня по
  <группе>" (planning) read task files only for projects in that group and its
  subgroups. Opening a group lists its projects; a project still opens only
  after explicit confirmation.
- One-time data migration, separately confirmed: create group
  `Хадасса → Промо`, move the 16 promo projects into it, move the two goals to
  `ai/goals.md`.

### Layout and switching

- Optional modules live in `modules/<id>/` with passport, rules, skills,
  scripts, tests, and data templates. `calendar-policy/` moves to
  `modules/calendar/`. core, projects, and tasks stay in `hub-template/` until
  last.
- The installer maps module files into the Hub's usual places (`ai/skills`,
  `scripts`, `tools`), so Claude Code and Codex see no difference.
- "Disabled" means not installed: no skills, scripts, or rules in the Hub.
  Disabling runs the normal Hub update without the module; the preview lists
  files to delete and needs confirmation. User data (goal log, snapshots,
  calendar allowlist) is never deleted.
- The release file list is built from passports, replacing the hand-written
  `RUNTIME_SCRIPTS` list.

## Phases

This task:

1. This spec.
2. Step 1 — drift: bring Hub-only code into this repository (including
   `calendar_task_sync.py`, `calendar-context.py`, `validate-day-plan-output.py`)
   and into the release list; decide each of the 10 diverging skill files
   individually; add a drift check between the Hub and `hub-template/`.
3. Step 2 — dead code: remove the items listed under Problem, each only after a
   reference check; fix stale `template/` references; merge plan/spec folders
   into `docs/superpowers`.

Later tasks (recorded in `ai/future-tasks.md`):

4. Passports for all modules, `ai/modules.md`, boundary check in warning mode.
5. planning + calendar into `modules/`; events; installer switch; calendar MCP
   cleanup (snapshots and friction out of the MCP).
6. Archiprojects: nesting, `ai/goals.md`, group index, group-wide work.
7. Split `architecture.md` into core and module rules; remove rule duplicates.
8. Migrate knowledge, goals, obsidian, learning; then core, projects, tasks;
   boundary check becomes strict.

## Testing

- All existing tests stay green after every phase.
- New tests: Hub/template drift; module boundaries; installation without
  planning and calendar (task workflows still work); group tree without cycles
  or orphans.
- The live Hub changes only through the normal preview-and-confirm update.

## Out of scope

Separate repositories per module; moving the Hub to a server; a UI.

## Stage 4 details (TASK-ai-dev-architecture-20260927-001)

Status: approved in chat 2026-09-27. Scope: phase 4 plus the Obsidian part of
phase 5 (Obsidian is the pilot switchable module).

### Passports

- Every module from the table above gets `modules/<id>/module.md`, including
  `release`. The format is Markdown readable by the Python standard library:
  header lines `Id:`, `Required: yes|no`, `Switchable: yes|no`, `Depends:`,
  `Uses if present:`, `Rules:`, `Keywords:`, then sections `## Purpose`,
  `## Installs`, `## Repository only`, `## Reads`, `## Writes`,
  `## Subscribes`. Empty values are written as `—`.
- `## Installs` lists `- <source> -> <hub target>` lines; a source ending in
  `/` includes every file beneath it. Only `obsidian` moves physically in this
  stage (`modules/obsidian/scripts`, `modules/obsidian/tests`,
  `modules/obsidian/rules.md`); other passports list files at their current
  paths. `hub-workflows` belongs to `planning` until phase 5 splits capture out.
  `calendar-policy/` is listed under `## Repository only` of `calendar`
  because `sync-calendar-policy.sh` installs it, not the release manifest.
- The release manifest is built from the `## Installs` lists of the selected
  modules and replaces `RUNTIME_SCRIPTS`. A test fails if any file under
  `hub-template/` or any installed script has zero or more than one owner.
  The create-if-missing policy for memory files and project cards is
  unchanged.
- Only `obsidian` has `Switchable: yes` in this stage.

### Module selection and `ai/modules.md`

- The manifest gains `modules`: the selected module IDs. Because the manifest is
  saved as `.local/hub-release/installed.json`, the selection persists.
- `update-installed-hub.sh` and `hub_release.py preview|apply|drift` accept
  `--without <id>` and `--with <id>`. Without flags the previous selection is
  used; a Hub whose metadata has no `modules` key gets all modules (today's
  behavior). Refused: a required or non-switchable module, an unknown ID, or
  removing a module that a selected module lists in `Depends:`.
- The installer generates `ai/modules.md` (managed, not stored in
  `hub-template/`): installed modules, and for each event its subscribers with
  the command and rules path. With no subscribers an event shows `—`.
- A module's rules install to `ai/rules/<id>.md`. The `Central Obsidian
  Projection` section leaves `ai/architecture.md` for
  `modules/obsidian/rules.md` (vault path, refresh, reverse scan/apply,
  proposal gate); `architecture.md` keeps a one-line pointer and its
  `Version:` is bumped.

### Events

- `after-task-write` only in this stage. `hub-task-intake`, `hub-task-switch`,
  `hub-task-finish`, `hub-info-update`, and
  `hub-calendar/resources/joint-task-change.md` replace their Obsidian blocks
  with one rule: after a confirmed task-file write, read `ai/modules.md`; for
  each `after-task-write` subscriber read its rules file and run its command;
  no subscriber means no call. A subscriber that reports a pending proposal is
  shown to the user and never applied without its own confirmation.
- After this stage no file owned by core, projects, tasks, knowledge, or
  calendar names an Obsidian script, the vault path, or `Obsidian`. A test
  enforces this strictly.

### Boundary check

- `scripts/check-module-boundaries.py` (owner: release) maps each file to its
  module through passports and searches it for other modules' identifiers:
  installed file basenames, skill folder names, rules paths, and `Keywords:`.
  A reference is allowed to self, core, `Depends:`, and `Uses if present:`.
- Output: one `WARN <file>: <module> via <token>` line per violation; exit 0.
  `--strict` exits 1 on any violation. Expected warnings now include
  `hub-info-update` writing task files and calendar files naming tasks (fixed
  in phase 5).
- Per the 2026-08-15 decision, every new check is shown failing on a
  deliberately broken fixture before it counts.

### Disabling Obsidian

- Disabling is the normal update with `--without obsidian`: the preview lists
  the removed scripts and rules and the changed skills and `ai/modules.md`,
  and applies only after plan-hash confirmation. A locally changed file is a
  conflict, as today.
- Never touched: the vault `projects/ai-dev-architecture/obsidian-vault`,
  anything under `/projects/` or `.local/` except release metadata. After
  disabling, boards stay as they are but stop refreshing, and Obsidian edits no
  longer become proposals. No launchd watcher is installed on this Mac
  (verified 2026-09-27), so none is removed. `--with obsidian` restores it.
- The 2026-08-29 decision `Scoped Obsidian reverse proposals` applies only
  while the module is installed; a new decision records this.

### Working Hub

1. The Hub has uncommitted files left from the previous update; ask the user
   before committing them, because the update refuses a dirty Hub.
2. Dry run with `--without obsidian`, show the list, apply after confirmation.
3. `hub_release.py drift` exits 0; task skills read `ai/modules.md` and work
   with no subscribers; `check-all-task-records.sh` passes.

### Tests

New: passport parsing and ownership; manifest with and without `obsidian`;
selection persistence and refusals; `ai/modules.md` content; disable then
re-enable on a fixture Hub with a vault fixture left byte-identical; boundary
check warn and strict modes; strict "no Obsidian outside its module". The moved
Obsidian tests keep running from `architecture-test.sh`. All existing tests and
CI stay green.

### Out of scope for this stage

Moving other modules into `modules/`; `before-task-confirmation`; planning and
calendar switching; archiprojects; splitting the rest of `architecture.md`.

## Stage 5 details (TASK-ai-dev-architecture-20260927-002)

Status: approved in chat 2026-09-27. Scope: phase 5 — planning and calendar
become switchable modules under `modules/`.

### Split of `hub-workflows`

- Capture and the cross-project overview (overdue, blocked, "что горит") belong
  to tasks. They move into a new tasks skill `hub-task-overview`, together with
  the shared personal-assistant contract now in `hub-workflows/SKILL.md`
  (all-project read scope, compact task index, proposal envelope, confirmation
  boundary). `hub-workflows` keeps day plan, evening and weekly review and
  points to that contract instead of repeating it.
- `ai/modules.md` also lists each installed module's skills.
  `hub-project-router` routes capture and overview to `hub-task-overview`, and
  day plan and reviews to the planning skill named in `ai/modules.md`; when
  planning is not installed it says so and offers nothing else.

### Events

- `EVENTS` gains `after-calendar-change`, declared by calendar. A subscription
  value is free text: a shell command or a pointer to a rules section.
- `before-task-confirmation`: before asking to confirm a task write, the task
  skills read `ai/modules.md`; each subscriber may add its items to the same
  confirmation screen; one confirmation approves exactly the shown set; if a
  subscriber cannot build its part, nothing is applied and the user is asked
  again. The "Calendar sync for dated tasks" sections leave the task skills and
  become planning's subscription (rules in `modules/planning/rules.md`,
  installed as `ai/rules/planning.md`), including the `Событие:` link line.
- `after-calendar-change`: `hub-calendar` fires it after a successful
  `apply_change`; planning subscribes and writes the snapshot. `hub-calendar`
  no longer names planning, tasks, or snapshot scripts. Its merged-gate
  exception becomes generic: another installed module may show the complete
  preview together with its own diff on one screen.
- `joint-task-change.md` moves from `hub-calendar` to planning.

### Calendar server cleanup

- The MCP tool `prepare_evening_review` and `evening_review.py` are removed; the
  server keeps only calendar tools. The evening review reads events with
  `read_events`, writes and lists snapshots with `snapshot-calendar.sh`
  (planning), and reads pending friction with `workflow_friction.py`
  (learning, `uses_if_present`). Snapshots then have one writer.
- After the Hub update the calendar server must be restarted (new session).

### Layout and switching

- Moves: `hub-workflows` and planning scripts to `modules/planning/`;
  `hub-calendar`, `calendar-policy/`, `sync-calendar-policy.sh`,
  `build-calendar-bridge.sh`, `grant-calendar-access.sh` to `modules/calendar/`.
  Hub targets stay the same. Tests move with their module and CI runs them.
- planning and calendar get `Switchable: yes`. Disabling calendar while planning
  is selected is refused (existing dependency rule).
- The calendar server is not in the release manifest. When calendar is added or
  removed, `update-installed-hub.sh` lists the extra steps in the preview and,
  after the same confirmation, runs `sync-calendar-policy.sh` (install) or its
  new `--remove` mode: delete `tools/apple-calendar-policy` and the
  `hub_calendar` entry in the Hub's `.mcp.json`, keeping other servers, the
  allowlist, and snapshots. Install adds that `.mcp.json` entry if missing.

### Working Hub

Both modules stay enabled. The update applies the moved files and skill edits;
`sync-calendar-policy.sh` refreshes the server without `prepare_evening_review`;
`drift` exits 0. Disabling is tested only on fixture Hubs.

### Tests

A fixture Hub installed without planning and calendar has no calendar or
planning skill, script, rules file, server, or `.mcp.json` entry, and its task
skills still read `ai/modules.md` with no subscribers; strict test: no file of
core, projects, or tasks names `hub-calendar`, `hub-workflows`, calendar MCP
tools, or planning scripts; the calendar server exposes no evening-review tool;
re-enabling restores everything. Baselines are taken at the branch base, and CI
runs on the pushed branch before merging (session review P1 practice).

## Stage 6 details (TASK-ai-dev-architecture-20260927-003)

Status: approved in chat 2026-09-27. Scope: phase 6 — nested groups, goals file,
group-wide work, one-time data migration.

### Data format

- `ai/archiprojects.md` (owner: projects) holds only `kind: group` entries with
  an optional `parent: <group-id>`. Validation rejects unknown parents, cycles,
  depth above 3 (a top group is depth 1), and any `kind: goal` left in the file.
- `ai/goals.md` (owner: goals, create-if-missing) holds goal entries in the same
  heading + fenced YAML style: `id`, `name`, `status`, `group`, `target`,
  `unit`, `due`. `group` must be a known group. `ai/goal-log.md` is unchanged;
  its `goal_id` now refers to `ai/goals.md`.
- Project cards keep only `primary_archiproject: <group-id|none>`, which must be
  a known group. `archiproject_contribution` and `related_archiprojects` are
  removed from cards, templates, skills, and validation. This supersedes the
  contribution/related parts of decisions 2026-08-24 and 2026-08-28.

### Commands

- `scripts/archiprojects.py` (projects): `validate --hub`, `tree --hub` (group
  tree with member project IDs, indented by depth), `members --hub --group <id>`
  (projects of the group and all subgroups, one per line). `check-hub-registry.sh`
  calls `validate` instead of its own group parsing.
- `read-compact-project-index.sh` gains a sixth column `group` (the card's
  `primary_archiproject`).
- `count-goal-progress.sh` (goals) reads goals from `ai/goals.md`.
- `read-compact-task-index.py` gains `--group <id>`: it reads task files only for
  `members` of that group; without it, behaviour is unchanged.

### Group-wide work

- `hub-task-overview`: "что горит по <группе>" resolves the group by id or name
  from `archiprojects.py tree`, then uses `--group`; a group match is not a
  project confirmation, and opening a project still needs it.
- Planning's day plan and weekly review accept an optional group with the same
  `--group` filter.
- `hub-goal-progress` shows each goal with its group.

### Migration (separately confirmed in the working Hub)

- New groups: `hadassah-promo` («Промо», parent `hadassah`) and `hadassah-seo`
  («SEO», parent `hadassah`).
- `hadassah-promo`: all 30 promo projects — every `release-page-*`,
  `stranitsa-stomatologii`, `stranitsa-vyezdnoy-sluzhby`, `promo-pages`.
- `hadassah-seo`: SEO projects currently in `hadassah`, listed for the user
  before the change (from card names/purposes containing SEO).
- Goals: `hadassah-promo-32-aug-sep` → group `hadassah-promo`;
  `seo-pages-80-sep` → group `hadassah-seo`; both move to `ai/goals.md`.
- Remove the two dropped fields from all 71 cards. The migration is a script
  with `--dry-run` (full diff list) and `--apply`; it never touches project
  folders, only Hub `ai/` files.

### Tests

Validation fixtures for cycle, missing parent, depth 4, goal in the group file,
unknown goal group, unknown card group; tree and members output; compact index
six columns; `--group` reads only member projects (a non-member task file is
not opened); goal progress from `ai/goals.md`; migration dry-run lists exactly
the planned changes and apply is idempotent. The Obsidian generator tolerates
cards without the dropped fields.
