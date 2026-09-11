# Hub-Only Audit Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILLS: use `superpowers:executing-plans` and a strict test-driven-development cycle. Execute one task at a time. Do not redesign working Hub behavior outside the approved specification.

**Goal:** Retire standalone architecture completely, fix confirmed Hub correctness bugs, reduce all-project context cost, and leave one tested Hub-only release path.

**Authoritative specification:** `docs/superpowers/specs/2026-09-11-hub-only-audit-fixes-design.md`

**Architecture:** `hub-template/` is the only shared architecture source. Project memory remains local. Hub routing, confirmation, Calendar safety, Obsidian proposal integrity, and optional knowledge skills remain intact.

**Tech stack:** Bash 3.2-compatible shell, Python 3 standard library, existing `pytest` calendar-policy environment, Git, Markdown. Do not add dependencies.

## Global execution rules

- Work from the architecture repository only.
- Preserve unrelated user changes. Never use `git reset --hard`, blanket checkout, `git add .`, or broad cleanup.
- TDD order for every behavior change: failing test → observe intended failure → minimal implementation → focused pass → integration pass → diff review → scoped commit.
- A pre-existing failing baseline must be recorded before changes; do not silently reinterpret it as a regression from this plan.
- Do not run application test suites from registered projects.
- Do not modify project task memory except the architecture project's own task/progress records when the active Hub workflow requires it.
- Do not remove project-local knowledge or genuine project-specific skills while retiring standalone.
- Historical plans/specs/audits may continue to mention standalone. Active runtime and user-facing docs may not.
- If a test fails because a required tool is missing, record the environment limitation and continue only where the intended red/green result can still be proved. `shellcheck` is optional; the repository's own tests are mandatory.

## Baseline commands

Run these before Task 1 and record results in `docs/audits/2026-09-11-hub-only-audit-fixes-progress.md`:

```bash
bash scripts/check-consistency.sh
bash scripts/hub-smoke-test.sh
python3 -m unittest discover -s tests -p 'test_task_records.py' -v
python3 -m unittest discover -s tests -p 'test_workflow_friction.py' -v
python3 -m unittest discover -s tests -p 'test_hub_release.py' -v
(
  cd calendar-policy
  python3 -m pytest tests/test_evening_review.py -q
)
```

Create the progress file before implementation with:

```markdown
# 2026-09-11 Hub-Only Audit Fixes — Progress

Specification: docs/superpowers/specs/2026-09-11-hub-only-audit-fixes-design.md
Plan: docs/superpowers/plans/2026-09-11-hub-only-audit-fixes.md

## Baseline

- check-consistency: <result>
- hub-smoke-test: <result>
- task-record tests: <result>
- workflow-friction tests: <result>
- hub-release tests: <result>
- evening-review tests: <result>
```

Append one short section after each completed task with commit, changed files, tests, and remaining risks.

---

## Task 1 — Fix evening-review friction state

**Files:**
- Modify: `calendar-policy/src/hub_calendar_policy/evening_review.py`
- Modify: `calendar-policy/tests/test_evening_review.py`
- Read only as contract reference: `scripts/workflow_friction.py`, `tests/test_workflow_friction.py`

### Step 1: Write failing regression tests

Add focused tests proving:

1. a friction line with no disposition is returned;
2. the same line with `accepted` state is not returned;
3. the same line with `rejected` state is not returned;
4. a different unresolved line remains returned when another line is resolved;
5. invalid state format fails loudly rather than treating everything as pending.

Use the exact observation ID formula already used by `workflow_friction.py`.

### Step 2: Observe the intended red

```bash
cd calendar-policy
python3 -m pytest tests/test_evening_review.py -q
```

Expected: the new resolved-observation assertions fail because `pending_friction()` currently ignores `.state.json`.

### Step 3: Implement the minimum fix

Update `pending_friction()` so it reads the daily source and optional state file, validates state format, and returns only entries whose disposition is `pending` or absent.

Do not add a new framework. Keep the ID formula byte-for-byte compatible with `scripts/workflow_friction.py`.

### Step 4: Green + regression

```bash
cd calendar-policy
python3 -m pytest tests/test_evening_review.py -q
cd ..
python3 -m unittest discover -s tests -p 'test_workflow_friction.py' -v
```

### Step 5: Commit

```bash
git add calendar-policy/src/hub_calendar_policy/evening_review.py calendar-policy/tests/test_evening_review.py
git commit -m "fix: respect workflow friction dispositions"
```

---

## Task 2 — Make the learning lifecycle and proposal schema consistent

**Files:**
- Modify: `hub-template/ai/skills/hub-workflows/SKILL.md`
- Modify: `hub-template/ai/skills/hub-workflows/resources/learning-lifecycle.md` only if wording needs one canonical statement
- Modify: `scripts/assistant-workflows-test.sh`
- Modify: `scripts/check-consistency.sh`

### Step 1: Add failing contract tests

Add tests that fail unless:

- showing a proposal does not consume friction;
- the workflow no longer says that evening review marks friction consumed immediately after proposal;
- the proposal action schema includes `goal_progress`, `add_observation`, `promote_rule`, and `retire_rule`;
- every learning action referenced in the preserved lifecycle exists in the canonical action enum.

The consistency check should compare referenced learning actions with the declared proposal actions rather than merely grep for one hard-coded sentence.

### Step 2: Observe red

```bash
bash scripts/assistant-workflows-test.sh
bash scripts/check-consistency.sh
```

Expected: failure on current consumed wording and missing learning actions.

### Step 3: Implement the minimum contract change

Change the proposal envelope action list to include all existing learning actions.

Replace the contradictory lifecycle sentence with the canonical sequence:

```text
proposal shown → still pending → accepted/rejected → resolved
```

Keep acceptance order: journal write first, then resolve accepted. Rejection resolves without a journal append. Failed append leaves pending.

### Step 4: Green

```bash
bash scripts/assistant-workflows-test.sh
bash scripts/check-consistency.sh
```

### Step 5: Commit

```bash
git add hub-template/ai/skills/hub-workflows scripts/assistant-workflows-test.sh scripts/check-consistency.sh
git commit -m "fix: unify hub learning proposal lifecycle"
```

---

## Task 3 — Repair task-record aggregation and add a compact task index

**Files:**
- Modify: `scripts/task_records.py`
- Modify: `tests/test_task_records.py`
- Create: `scripts/read-compact-task-index.py`
- Create: `tests/test_compact_task_index.py`
- Modify: `scripts/hub_release.py` to ship the new runtime script
- Modify: `hub-template/ai/skills/hub-workflows/SKILL.md`

### Step 1: Add failing `read_project_records()` tests

In `tests/test_task_records.py`, add tests for:

- current + future + paused records combine into one list;
- per-kind validation is preserved;
- invalid current/future/paused input still raises;
- the existing three-file CLI branch returns JSON instead of raising `NameError`.

Run:

```bash
python3 -m unittest discover -s tests -p 'test_task_records.py' -v
```

Expected: fail because `read_project_records()` is undefined.

### Step 2: Implement aggregate parsing

Add only:

```python
read_project_records(project_id, current_text, future_text, paused_text)
```

It must call the existing strict `read_records()` logic for each kind and concatenate normalized rows. Add `source_kind` to aggregate rows if needed by the compact index without changing existing single-file output contracts.

Rerun the focused tests until green.

### Step 3: Add failing compact-index tests

`tests/test_compact_task_index.py` should create a temporary Hub with:

- two active registered projects;
- one inactive/archived project;
- current/future/paused records;
- one invalid record fixture.

Assert that the compact index:

- includes only active registered projects;
- emits only normalized discovery fields (`project_id`, `task_id`, `title`, `status`, `due`, `source_kind`, `source_path`);
- never emits full Markdown bodies or unrelated project files;
- fails if a selected active project's canonical task record is invalid;
- produces deterministic ordering.

### Step 4: Implement compact index

Create `scripts/read-compact-task-index.py --hub HUB`.

It must:

1. read the canonical registry;
2. select active registered projects only;
3. read exactly `ai/current-task.md`, `ai/future-tasks.md`, and `ai/paused-tasks.md`;
4. call `read_project_records()`;
5. emit compact JSON rows only.

Do not read project code, knowledge, changelog, decisions, or arbitrary files.

Add the script to `RUNTIME_SCRIPTS` in `scripts/hub_release.py`.

### Step 5: Route personal-assistant discovery through the index

Update the shared workflow rule so personal-assistant day/weekly/overdue/blocked discovery starts from the compact index. Full canonical task records are opened only for selected records when details absent from the index are required.

The compact index remains derived data, not evidence replacing the source record. Final factual output should still cite canonical source paths.

### Step 6: Green

```bash
python3 -m unittest discover -s tests -p 'test_task_records.py' -v
python3 -m unittest discover -s tests -p 'test_compact_task_index.py' -v
python3 -m unittest discover -s tests -p 'test_hub_release.py' -v
bash scripts/assistant-workflows-test.sh
bash scripts/check-consistency.sh
```

### Step 7: Commit

```bash
git add scripts/task_records.py scripts/read-compact-task-index.py scripts/hub_release.py tests/test_task_records.py tests/test_compact_task_index.py hub-template/ai/skills/hub-workflows/SKILL.md
git commit -m "feat: add compact hub task discovery"
```

---

## Task 4 — Split `hub-workflows` into progressive resources

**Files:**
- Modify: `hub-template/ai/skills/hub-workflows/SKILL.md`
- Create: `hub-template/ai/skills/hub-workflows/resources/day-plan.md`
- Create: `hub-template/ai/skills/hub-workflows/resources/evening-review.md`
- Create: `hub-template/ai/skills/hub-workflows/resources/weekly-review.md`
- Create: `hub-template/ai/skills/hub-workflows/resources/capture.md`
- Modify: `scripts/assistant-workflows-test.sh`
- Modify: `scripts/check-consistency.sh`

### Step 1: Add failing progressive-disclosure assertions

Tests must require:

- all four scenario resources exist;
- core `SKILL.md` references each resource;
- common security, project scope, proposal envelope, and confirmation rules remain in core;
- detailed scenario heading/format contracts live in their matching resource, not duplicated across core;
- each resource points back to core authority instead of redefining scope.

### Step 2: Observe red

```bash
bash scripts/assistant-workflows-test.sh
bash scripts/check-consistency.sh
```

### Step 3: Move, do not redesign

Move existing day-plan, evening-review, weekly-review, and capture-specific instructions into their matching resource.

Keep behavior, exact output headings, proposal semantics, Calendar restrictions, and canonical-source rules unchanged.

Keep in core only:

- purpose/routing;
- personal-assistant scope;
- common fixed sequence;
- common canonical-input rules;
- proposal envelope;
- confirmation boundary;
- preserved learning lifecycle summary;
- resource dispatch instructions.

### Step 4: Green and size check

```bash
bash scripts/assistant-workflows-test.sh
bash scripts/check-consistency.sh
wc -c hub-template/ai/skills/hub-workflows/SKILL.md
```

Acceptance: core `SKILL.md` is materially smaller than the pre-change ~22 KB and no longer contains the full detailed format of all four workflows. Do not chase an arbitrary byte target if it requires duplicating rules elsewhere.

### Step 5: Commit

```bash
git add hub-template/ai/skills/hub-workflows scripts/assistant-workflows-test.sh scripts/check-consistency.sh
git commit -m "refactor: split hub workflows by scenario"
```

---

## Task 5 — Make Calendar snapshot creation atomic

**Files:**
- Modify: `calendar-policy/src/hub_calendar_policy/evening_review.py`
- Modify: `calendar-policy/tests/test_evening_review.py`

### Step 1: Add failing concurrency regression

Add a test that creates many snapshots for the same day concurrently and asserts:

- every returned path is unique;
- every path exists;
- no snapshot content was overwritten by another call;
- all names still match `YYYY-MM-DD-*` so `prior_snapshots()` can discover them.

### Step 2: Observe red

```bash
cd calendar-policy
python3 -m pytest tests/test_evening_review.py -q
```

The old count-before-write implementation is race-prone; the test must demonstrate the collision or exercise a deterministic collision hook rather than relying on luck.

### Step 3: Implement atomic unique creation

Use standard-library atomic unique file creation (`tempfile`, `mkstemp`, or `os.open(..., O_CREAT|O_EXCL)`). Keep the daily prefix and UTF-8 text format.

Do not add locking infrastructure.

### Step 4: Green

```bash
cd calendar-policy
python3 -m pytest tests/test_evening_review.py -q
```

### Step 5: Commit

```bash
git add calendar-policy/src/hub_calendar_policy/evening_review.py calendar-policy/tests/test_evening_review.py
git commit -m "fix: create calendar snapshots atomically"
```

---

## Task 6 — Retire the standalone distribution

**Files:**
- Create: `tests/test_hub_only_distribution.py`
- Modify: `scripts/install.sh`
- Modify or retire: `scripts/update-installed-architecture.sh`
- Modify: `scripts/check-consistency.sh`
- Modify: `scripts/hub-smoke-test.sh`
- Modify: `README.md`
- Modify relevant active docs under `docs/` and `getting-started/`
- Remove after active-reference check: `template/**`
- Reconcile root project entry/rule copies: `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, `ai/external-tools.md`, root generic `ai/skills/**`
- Preserve root project memory and true local extensions

### Step 1: Inventory active standalone consumers

Before deletion, record exact active references with commands equivalent to:

```bash
git grep -nE 'template/|--mode standalone|standalone architecture|update-installed-architecture' -- \
  ':!docs/superpowers/**' ':!docs/audits/**' ':!CHANGELOG.md'
```

Historical plans/specs/audits are evidence and may keep old wording. Active runtime/user docs must be migrated.

Also inventory root `ai/skills/` against Hub shared skills and classify each root skill as:

- exact/shared generic copy → remove from project-local rules;
- genuine project-specific extension → preserve and list briefly in project context;
- unclear → stop on that item rather than deleting it.

Do not delete project memory or knowledge.

### Step 2: Write failing Hub-only distribution tests

`tests/test_hub_only_distribution.py` must prove:

- running `scripts/install.sh` with no mode selects Hub;
- `--mode hub` selects Hub;
- `--mode standalone` exits nonzero and writes nothing;
- no installer path copies `template/` into a project;
- the legacy updater cannot apply or restore standalone architecture;
- active documentation does not instruct users to install/update standalone;
- Hub knowledge skills still exist.

Before deleting `template/`, add an assertion that the final repository must not contain an active distributable `template/` tree.

### Step 3: Observe red

```bash
python3 -m unittest discover -s tests -p 'test_hub_only_distribution.py' -v
```

Expected: fail on current default standalone install and existing `template/`.

### Step 4: Make installer Hub-only

Change `scripts/install.sh` so:

```text
no mode        → hub
--mode hub     → hub
--mode standalone → explanatory exit 2, no writes
```

Remove interactive standalone fallback, standalone template resolution, and standalone `rsync` branch.

### Step 5: Retire legacy updater safely

If `scripts/update-installed-architecture.sh` still has an active migration entrypoint, reduce it to a read-only retirement/migration message. It must never copy generic standalone rules again.

If active callers are zero after docs/scripts are updated, removal is allowed instead. The test must cover the chosen final contract.

### Step 6: Remove standalone source and root generic copies

Delete `template/**` only after all active consumers are gone.

For the architecture repository itself, preserve project memory. Replace full root generic entry files with the minimal Hub-managed routing pointer required by the supported clients, or remove a pointer only if direct-open routing tests prove it unnecessary. Remove project-local generic architecture copies and exact shared-skill copies; preserve confirmed project-specific extensions.

Do not delete `.claude/`, `.agents/`, `.codex/`, knowledge, or unrelated configuration merely because standalone is retired.

### Step 7: Rewrite active docs

README/install/update/help must describe only:

```text
install Hub → register/create/migrate project → work through Hub
```

No active document should present standalone as an available mode.

### Step 8: Green

```bash
python3 -m unittest discover -s tests -p 'test_hub_only_distribution.py' -v
bash scripts/hub-smoke-test.sh
bash scripts/check-consistency.sh
```

### Step 9: Commit

Use explicit paths after reviewing the deletion list:

```bash
git add scripts tests README.md docs getting-started hub-template AGENTS.md CLAUDE.md ai
git add -u template
git commit -m "refactor: retire standalone architecture"
```

Do not use `git add .`.

---

## Task 7 — Make one Hub release/update path authoritative

**Files:**
- Modify: `scripts/hub_release.py`
- Modify: `tests/test_hub_release.py`
- Modify as needed: `scripts/install-hub.sh`, Hub update/check scripts that actively deploy shared files
- Modify: `tests/test_hub_update_check.sh`, `tests/test_live_hub_merge.py` only where their current contract overlaps
- Modify active docs with release/update commands

### Step 1: Add failing release regressions

Tests must cover:

- preview plan hash changes if source bytes change;
- apply refuses a different plan hash;
- conflict preserves local modified managed files;
- an injected apply failure restores already-replaced files;
- create-if-missing memory remains untouched when present;
- a remote symbolic ref is resolved once and the same commit SHA is used for preview/apply by the caller;
- active update docs contain no `curl | bash` examples.

Do not duplicate the release engine in shell if `hub_release.py` already supplies the required primitive.

### Step 2: Observe red for the missing remote-revision/caller guarantees

```bash
python3 -m unittest discover -s tests -p 'test_hub_release.py' -v
bash tests/test_hub_update_check.sh
```

### Step 3: Canonicalize callers

Make existing Hub install/update callers use the content-addressed preview/apply path for an existing Hub.

When downloading a remote source:

1. resolve the requested branch/tag to one commit SHA;
2. fetch that exact revision;
3. preview from it;
4. apply from the same local source/revision after confirmation.

Do not let preview use `main` and apply re-resolve `main` later.

Keep create-if-missing semantics for user memory and existing rollback behavior.

### Step 4: Remove pipe-to-shell guidance

Replace active `curl ... | bash` examples with clone/download-then-run or local-script instructions.

### Step 5: Green

```bash
python3 -m unittest discover -s tests -p 'test_hub_release.py' -v
bash tests/test_hub_update_check.sh
python3 -m unittest discover -s tests -p 'test_live_hub_merge.py' -v
bash scripts/hub-smoke-test.sh
```

### Step 6: Commit

```bash
git add scripts tests README.md docs getting-started
git commit -m "refactor: use one content-addressed hub release path"
```

---

## Task 8 — Final consistency, knowledge safeguards, and documentation

**Files:**
- Modify: `scripts/check-consistency.sh`
- Modify: `hub-template/ai/architecture.md`
- Modify: `hub-template/AGENTS.md`, `hub-template/CLAUDE.md` only if needed for the final Hub-only wording
- Modify active docs affected by prior tasks
- Modify architecture-project context/decisions/changelog only if the normal Hub task-finish workflow requires it

### Step 1: Add final consistency assertions

Require:

- `hub-template/` is the only distributable architecture template;
- every Hub skill referenced by active Hub entry/routing exists;
- every `hub-workflows` resource referenced by core exists;
- workflow action references are covered by the proposal action schema;
- new `read-compact-task-index.py` is included in the Hub release manifest;
- no active install/update docs depend on `template/`;
- `hub-knowledge-enable`, `hub-knowledge-capture`, and `hub-knowledge-review` still exist;
- knowledge is described as optional/on-demand, not default context.

Exclude historical `docs/superpowers/**` and `docs/audits/**` from assertions intended only for active product documentation.

### Step 2: Observe red where any final invariant is not yet represented

```bash
bash scripts/check-consistency.sh
```

### Step 3: Align Hub architecture docs

Document the final source-of-truth model:

- shared workflows: Hub;
- project paths/identity: registry;
- project task memory: current/paused/future;
- project orientation: project-context;
- durable decisions: decisions;
- semantic result history: changelog;
- detailed reusable references: optional knowledge;
- exact file/code history: Git.

Do not reintroduce standalone wording as a fallback.

### Step 4: Green

```bash
bash scripts/check-consistency.sh
bash scripts/hub-smoke-test.sh
bash scripts/architecture-test.sh
```

### Step 5: Commit

```bash
git add scripts/check-consistency.sh hub-template README.md docs getting-started ai
git commit -m "docs: align architecture around hub-only source of truth"
```

---

## Task 9 — Final acceptance and measured context check

No new feature work in this task unless a failing acceptance test exposes a regression caused by Tasks 1–8.

### Step 1: Run the full architecture-focused suite

```bash
bash scripts/check-consistency.sh
bash scripts/hub-smoke-test.sh
bash scripts/architecture-test.sh
bash scripts/assistant-workflows-test.sh
python3 -m unittest discover -s tests -v
(
  cd calendar-policy
  python3 -m pytest -q
)
```

If the repository contains additional architecture-owned smoke tests that are safe and do not execute registered application suites, run them and record them. Do not expand into app-specific tests.

### Step 2: Verify retired standalone state

Record:

```bash
test ! -d template
git grep -nE 'standalone architecture|--mode standalone|template/' -- \
  ':!docs/superpowers/**' ':!docs/audits/**' ':!CHANGELOG.md' || true
```

Any remaining active hit must be explained as a migration-only retirement message or removed.

### Step 3: Measure context improvement

Record before/after byte sizes where the before size is available from Git history:

```bash
wc -c hub-template/ai/skills/hub-workflows/SKILL.md
```

Run the compact index against a disposable fixture or the confirmed Hub scope and compare its output size with the total bytes of the three canonical task files used to generate it. Do not copy private task contents into the audit; record only byte counts and ratio.

Acceptance is a clear material reduction, not a fixed token target.

### Step 4: Final diff review

Review:

```bash
git status --short
git diff --stat
git diff
```

Confirm:

- no unrelated files changed;
- no project memory/knowledge was accidentally deleted;
- no Hub security or confirmation gate was weakened;
- no second update engine was introduced;
- no active standalone installation path remains.

### Step 5: Finish progress record

Append final test results, final commits, measured context reduction, and any explicit environment-only limitation to `docs/audits/2026-09-11-hub-only-audit-fixes-progress.md`.

Commit only this progress update if it changed after the last implementation commit:

```bash
git add docs/audits/2026-09-11-hub-only-audit-fixes-progress.md
git commit -m "docs: record hub-only audit fix verification"
```

## Completion gate

- [ ] Tasks 1–8 have focused red/green evidence.
- [ ] Final architecture-focused suite passes.
- [ ] Standalone cannot be installed or updated.
- [ ] `template/` is retired from active distribution.
- [ ] Evening review filters accepted/rejected friction.
- [ ] Learning lifecycle and proposal action schema agree.
- [ ] `read_project_records()` exists and the broken aggregate CLI path works.
- [ ] Personal-assistant discovery uses a compact task index first.
- [ ] `hub-workflows` uses scenario resources for progressive disclosure.
- [ ] Snapshot creation is collision-safe.
- [ ] Hub release/update uses one content-addressed path and one source revision per preview/apply cycle.
- [ ] Knowledge skills remain optional and available.
- [ ] No unrelated registered-project application code was tested or modified.

## Explicitly unnecessary extra checks

Do **not** add these just for this refactor:

- application test suites from the user's projects;
- an exact LLM tokenizer dependency such as `tiktoken`;
- a new CI platform;
- a database or background worker;
- broad security scanning unrelated to the changed architecture paths.

Optional only if already installed and cheap: `shellcheck` on changed shell files. Its absence does not block completion.