# Hub Skill Namespace And Nested Project Promotion — Design

Date: 2026-08-14
Status: approved for planning
Projects touched: `ai-dev-architecture` (part A), Personal AI Hub installation and
five hub projects (part B)

## Problem

A mini-audit of the running hub found two structural defects. Both come from the
same root: work was done in an installed hub without a matching upstream rule, so
nothing could detect the resulting drift.

### A. Six hub skill names collide with project skill names

Ten projects carry standalone-mode skills copied from `template/ai/skills`. That
is a supported mode, not a defect. The defect is that six hub-owned skills share
a name with a project-owned skill of the same name but different content:

| Skill | Hub version | Project version | Projects affected |
|---|---|---|---|
| `environment-check` | 23 lines | 251 lines | 10 |
| `task-switch` | 25 lines | 139 lines | 10 |
| `task-finish` | 31 lines | 153 lines | 10 |
| `task-intake` | 26 lines | 157 lines | 9 |
| `knowledge-capture` | 75 lines | differs | 1 |
| `knowledge-review` | 63 lines | differs | 1 |

The hub versions are thin and boundary-focused; the project versions are full
standalone procedures. No architecture rule states which one applies inside a
hub-confirmed project, so skill selection is undefined. Observed in practice:
this session used the hub versions, but nothing forces that choice.

`hadassah-seo-planner` additionally lacks `task-intake` — the same project that
was missing `ai/future-tasks.md`. Its standalone install is incomplete.

### B. Six standalone projects are nested inside three registered projects

`hadassah-seo-tech`, `hadassah-content`, and `hadassah-analytics` each contain
one to three subdirectories that are complete standalone installs: their own
`ai/architecture.md`, own skills, and all six memory files. The hub cannot route
to them, and hub workflows operate on the container's memory instead of theirs.

The three containers are thin wrappers: their own `ai/`, an empty `knowledge/`
scaffold, and one to three commits. All substantive content sits in the nested
directories.

The local router does not model this. It states: `Areas have no separate current
task; the confirmed project's existing ai/current-task.md remains the only task
memory.` The nested directories each hold their own unfinished task, and the user
works on them in parallel. Installing a local router would collapse six task
states into three, which is a loss of information, not a formalization.

## Decisions

### A. Rename rather than write a precedence rule

A precedence rule ("hub-owned skills win inside a confirmed project") is a
convention that depends on an agent reading and obeying it. Distinct names are a
structural guarantee. The structural fix is chosen deliberately, accepting that
it costs more now.

All fifteen hub skills take a `hub-` prefix, not only the six that collide. A
uniform rule has no exceptions to remember and cannot be reopened by a future
standalone skill that happens to pick a colliding name.

The rename is only safe once the updater can remove superseded paths.
`update-installed-hub.sh` currently copies from a fixed list and never deletes
anything that disappears upstream, so a rename alone would leave the old
directories in every installed hub — reproducing the exact collision under the
old names, plus orphaned files.

### B. Promote nested projects; do not add a "program" concept

Considered and rejected: a new registry-level concept for a parent project with
child projects that keep their own memory and share context. It would honestly
model the situation, but the shared context it protects does not currently exist
as a mechanism. The nested directories are self-contained standalone installs
that have never read each other. Their shared context is directory adjacency —
convenience for the human reader, not something any agent consumes. Adding a
registry schema, router support, and validation for a benefit nothing currently
uses contradicts the project's own rule against unjustified entities.

If parallel switching between promoted projects turns out to be real friction,
the cheaper next step is a `Related:` card field that lets the router offer a
sibling switch. The full parent/child concept stays unbuilt until that proves
insufficient.

## Part A — Design

### A1. Superseded-path removal in `update-installed-hub.sh`

Add an explicit `SUPERSEDED_PATHS` array of hub-relative paths to delete from an
installed hub because they were renamed or retired upstream. Explicit list, never
"delete whatever is absent from the template" — the latter eventually deletes
something the user added.

Guards:

- `check-consistency.sh` verifies `SUPERSEDED_PATHS` does not intersect hub
  memory files (registry, cards, `active-project.md`, cross-project signals) or
  the current `PROTECTED_FILES` list. This extends the existing update-class
  overlap check.
- Paths resolve inside the hub; symlinked paths are refused.
- Removals appear in the update preview as their own block and require explicit
  confirmation before anything is deleted.

### A2. Rename all fifteen hub skills

`ai/skills/<name>/` becomes `ai/skills/hub-<name>/` for all fifteen.

Files to update:

- `hub-template/ai/architecture.md` — every skill reference
- `hub-template/CLAUDE.md`, `hub-template/AGENTS.md`
- each `hub-template/ai/skills/hub-*/SKILL.md` — frontmatter `name:` and every
  cross-reference to another hub skill
- `scripts/check-consistency.sh` — `HUB_REQUIRED_SKILLS`
- `scripts/hub-smoke-test.sh` — skill name lists and contract assertions
- `scripts/update-installed-hub.sh` — `PROTECTED_FILES`, plus the fifteen old
  paths added to `SUPERSEDED_PATHS`
- `docs/` and `getting-started/` references
- the live hub installation at `_ai-hub`, renamed directly

Bump `hub-template/ai/architecture.md` to `1.3` so `update-installed-hub.sh`
delivers the change to hubs already at `1.2`.

### A3. Guards against the collision returning

- `check-consistency.sh` (template side): every directory under
  `hub-template/ai/skills/` must start with `hub-`.
- `check-hub-registry.sh` (installed-hub side): a directory under
  `<hub>/ai/skills/` without the `hub-` prefix is an error naming the exact path.
  This detects a stale directory left by an incomplete update — the failure mode
  that motivated A1.

## Part B — Design

### B1. Per-container handling

| Container | Nested | Action |
|---|---|---|
| `hadassah-analytics` | 1 | Flatten in place: nested content moves up one level. Keeps its id, card, registry entry, and repository. No new project. |
| `hadassah-seo-tech` | 2 | Promote both to new registered projects. |
| `hadassah-content` | 3 | Promote all three to new registered projects. |

Registry: 23 → 28 projects. Five entries are added; the two emptied containers
stay in the registry with `Status: archived` rather than being removed.

### B2. Containers are archived, not deleted

After promotion, `hadassah-seo-tech` and `hadassah-content` are empty shells
holding their own git history. Set `Status: archived` in the registry and card,
and keep the directories. Deletion is irreversible and buys nothing; the history
is the only copy of the nested directories' past. Deletion is a separate decision
once the promoted projects are confirmed healthy.

Archived projects are exempt from the required-memory-file check, so this status
is consistent with the guard added earlier today.

### B3. Identifiers

| Current path | Proposed id |
|---|---|
| `hadassah-seo-tech/seo-audit-13-jul` | `hadassah-seo-audit-jul` |
| `hadassah-seo-tech/вся техничка:работа с подрядчиком` | `hadassah-seo-tech-contractor` |
| `hadassah-content/кц:онкология` | `hadassah-content-oncology` |
| `hadassah-content/цк:детская хирургия` | `hadassah-content-pediatric-surgery` |
| `hadassah-content/цк:центр коррекции веса и метаболизма` | `hadassah-content-weight-metabolism` |

Open question for the user, to settle before implementation: the registry already
holds `hadassah-seo-audits` and `hadassah-audit-2026-08-10`, so
`hadassah-seo-audit-jul` joins a crowded set of similar names. If the three cover
different work, the names should separate them more clearly.

### B4. Move mechanics

Each promoted directory moves to `<hub>/projects/<new-id>` and receives a fresh
local git repository, an initial commit, and a private GitHub repository named
after its id — the Repository Provisioning flow. History is not extracted from
the container repository; it stays in the archived container.

No new skill. `project-create` targets new scaffolds, `project-register` targets
existing direct children, and `project-migrate` targets a confirmed external
legacy source; none covers promoting a nested directory. Five one-off moves do
not justify a sixth workflow. If promotion recurs, add `project-promote` then.

### B5. Confirmation sequence

Per hub rules, each promotion needs its own explicit confirmation naming the id
and the exact path. Filling each card's `Purpose` and `Typical tasks` requires
reading that project's memory, which is a separate confirmation and must happen
before the move, not after.

### B6. Preconditions verified before any move

1. No nested directory references another nested directory or its container. If
   cross-references exist, promotion stops until they are understood.
2. `hadassah-analytics` has no live unfinished task in its own `ai/current-task.md`.
   If it does, flattening would overwrite it, and that container follows the same
   promotion path as the other two instead.

## Verification

- `bash scripts/check-consistency.sh` — passes, including the two new checks
- `bash scripts/hub-smoke-test.sh` — passes, with coverage for superseded-path
  removal (including refusal to remove a hub memory file) and for the `hub-`
  prefix guards
- `bash scripts/smoke-test.sh` — passes
- `bash scripts/check-hub-registry.sh <hub>` — passes with 28 projects
- Mutation check: disabling either new guard makes the smoke test fail
- Each promoted project has six memory files, a valid card, a local repository,
  and either a pushed remote or an explicit `pending-sync` report

## Out of scope

- Committing the pending changes in `hadassah-seo-tech` and `seo-content-creator`
  (audit item 5) — a routine chore, handled separately without a spec.
- `FT-20260814`, live verification that `project-create` provisions a GitHub
  repository — handled separately. Part B exercises the same provisioning path
  five times and will produce strong incidental evidence, but the future task
  remains open until it is verified on a genuinely new project.
- Removing standalone skills from the ten projects. Standalone mode stays
  supported; only the naming collision is being fixed.
- Repairing the incomplete standalone install in `hadassah-seo-planner` (missing
  `task-intake`). Recorded here so it is not lost.

## Risks

- The rename touches every hub skill reference across two repositories. The
  existing consistency and smoke tests cover the reference lists, which is what
  makes the rename mechanical rather than risky.
- Superseded-path removal is the first mechanism in this system that deletes
  files in a user's installation. It is confirmation-gated and limited to an
  explicit list, but it is the highest-risk change in this design.
- Promotion moves directories whose names contain colons, spaces, and Cyrillic.
  Destination names are ASCII slugs, so the risk is confined to the move step.
