# Hub Audit Fixes — Design

Date: 2026-08-15
Status: approved
Source: architecture audit of the live hub and this template repository, session 2026-08-15

## Problem

An audit of the live Personal AI Hub and this template repository found six
defects. None break the architecture's core boundaries: the live hub matches
`hub-template/` byte-for-byte on every rule file, the registry matches the
filesystem 29-for-29, and mutation testing confirmed that the existing checks
catch card/registry mismatches, path escapes, entry-file divergence, canonical
list drift and missing skill files.

The defects share one theme: **checks that report success without having
verified anything**, plus two documentation gaps.

| # | Defect | Severity |
|---|--------|----------|
| 1 | Relative `--source` resolves against the hub directory, so the updater can compare the hub with itself and report "no updates" | breaks work |
| 2 | The registry validator never checks the reverse direction: a directory in `projects/` with no registry entry is invisible | creates risk |
| 3 | `--check` compares version numbers but its output reads as "the files match" | creates risk |
| 4 | Three hub skills are named in no rule layer at all | cosmetic |
| 5 | A changed template `.gitignore` never reaches an installed hub | cosmetic |
| 6 | `hub-registry-check` says "each allowed root" although exactly one root is permitted | cosmetic |

## Evidence

**Defect 1.** `scripts/update-installed-hub.sh` runs `cd "$HUB_DIR"` at line 128
and resolves `SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"` at line 147, inside
`resolve_source_template`. A relative source is therefore resolved relative to
the hub. Reproduced by running `--source .` from this repository:

```
Source template: /Users/zykovsrg/Documents/vibecode/_ai-hub
...
No hub updates found.
```

The existing sanity guards (`AGENTS.md` present, the exact string
`# Personal AI Hub — Codex`, six mandatory hub skills) cannot catch this,
because an installed hub is a copy of the template and satisfies all of them.
`scripts/update-installed-architecture.sh` repeats the pattern at lines 133–134
and 181.

**Defect 2.** `scripts/check-hub-registry.sh` iterates registry entries and
validates each against the filesystem. Nothing iterates the filesystem.
Confirmed by control mutation: `mkdir projects/zz-unregistered-audit-probe`
followed by the validator produced `Registry check passed: 29 projects`,
exit 0. The reverse direction exists only as a manual step in the
`hub-registry-check` skill, which runs only when explicitly requested.

**Defect 3.** With a drifted `<hub>/CLAUDE.md` and an unchanged version number,
`--check` prints `Hub architecture is up to date (v1.4)` and exits 0, while
`--dry-run` against the same state prints the diff. Already recorded as
`FT-20260815-002`.

**Defect 4.** Grepping all fifteen hub skill names against
`ai/architecture.md`, `CLAUDE.md` and `AGENTS.md` returns zero hits for
`hub-project-router`, `hub-registry-check` and `hub-local-router-install`. The
architecture describes each workflow's procedure but never names the skill that
performs it.

**Defect 5.** `PROTECTED_FILES` and `MEMORY_FILES` in
`scripts/update-installed-hub.sh` omit `.gitignore`, so the updater never
delivers it. Current contents are identical (`/projects/`), so there is no
present-day symptom.

**Defect 6.** `hub-template/ai/skills/hub-registry-check/SKILL.md`, step 2,
says "unregistered direct children of each allowed root". `ai/architecture.md`
lines 47–48 permit exactly one root and `check-hub-registry.sh` lines 68–70
enforce it.

## Decisions

Two design choices were settled with the user and constrain implementation.

### Defect 2 is a warning, never an error

An unregistered directory prints `WARNING: unregistered directory in projects
root: <name>` to stderr and leaves the exit code at 0. The stdout line
`Registry check passed: N projects` is unchanged so that anything parsing the
output keeps working.

Rationale, in order of weight:

1. The validator is a gate inside `hub-project-create`, `hub-project-switch`,
   `hub-project-register` and `hub-project-migrate`. An unregistered directory
   does not affect the question that gate asks — the router only ever opens
   registered paths, so such a directory is already unreachable.
2. A hard error would break the architecture's own migration order.
   `ai/architecture.md` lines 117–119 specify move → *separate* registration
   confirmation → validation. Between those steps the moved folder legitimately
   sits in `projects/` unregistered. A strict check would fail on a state the
   documented process creates.
3. The risk found is invisibility, not access. A warning on every run addresses
   exactly that, and is more durable than a strict mode that would eventually
   be worked around.

A `--strict` flag was rejected: two behaviours of one check must be remembered,
tested and documented, and the second solves nothing the first does not.

### Defect 4 gets a guard, not just an edit

Naming the three skills fixes today's drift but does not prevent the next one.
Defect 4 is the only finding in this audit where a divergence had already
occurred and survived unnoticed until a manual audit — direct evidence that the
link between rule layers does not hold without an automated check.

Names go into `hub-template/ai/architecture.md` only. `CLAUDE.md` and
`AGENTS.md` stay untouched: they are deliberately compact and already carry the
rule "route detailed procedures to `ai/architecture.md` and one matching skill".

## Design

### Scripts

**Defect 1 — source resolution.** Expand `--source` to an absolute path where
the argument is parsed, before any `cd` into the target directory, in both
`update-installed-hub.sh` and `update-installed-architecture.sh`. Add a guard
that does not exist today: if the canonical source equals the canonical target,
fail with an explicit error. Without it, "compared itself with itself" stays
reachable by other routes such as a symlink or an explicit `--source` pointing
at the hub.

**Defect 2 — reverse check.** After the registry parsing loop in
`check-hub-registry.sh`, enumerate direct child directories of `projects/` and
compare their names against the collected registry IDs. Names only; no project
content is read, so the "never read project content" boundary is untouched.
Emit the warning described above.

**Defect 3 — honest `--check`.** Text-only change to the `--check` output and
to the `--help` entry, stating that version numbers were compared and pointing
at `--dry-run` for a file comparison. No new code path: content comparison is
what `--dry-run` already does, and a second mode doing the same work would be a
redundant entity. This follows the promotion notes recorded in
`FT-20260815-002`.

**Defect 5 — `.gitignore` delivery.** Not via `PROTECTED_FILES`. Protected
files are overwritten wholesale by `copy_file`, so listing `.gitignore` there
would silently destroy any line a user added to their hub's `.gitignore`.
Instead the updater ensures the required `/projects/` line is present and
appends it when missing, reusing the approach already implemented in
`install-hub.sh` lines 90–91. Nothing is overwritten.

### Rule files

Both are protected architecture files and go through `architecture-update`:
exact wording shown and confirmed before any edit, in this repository and in
the live hub.

**Defect 4.** Name `hub-project-router` in the Local Router section,
`hub-registry-check` in Ownership And Registry, and `hub-local-router-install`
in Project-local Router, in `hub-template/ai/architecture.md`.

**Defect 6.** In `hub-template/ai/skills/hub-registry-check/SKILL.md` step 2,
replace "each allowed root" with wording naming the sole allowed root.

### New consistency check

Add to `scripts/check-consistency.sh`: every directory under
`hub-template/ai/skills/` must be named in at least one of
`hub-template/CLAUDE.md`, `hub-template/AGENTS.md`,
`hub-template/ai/architecture.md`.

This does not overlap the existing `hub skill references` check. That one reads
the hardcoded `HUB_REQUIRED_SKILLS` list at line 128 and verifies
declared → exists. The new check runs exists → declared and needs no list: it
enumerates directories.

## Testing

Every new check is mutation-tested, because a check that does not fail is not a
check. Each mutation is reverted and a clean `git status` confirmed, in both
repositories.

| Mutation | Expected |
|---|---|
| Unregistered directory in `projects/` | warning on stderr, exit 0, stdout line unchanged |
| `--source` pointing at the hub itself | error, non-zero exit |
| Relative `--source` from a third directory | resolves to the intended template, not the hub |
| Hub skill directory named in no rule file | `check-consistency.sh` fails |
| `.gitignore` missing `/projects/` | line appended, pre-existing lines intact |

Regression suite after implementation: `check-consistency.sh`,
`hub-smoke-test.sh`, `smoke-test.sh`, and `check-hub-registry.sh` against the
live hub.

## Delivery order

1. Edit the source repository; run `architecture-update` confirmation for the
   two protected-file changes.
2. Run the mutation tests, then the full regression suite.
3. Separately confirmed step: `update-installed-hub.sh --apply` against the
   live hub, using an absolute `--source`.
4. Run `check-hub-registry.sh` against the live hub.

The live hub currently matches the template exactly, so step 3 delivers only
this change set.

## Out of scope

- `HUB_REQUIRED_SKILLS` at `check-consistency.sh:128` is a fourth uncontrolled
  copy of the skill inventory, unmarked by canonical-list markers. Noted, not
  changed here.
- The legacy standalone copies of the architecture inside 15 hub projects
  (`FT-20260815-001`) and the fate of standalone mode (`FT-20260813-001`).
- The tracked-versus-excluded state of this repository's own `ai/`
  (`FT-20260814-002`).
