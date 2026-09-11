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

## Independent verification remediation

### Remediation 1 — compact index allowed root

- Finding: `scripts/read-compact-task-index.py` trusted registry `Path:` values without proving that the resolved project root was one real direct child of `<hub>/projects`.
- RED commit: `7d37140a8bca113c5d8497238e11cba4bb5ff09f`.
- RED run: `34602361683` — failed as expected after the new path-boundary regression tests were added.
- Observed failure: outside-root, nested, symlink-escape and traversal fixtures were not rejected by the previous implementation.
- GREEN commit: `2a6f2ebc4a8f35534956aeadfd3179611a7cbe37`.
- GREEN run: `34602437346` — `success`.
- Changed files: `tests/test_compact_task_index.py`, `scripts/read-compact-task-index.py`.
- Tests: outside `<hub>/projects`; nested rather than direct child; symlink escape; lexical path traversal; existing strict task-record validation retained.
- Result: PASS. Registry project paths must be absolute, non-symlink, traversal-free directories whose resolved parent is exactly the resolved `<hub>/projects` root.

### Remediation 2 — true compact / lazy discovery

- Finding: compact output excluded task bodies, but primary discovery still used `read_text()` on complete `current-task.md`, `future-tasks.md` and `paused-tasks.md` files for every active project.
- RED commit: `1bc17742139158f8fb24ab45ade689544a48ffa4`.
- RED run: `34602529560` — failed as expected because canonical task files were still full-read.
- Observed failure: a regression fixture that forbids `Path.read_text()` for canonical task records exposed the eager reads; a large body marker was included in the fixture but must never be needed for discovery.
- GREEN commit: `f0664658148d7f6ff3b7f2011091fdbda42d52c2`.
- GREEN run: `34602651781` — `success`.
- Changed files: `tests/test_compact_task_index.py`, `scripts/read-compact-task-index.py`, `scripts/task_records.py`.
- Tests: primary discovery succeeds while full-file `Path.read_text()` is forbidden; the large body marker is absent from output; per-kind ID/status/due/title validation remains shared and strict.
- Result: PASS. Primary discovery now streams canonical files line-by-line and retains only metadata required for `project_id`, `task_id`, `title`, `status`, `due`, `source_kind`, `source_path`; full canonical records remain available for a later selected-task read.

### Remediation 3 — pin remote source SHA

- Finding: mutable remote refs could be resolved separately for preview and apply, so a branch/tag moving between those phases could change the applied source after review.
- RED commit: `19f619498f00d4554ac214f65d5a1eec9e23c669`.
- RED run: `34602766464` — branch-move regression failed against the old wrapper/engine contract.
- Observed failure: the old runtime did not carry one immutable source commit SHA as an enforced part of the reviewed apply contract.
- GREEN commit: `91bd694160b3e8a8b6552059842c4ba97b41c6d2`.
- Test-fixture-only follow-ups: `94d2f59a47576c6714b5ede37ac868b5c20dc52e`, `dc132367fa365cdaedf30b92af9c71ec5f0f28e7`, `ece45a3f81c1ebe1dcc233cb2ef78f01ae36cfa2`, `68b3b32f39efea06f7908bcc53b0a17b5fdd23cc`; these isolated the GitHub Actions shallow checkout, canonical `_ai-hub` basename and installer `.gitignore` normalization from the source-pinning assertion without changing release behavior.
- GREEN run: `34603713031` — architecture and calendar-policy jobs both `success`.
- Changed files: `tests/test_hub_update_check.sh`, `scripts/update-installed-hub.sh`, `scripts/hub_release.py`.
- Tests: local remote branch is previewed at SHA A, moved to SHA B, then confirmed apply uses SHA A and must not install the B marker; CLI/wrapper requires reviewed source SHA for remote apply.
- Result: PASS. Remote preview resolves one SHA, that SHA participates in the plan hash, and remote apply fetches/enforces the confirmed SHA rather than re-resolving the mutable ref.

### Remediation 4 — transactional installed.json

- Finding: managed files were rollback-capable but `.local/hub-release/installed.json` was written after file apply with an ordinary non-transactional write.
- RED commit: `f5f2d7ff63356e6949eb4396a4909f2858509832`.
- RED run: `34603019413` — new metadata fault-injection regressions failed against the previous implementation.
- Observed failure: failure before/during metadata replacement could leave managed files and release metadata in different states, including when no prior `installed.json` existed.
- GREEN commit: `fc427e542483dbf966f22e8e6d0f9f0cd64df7e9`.
- GREEN run: `34603713031` — all focused release unit tests and the full architecture/calendar workflow passed.
- Changed files: `tests/test_hub_release.py`, `scripts/hub_release.py`.
- Tests: metadata staging failure and metadata replace failure, each with previous `installed.json` present and absent; managed-file and metadata before-state checked after failure.
- Result: PASS. Metadata is staged in the release state directory, installed by atomic `os.replace`, backed up when present, restored exactly on failure or returned to absence when originally absent, with temporary-file cleanup inside the same rollback boundary as managed files.

### Remediation 5 — remove retired managed files

- Finding: preview only considered incoming manifest files, so files managed by the previous release but removed upstream remained installed indefinitely.
- RED commit: `101d1065e08732b68496db477b77b6e83d74b0d9`.
- RED run: `34603221855` — new retired-file regressions failed against the previous implementation.
- Observed failure: a previously managed target absent from the incoming manifest produced no remove operation; local modification, create-if-missing preservation and removal rollback therefore had no enforceable lifecycle.
- GREEN commit: `4d89f64605e15e4792460eb9414f71f41f8a2782`.
- GREEN run: `34603713031` — all four retired-file regressions plus the full architecture/calendar workflow passed.
- Changed files: `tests/test_hub_release_retired.py`, `scripts/hub_release.py`.
- Tests: unchanged retired managed file → remove/apply delete; locally modified retired managed file → conflict/preserve; retired create-if-missing memory file → preserve; injected failure after removal → exact bytes and mode restored.
- Result: PASS. Preview now compares previous installed baseline with the incoming manifest, generates safe remove operations only for unchanged previous `managed` targets, preserves create-if-missing state and includes removal in transactional rollback.

### Remediation regression status

Implementation regression run `34603713031` passed the complete architecture-focused workflow. It verifies the new compact-path and lazy-discovery tests, immutable source-SHA wrapper test, transactional release metadata tests and retired-file tests together with Hub-only consistency, Hub smoke, architecture smoke, assistant workflows, the complete Python unittest suite and the full Calendar policy pytest suite.

Scoped result: all five authoritative remediation findings are fixed. No HIGH/MEDIUM finding from this remediation list remains open. This statement does not constitute a new architecture audit.

## Status

Tasks 1–9 and independent verification remediation 1–5 are implemented. Hub-only distribution remains intact; standalone/template distribution has not been restored. No merge into `main` was performed. A final CI run on this progress-record commit is required before the branch is handed back for the next independent verification session.
