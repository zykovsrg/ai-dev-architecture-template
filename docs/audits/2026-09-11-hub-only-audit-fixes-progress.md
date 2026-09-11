# 2026-09-11 Hub-Only Audit Fixes — Progress

Specification: `docs/superpowers/specs/2026-09-11-hub-only-audit-fixes-design.md`
Plan: `docs/superpowers/plans/2026-09-11-hub-only-audit-fixes.md`
Branch: `audit/hub-only-fixes-2026-09-11`
Base `main`: `2a172790e6d45ab33aced3b4f14e9a310493e02f`
Execution: GitHub branch + GitHub Actions; the requested local filesystem path was unavailable in this session.

## Baseline

- Baseline run: `34586554005`.
- `check-consistency`, repository Python unit tests, assistant-workflows and Calendar policy passed.
- Pre-existing blockers were recorded rather than treated as TDD RED: Hub entry exceeded the old smoke size limit; `calendar-date.sh` used macOS-only `date -j`; initial Linux runner also lacked a usable `/private/tmp`.
- Final implementation removed these portability/context blockers rather than suppressing them.

## Tasks 1–5

### Task 1 — evening-review friction dispositions

- RED: `6106134e549e4fc33c4949a38799de234e10a51a`, run `34586657860` — 4 expected Calendar-policy failures: accepted/rejected observations still appeared pending and malformed state was not rejected.
- GREEN: `341b2c8ddcfa4fd93f04085f67c37e6d11dcb250`, run `34586758742`.
- Result: evening review follows accepted/rejected/pending observation disposition state and rejects malformed state.

### Task 2 — learning proposal lifecycle/schema

- RED: `0506321b67bc7d45a11a2136ef5aaa1d99d45edd`, run `34586942087` — learning actions absent from proposal schema and friction was consumed on proposal display.
- GREEN fixes: `fa53cf6c3e4408e345c88159e1259bcf90567c6d`, `a311b4facf6ef1c02c8d743cb2324eba6686a73f`; run `34587109595`.
- Result: `goal_progress`, `add_observation`, `promote_rule`, `retire_rule` share the proposal vocabulary; display leaves friction pending and only acceptance/rejection resolves it.

### Task 3 — task aggregation and compact discovery

- RED run `34588675548`: missing `read_project_records` aggregate API.
- Second RED run `34588757742`: missing compact task index.
- GREEN run `34588834738`.
- Result: strict three-record aggregation plus deterministic active-project compact index with only `project_id`, `task_id`, `title`, `status`, `due`, `source_kind`, `source_path`; archived projects and arbitrary project content are excluded.

### Task 4 — progressive disclosure

- RED: `1d8f77496a7026ba624b8118e8e4f4de0e259bcd` — scenario resources absent and monolithic core still carried detailed formats.
- GREEN: core/resource split ending with run `34589188773`.
- Result: day plan, evening review, weekly review and capture live in scenario resources; shared confirmation/security/proposal authority stays in core.
- Core size: `22,507` bytes before split (`e7c1970a5b0639cb6e7fbb79fa09b959b0cbdb79`) → `9,534` bytes current, reduction `12,973` bytes / `57.6%`.

### Task 5 — atomic Calendar snapshots

- RED: `3b1d8c3d036364815bf51e31085ab62228dbbaa2`, run `34589266408` — 16 concurrent calls collided on the same snapshot filename.
- GREEN: `60a603e09ec526f17eebd227888af011262b1ccc`, run `34589337582`.
- Result: snapshot allocation is atomic and collision-safe.

## Task 6 — retire standalone distribution

- RED: `6bae162232e934a70e12281a066c93780e234641`, run `34589625642` — default install was standalone, standalone remained writable/updatable, `template/` existed and active docs advertised it.
- Consumer inventory: `docs/audits/2026-09-11-standalone-consumer-inventory.md`.
- Physical retirement commit: `088d1c511562fd26042b919528832fe3280efdea`.
- Removed distributable `template/`, root generic `ai/architecture.md` and root generic `ai/skills/`.
- Preserved project-owned memory/history/knowledge (`ai/current-task.md`, `future-tasks.md`, project context, decisions, changelog, session reviews, `knowledge/`) and Hub knowledge workflows.
- Root `AGENTS.md`/`CLAUDE.md` are now minimal direct-open Hub pointers.
- Installer is Hub-only; legacy project updater is a read-only retirement entrypoint.
- Old consolidation recognizes only known exact legacy fingerprints; modified/project-specific files are not silently rewritten.
- Linux/macOS portability fixed for temp paths, ISO date validation and EventKit bridge build.

## Task 7 — one content-addressed release path

- RED updater contract: `d459d2d790df3a54c03daef104f4beb529293599`, run `34595043250`.
- Result: install/update use `scripts/hub_release.py` as the manifest/preview/apply engine.
- Remote branch/tag preview resolves one exact commit SHA; apply can be pinned to that SHA plus reviewed `plan_sha256`.
- Tests cover source-byte hash drift, wrong plan hash, first-adoption conflicts, memory preservation, symlink rejection and rollback after injected mid-apply failure.
- Active documentation rejects executable `curl ... | bash` update guidance.

## Task 8 — final authority model and docs

- RED: `8c709c557942e0580395f64e41294bcf0b8c9703`, run `34595479648` — explicit source-of-truth contract absent.
- GREEN: README now names canonical authorities:
  - Hub / `hub-template/` — shared workflows, routing and security policy;
  - `ai/project-registry.md` — project identity/status/path;
  - project `ai/current-task.md`, `paused-tasks.md`, `future-tasks.md` — task state;
  - `ai/project-context.md`, `ai/decisions.md`, `ai/changelog.md` — orientation, durable decisions, semantic history;
  - optional `knowledge/` — detailed reusable references;
  - project Git — exact file/code history.
- Project cards, compact indexes and Obsidian are documented as projections, not competing authorities.

## Task 9 — acceptance and measurements

Acceptance run before this audit-only progress update: `34595672683` — workflow conclusion `success`; both architecture and calendar-policy jobs passed.

The workflow executes the required acceptance set:

- `bash scripts/check-consistency.sh`
- `bash scripts/hub-smoke-test.sh`
- `bash scripts/architecture-test.sh`
- `bash scripts/assistant-workflows-test.sh`
- `python3 -m unittest discover -s tests -v`
- `(cd calendar-policy && python3 -m pytest -q)`

Final repository checks:

- current recursive tree contains no `template/` path;
- active-doc consistency check finds no supported standalone install/update guidance and no executable pipe-to-shell update path;
- branch comparison against `main`: ahead by 63 commits, behind by 0 at pre-audit HEAD; merge base remains the original `2a172790...` base;
- no merge into `main` was performed.

### Context-size measurements

`hub-workflows` core: `22,507` → `9,534` bytes (`-57.6%`). Scenario detail remains available on demand in four resource files.

Compact task discovery has two relevant measurements:

1. Minimal regression fixture (`tests/test_compact_task_index.py`): three deliberately tiny records per active project are only `484` input bytes for two projects, while normalized JSON with provenance paths is about `1,205` bytes. Therefore the compact index is **not** claimed to compress already-minimal records.
2. Representative canonical-record fixture using the former full current/future/paused task templates with one valid record of each kind for two projects: `5,350` input bytes → `1,205` compact discovery bytes, reduction `4,145` bytes / `77.5%`.

Interpretation: the guaranteed benefit is bounded discovery scope and exclusion of prose/secrets/arbitrary files; byte/token reduction appears when canonical task records contain normal workflow instructions/context, not when input records are already minimal.

## Status

Tasks 1–9 implemented. Functional acceptance is green. This file is the final audit-only documentation change; its own CI run must also pass before the branch is declared ready for independent review.
