# Design: Single source of truth for repeated lists

Date: 2026-06-16
Status: approved (design); plan pending

## Problem

Three rule-lists are copied verbatim across many files:

- protected architecture files — duplicated in ~14 files
- controlled memory files — duplicated in ~19 files
- skill precedence (5 levels) — duplicated in ~11 files

When a list changes, every copy must be edited by hand. In practice copies drift:
the v6.4 review found 12 inconsistencies, almost all caused by this duplication
(stale `architecture.md` version, three different precedence lists, `future-tasks`
missing from `release-check`, etc.). Fixing each symptom does not stop new drift.

## Goal

Make each list have one authoritative definition and prevent silent drift, without
introducing a build/generation step.

Non-goals (explicitly out of scope):

- No template/codegen build pipeline. The user chose a check-script guardrail, not
  generation.
- No machine comparison of the precedence list across languages (it mixes English
  and Russian). Precedence is deduplicated by reference links only.

## Audience split (why two canonical homes are acceptable)

- AI-facing files are read by the agent at runtime: `CLAUDE.md` / `AGENTS.md`
  (always loaded), `ai/architecture.md` and `ai/skills/*` (on demand). These get
  copied into user projects.
- Human-facing files live only in the architecture repo: `README.md`, `docs/*`.

The agent never reads the human docs, so those can point to a canonical page. The
human canonical page (`docs/file-roles.md`) and the AI canonical reference
(`ai/architecture.md`) are two presentations of the same set; the check script keeps
them in lockstep.

## Approach: "holder vs link" + marker-bounded canonical blocks + check script

### 1. Two classes of files per list

- **Holders** — contain the list inline, wrapped in invisible markers, verified by
  the check script. Only files that genuinely need the list at hand:
  - protected-files + controlled-memory: `ai/architecture.md`, `template/CLAUDE.md`,
    `template/AGENTS.md`, `docs/file-roles.md`, and the skills that operate on the
    list: `release-check`, `environment-check`, `task-finish`, `task-switch`.
  - (Holders may contain only the lists they actually use; e.g. `task-switch` holds
    only controlled-memory, not protected-files.)
- **Link-only** — the inline list is removed and replaced with a one-line reference
  to the canonical page. Pure human docs: `README.md`, `docs/concepts.md`,
  `docs/install.md`, `docs/update.md`, `docs/update-installed-projects.md`,
  `docs/prompts.md`, `docs/start-prompts.md`.

Rationale: we do not fight the fact that AI files need the list inline. We allow the
copies but make them provably identical.

### 2. Marker syntax

Each canonical list is wrapped in HTML comment markers (invisible in rendered
markdown, harmless when copied into projects):

```
<!-- canon:protected-files -->
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`
<!-- /canon:protected-files -->
```

Marker names: `canon:protected-files`, `canon:controlled-memory`.

Annotations are allowed on a bullet (e.g. `` - `.claude/` (создаётся проектом…) ``);
the script extracts only the first backtick-quoted path token and ignores the rest,
so English/Russian prose around the path does not break the comparison.

Markers wrap only the enumerated list block. Incidental prose mentions of an
individual file elsewhere (e.g. "`ai/paused-tasks.md` is owned by task-switch") are
left untouched — they are not the canonical list and are not markered or checked.

### 3. Check script `scripts/check-consistency.sh`

Behaviour:

1. For each marker name, find every file under `template/` and `docs/` that contains
   the marker pair.
2. Extract the list of path tokens between the markers (first backtick-quoted span
   per bullet; bullets without a backtick path are ignored).
3. Build an ordered list of paths per file. Compare all holders for that marker.
4. If any holder's path list differs (missing, extra, or reordered path), print the
   marker name, the differing file, and the diff, then exit non-zero.
5. If everything matches, print a short OK summary and exit zero.

Notes:

- Order matters: holders must list paths in the same order. This keeps comparison
  simple and the docs visually consistent. The plan must first define one canonical
  order per list and normalize every holder to it — e.g. `release-check` currently
  orders controlled-memory differently and must be reordered before the script can
  pass.
- The script only enforces the two file-path lists. It does not touch precedence.
- The script lives in `scripts/` (architecture repo only; not copied into projects).

### 4. Wiring into workflows

- `ai/skills/architecture-update/SKILL.md`: add a step — after editing any canonical
  list, run `scripts/check-consistency.sh` and confirm it passes before finishing.
- `ai/skills/release-check/SKILL.md`: add the consistency check to the pre-merge
  checklist; if it fails, mark `Safe to merge: no`.
- `scripts/update-installed-architecture.sh`: optional — after `--apply`, run the
  check and warn (not block) if it fails. (Low priority; include only if cheap.)

### 5. Documentation of the system

Add a short subsection to `ai/architecture.md` (e.g. "Canonical lists and the
consistency check") describing: which lists are canonical, the marker names, which
files are holders vs link-only, and how to run the check. This is the meta-rule that
keeps the system intact across future edits.

### 6. Precedence list (no script)

Deduplicate by reference: keep the 5-level precedence list inline only in
`ai/architecture.md` (AI canonical), `template/CLAUDE.md`, `template/AGENTS.md` (always
loaded), and `docs/concepts.md` (human canonical). Remove it from `README.md`,
`docs/prompts.md`, `docs/update-installed-projects.md`, `ai/external-tools.md`,
`release-check`, `environment-check`, replacing each with a reference link. The check
script does not verify it.

## Testing

The check script is the test. The plan must verify:

1. On the clean repo after refactor, `scripts/check-consistency.sh` exits 0 and
   reports all holders consistent.
2. Deliberate-drift check: temporarily remove or change one path inside one holder's
   marker block; the script must exit non-zero and name that file and the offending
   path. Revert afterwards.
3. Markers render invisibly: spot-check that no marker text appears in the rendered
   list (HTML comments).

## Risks

- A new contributor adds a list copy without markers — the script won't see it. The
  architecture.md documentation section and the `architecture-update` step mitigate
  this by telling editors to use markers.
- Order-sensitive comparison can produce noisy failures if someone reorders for
  readability. Accepted: a fixed order is also good for readers, and the failure
  message is clear.

## File-by-file impact (for the plan)

- New: `scripts/check-consistency.sh`.
- Add markers around existing lists: `ai/architecture.md`, `template/CLAUDE.md`,
  `template/AGENTS.md`, `docs/file-roles.md`, `release-check`, `environment-check`,
  `task-finish`, `task-switch` (controlled-memory only where applicable).
- Remove list + add reference link: `README.md`, `docs/concepts.md`,
  `docs/install.md`, `docs/update.md`, `docs/update-installed-projects.md`,
  `docs/prompts.md`, `docs/start-prompts.md`.
- Precedence dedup: as listed in §6.
- Workflow wiring: `architecture-update`, `release-check`, (optional) updater script.
- Docs: new subsection in `ai/architecture.md`; CHANGELOG entry (v6.5).
