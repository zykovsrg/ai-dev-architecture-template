# Modular Architecture Design

Task: TASK-ai-dev-architecture-20260926-001
Status: approved in chat 2026-09-26 (sections 1–4); written spec pending user review.

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
