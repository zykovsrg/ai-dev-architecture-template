# Design: `--check` version command for the updater

Date: 2026-06-16
Status: approved (design)

## Goal

Add a `--check` mode to `scripts/update-installed-architecture.sh` that compares the
architecture version installed in a project against the version in the template repo
and, when the project is behind, reports it and shows a dry-run preview (without
applying).

## Why extend the existing script (not a new one)

The updater already resolves the source (curl from GitHub `main` by default, or local
`--source`) and validates that the target is a project with the architecture
installed. A separate script would duplicate that logic. DRY: add a flag.

## Behaviour

`--check`:

1. Resolve the source template (existing `resolve_source_template`).
2. Read the version from the project's `ai/architecture.md` and the source's
   `template/ai/architecture.md`. The version is the first line matching
   `^Version: <X>.<Y>`.
3. Compare numerically: parse `major.minor` as integers; project is "behind" if
   source major > project major, or equal major and source minor > project minor.
4. Outcomes:
   - Up to date (project >= source): print `Architecture is up to date (vX.Y).`,
     exit 0.
   - Behind: print `Project: vX.Y, latest: vZ.W — update available.`, then run the
     existing dry-run diff display, then print the apply command hint, exit 1.
   - Project version unreadable (old format, missing line): print
     `Could not read project architecture version — recommend updating.`, show the
     dry-run, exit 1.
   - Source version unreadable: this is an internal error — `die` with a clear message.

Exit codes: 0 = up to date; 1 = behind or unreadable project version; existing non-zero
`die` codes for setup errors (not a git repo, source missing, etc.).

`--check` combines with `--source` and `--ref` (same source resolution). It ignores
`--commit`/`--allow-dirty` (it never writes). If combined with `--apply`, `--check`
wins and nothing is applied (check is read-only).

## Implementation notes

- Add `CHECK="false"`. Arg `--check` sets `CHECK="true"` and `MODE="dry-run"` (so the
  existing dry-run display is reused for the preview).
- Add `read_arch_version FILE` helper: prints the `X.Y` after `Version:` or empty.
- Add `version_lt A B` helper: returns 0 (true) if version A < version B, numeric
  major then minor. Pure POSIX/awk; no `sort -V` dependency (macOS bash 3.2 / BSD).
- After `resolve_source_template`, if `CHECK=true`: compute versions, print the
  comparison. If up to date, exit 0 before the dry-run block. Otherwise set a flag so
  the dry-run block's final `exit 0` becomes `exit 1` and an apply hint is printed.
- Update `usage()` with the `--check` option and an example.

## Docs

- Add a short "Проверить версию" subsection to `docs/update.md` and
  `docs/update-installed-projects.md` with the `--check` usage.
- `README.md`: one line under the update section mentioning `--check`.
- CHANGELOG: `v6.8` entry; bump `ai/architecture.md` to `6.8`.

## Testing

1. Make a temp "project": copy `template/` into a temp git repo, set its
   `ai/architecture.md` to `Version: 6.0`. Run `--check --source <repo>` → expect
   "update available", a dry-run diff, exit 1.
2. Set the temp project's version equal to the source → expect "up to date", exit 0.
3. Remove the `Version:` line from the temp project → expect "could not read", exit 1.
4. `version_lt` unit checks: `6.9 < 6.10` true, `6.10 < 6.9` false, `6.7 < 6.7` false,
   `5.9 < 6.0` true.
