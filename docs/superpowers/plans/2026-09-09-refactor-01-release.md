# Release Integrity and Learning Preservation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans`. Execute R01–R06 in order with the constraints in [the complete plan](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-complete.md).

**Goal:** Preserve live improvements in the distribution, make installation/update reviewable and recoverable, and fix snapshot/observation defects.
**Architecture:** Bash entry scripts retain their CLI. One standard-library release helper supplies a shared managed-file inventory, preview, apply and restore. Existing learning remains the owner of task/calendar observations.
**Tech Stack:** Bash 3.2, Python 3 standard library, Git; existing calendar build tools only in integration checks.

## R01 — Reconcile the distribution source (Terra)

**Modify:** `hub-template/ai/architecture.md`; `hub-template/ai/skills/hub-calendar/SKILL.md`, `hub-project-create/SKILL.md`, `hub-workflows/SKILL.md`, `hub-task-intake/SKILL.md`, `hub-task-switch/SKILL.md`, `hub-task-finish/SKILL.md`; `scripts/generate-obsidian-projects-kanban.sh`.
**Create from inspected live counterparts:** `hub-template/ai/skills/hub-goal-progress/SKILL.md`; `scripts/count-goal-progress.sh`, `scripts/check-workflow-memory.sh`, `scripts/snapshot-calendar.sh`; `tests/test-count-goal-progress.sh`, `tests/test-check-workflow-memory.sh`, `tests/test-snapshot-calendar.sh`.
**Create:** `docs/audits/2026-09-09-release-preservation-manifest.md`, `docs/audits/2026-09-09-refactor-progress.md`.
**Read live:** the same relative paths beneath `HUB_ROOT`; the three canonical learning/goal files only to inspect their schema, not to distribute actual entries.

- [ ] Record both repository heads and dirty paths. Refresh the readonly updater preview against the current working source. Enumerate all `HUB_ROOT/ai/skills/` resources, not just SKILL.md, and compare against `hub-template/ai/skills/`.
- [ ] Write manifest rows `live_path, source_path, before_hashes, preserve|merge|retire, reason, test`. Additional file differences discovered by enumeration get individual rows and the same handling; do not ignore them because they were not named above.
- [ ] Carry forward live goal progress, learner, project-selection guard, calendar naming/permissions and missing-board manifest support. For generator drift, preserve the branch that allows a newly registered board with no previous manifest entry only if that board does not already exist; keep validation for known boards.
- [ ] Create empty distribution files `hub-template/ai/goal-log.md`, `workflow-observations.md`, `workflow-context.md` using the live schemas with no personal entries. These are create-if-missing user data, never replace-on-update code.
- [ ] Keep current release version unchanged until the final release task. Reconcile content first. Do not translate or rewrite unrelated rules while merging.
- [ ] Run the copied three Bash test suites and `bash scripts/assistant-workflows-test.sh`. Review each preserved behavior against its live source and record known old defects as expected pending R04/R05 rather than altering tests to hide them.
- [ ] Commit `refactor: reconcile hub distribution with live behavior` and record R01.

**Acceptance:** every managed drift has a disposition; all six named live improvements exist in source; private observations/goal amounts were not copied into the release. This task actually merges the source, rather than returning an inventory for another Astra plan.

## R02 — Single release manifest and pure update decisions (Terra)

**Create:** `scripts/hub_release.py`, `tests/test_hub_release.py`, `release/hub-files.json`.
**Modify:** `scripts/update-installed-hub.sh`, `scripts/install-hub.sh`, `scripts/sync-calendar-policy.sh`.
**Interface:** `python3 scripts/hub_release.py build --source PATH` emits canonical JSON to stdout; `check --source PATH --manifest PATH` verifies it. No install side effect. Paths in the manifest are repository-relative source and hub-relative target.

Manifest v1:

```json
{"format":1,"files":[{"source":"hub-template/AGENTS.md","target":"AGENTS.md","sha256":"actual computed digest","mode":420,"policy":"managed"}],"remove":[],"ignore_lines":["/projects/","/.local/"]}
```

The digest is computed, never a literal placeholder in a built manifest. Include `hub-template/` files with explicit classification; shared skill resources are managed. User memory files are `create-if-missing`: existing `MEMORY_FILES`, three new empty learning/goal files, and card/archive scaffold. Root `.gitignore` is merged linewise, not replaced. `allowed-roots.md` on a fresh install is generated from the actual target root; never ship an absolute author's path.

Include architecture scripts referenced by shared workflows: registry/index/generator/sync, goal counter, snapshot validator and workflow-memory checker plus new runtime helpers introduced by later tasks. Include relevant installed tests. Include calendar-policy `src/`, source bridge files and `pyproject.toml` under `tools/apple-calendar-policy/`; exclude `.venv`, `__pycache__`, `.pyc`, built app and allowlist. `remove` only contains explicit formerly managed paths, never directory-wide mirroring.

- [ ] Write unit tests for the decision function below before implementing it. Hash values `old`, `new`, `mine` are test inputs, not real hashes. Tests: equal current/incoming → keep; unchanged installed baseline → replace; modified baseline → conflict; missing file → create; no baseline plus differing existing file → conflict; unmodified known retired file → remove; modified retired file → conflict.

```python
def decide(current, installed, incoming):
    if incoming is None:
        if current is None:
            return "keep"
        return "remove" if installed is not None and current == installed else "conflict"
    if current == incoming:
        return "keep"
    if current is None:
        return "create"
    if installed is not None and current == installed:
        return "replace"
    return "conflict"

def test_conflict_without_baseline(self):
    self.assertEqual(decide("mine", None, "new"), "conflict")
```

- [ ] Implement deterministic sorted manifest serialization (`json.dumps(..., sort_keys=True, separators=(",", ":"))`), SHA-256 for source bytes, permissions and duplicate-target rejection. Reject absolute targets, `..`, symlink components and target roots outside the selected hub. Test symlinked ancestors, not only the final file.
- [ ] Use this containment primitive for each file; additionally check each existing path component with `is_symlink()` before `resolve()` so a link resolving inside the root also fails:

```python
from pathlib import Path

def target_path(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("unsafe relative target")
    result = root.joinpath(rel)
    probe = root
    for part in rel.parts:
        probe = probe / part
        if probe.is_symlink():
            raise ValueError("symlink target component")
    result.resolve().relative_to(root.resolve())
    return result
```

- [ ] Add a test that changing a managed resource causes manifest verification failure, while changing fixture user memory does not. Empty create-if-missing templates must still have source integrity checks.
- [ ] Generate `release/hub-files.json` via the helper during implementation. Subsequent tasks regenerate it after changing managed files. Installer and updater both consume it; remove the duplicate hard-coded managed-file enumerators only once callers use the helper.
- [ ] Run `python3 -m unittest discover -s tests -p test_hub_release.py -v`; commit `feat: define content-verified hub releases`.

## R03 — Preview, recoverable apply, and first adoption (Terra)

**Modify:** R02's helper/tests, `scripts/update-installed-hub.sh`, `scripts/install-hub.sh`, `scripts/sync-calendar-policy.sh`, `scripts/calendar-policy-install-test.sh`, `scripts/hub-smoke-test.sh`.
**Create:** `scripts/hub-release-test.sh`.
**Runtime state, not shipped:** `.local/hub-release/installed.json`, `plans/<digest>.json`, `backups/<operation-id>/` beneath the target hub. No project/task data or calendar credentials in a release backup.

CLI contract for the helper:

```text
preview --source PATH --hub PATH
apply --source PATH --hub PATH --confirm-plan SHA256
restore --hub PATH --operation-id ID --confirm-plan SHA256
```

`preview` returns JSON containing manifest digest, each target's current digest/mode/existence, chosen operation, required ignore additions, build action, and plan digest. Preview may store only its noncanonical plan under `.local/hub-release/plans/`; `--check` remains purely readonly and returns 0 only for matching managed content, 1 for drift, 2 for error. Print a summary and exact file diffs without exposing preserved memory. If no baseline exists, report `first-adoption`; the exact reviewed plan may explicitly adopt current hashes as before-state. `--allow-dirty` never authorizes an unseen overwrite.

- [ ] Add fixtures with a managed file, missing managed file, user memory, symlink target, modified target, omitted ignore line and fake calendar build. Test rejected stale plan leaves all target bytes unchanged. A no-change preview must not build or write anything.
- [ ] Implement the transaction in this order:

```text
acquire exclusive hub-release lock (fail clearly if already held)
load saved plan; recompute source and current target hashes
require exact plan digest and no changed preconditions
stage all incoming files and merged ignore content outside target paths
build calendar bridge in staging; stop before replacing any file on build failure
back up each named changed target with bytes, mode and prior existence
replace staged targets one by one; record each applied operation durably
on filesystem error restore named targets from backups; keep journal if restore fails
write installed manifest and success receipt only after every replacement succeeds
release lock; return changed paths and operation ID
```

Use `os.replace()` for file replacement, a unique `tempfile.mkdtemp()` staging directory and an exclusive lock directory. On interrupted-run detection refuse a new apply until explicit restore/reconciliation. Restore only targets still matching this operation's after-state; if the user edited a target afterward, preserve it and report the conflict. Do not overwrite post-update user changes during rollback.

- [ ] Create allowlist only when absent, containing an empty ID list; never read existing values into logs. Include `/.local/` and `/projects/` additions in the plan and commit paths. Keep runtime allowlist/build environment outside backup/commit sets.
- [ ] Adapt `sync-calendar-policy.sh` to use the staged source and explicit managed paths, removing its broad live `rsync --delete` behavior. A direct sync call must use the same preview/apply contract, not an unguarded second writer.
- [ ] Keep shell flags compatible: `--check` uses content check; default/`--dry-run` shows the plan; `--apply --confirm-plan SHA256` applies the displayed plan. `--commit` stages exact returned managed paths including `.gitignore`, and only those paths. Missing confirmation displays the command, writes no code.
- [ ] Add failure injection at staging/build, second replace and receipt write in tests. Verify byte-for-byte restore and preserved user memory. Test concurrent apply refusal, stale source, stale destination, first adoption, modified retirement and repeat apply.
- [ ] Run helper tests, `bash scripts/hub-release-test.sh`, `bash scripts/calendar-policy-install-test.sh`, `bash scripts/hub-smoke-test.sh`. Commit `fix: make hub updates previewed and recoverable`.

## R04 — Unique snapshots and real calendar dates (Luna or Terra)

**Modify:** `scripts/snapshot-calendar.sh`, `scripts/check-workflow-memory.sh`, `tests/test-snapshot-calendar.sh`, `tests/test-check-workflow-memory.sh`.
**Create:** `scripts/lib/calendar-date.sh`; add it to release manifest.
**Modify callers:** `hub-template/ai/skills/hub-calendar/SKILL.md`, `hub-template/ai/skills/hub-workflows/SKILL.md`, `hub-template/ai/architecture.md`.

- [ ] Add tests: two snapshots with identical `--at` retain both contents; planning 2099 does not delete a freshly captured snapshot; actually old capture is pruned; legacy unknown-age file remains; invalid input creates/prunes nothing. Impossible dates `2026-02-30`, `2026-99-99` rejected; `2028-02-29` accepted.
- [ ] Define a Bash-sourceable date function used by all callers (macOS BSD date):

```bash
valid_calendar_date() {
  local value="$1" normalized
  [[ "$value" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || return 1
  normalized="$(TZ=UTC date -j -f '%Y-%m-%d %H:%M:%S' "$value 12:00:00" '+%F' 2>/dev/null)" || return 1
  [ "$normalized" = "$value" ]
}
```

- [ ] Preserve `--at` as described-day/time input. Validate all event input before pruning. New snapshot basename is `<described-day>-<HHMM>--captured-<epoch-seconds>--<random>.txt`; use `mktemp` with that prefix in the validated snapshot directory. Epoch comes from `date +%s`, not `--at`. Input is staged then moved to the allocated unique target. Reject directory symlinks.
- [ ] Add `--list --day YYYY-MM-DD`, listing absolute paths for both exact legacy `YYYY-MM-DD-HHMM.txt` and new names, deterministically by capture epoch then filename; legacy entries sort by their old minute time and are labeled legacy in documentation. The listing does not mutate files.
- [ ] Retention: only remove new-format captures with numeric epoch older than real `now - 14*86400`; retain legacy snapshots whose capture time is unknown. Do not prune pending friction files; R05 owns their lifecycle. Update every snapshot-reading instruction to use `--list --day` rather than assuming the old filename shape.
- [ ] In memory validator, after regex format check extract the first date and call `valid_calendar_date`; preserve existing schema-section exemption. Example assertion:

```bash
if valid_calendar_date 2026-02-30; then
  printf '%s\n' 'FAIL: impossible date accepted' >&2
  exit 1
fi
valid_calendar_date 2028-02-29
```

- [ ] Run the two test suites and `bash scripts/assistant-workflows-test.sh`; commit `fix: preserve snapshots and reject impossible dates`.

## R05 — Preserve pending observations and bound repeated learning context (Terra)

**Modify:** `hub-template/ai/skills/hub-workflows/SKILL.md`, `hub-template/ai/architecture.md`, `scripts/check-workflow-memory.sh`.
**Create:** `scripts/workflow-friction.py`, `tests/test_workflow_friction.py`, `hub-template/ai/skills/hub-workflows/resources/learning-lifecycle.md`.
**Runtime:** retain existing daily `.txt` observation sources. A sibling `<date>.state.json` contains only stable source IDs, line hashes and disposition `pending|accepted|rejected`. Canonical observation text remains in the existing journal. This is resumable source bookkeeping, not another learning journal.

- [ ] Test interruption before decision, partial acceptance, rejection, duplicated retry, changed source line, two identical lines at distinct positions, and retention. An old unresolved line survives. A source edited after preview cannot be consumed with its old digest.
- [ ] Define source IDs and allowed transitions:

```python
import hashlib

def observation_id(day, ordinal, text):
    raw = f"{day}\0{ordinal}\0{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def transition(old, decision):
    if decision not in {"accepted", "rejected"}:
        raise ValueError("explicit disposition required")
    if old == decision:
        return old
    if old != "pending":
        raise ValueError("conflicting disposition")
    return decision
```

- [ ] Implement `list --hub PATH --day DATE` returning pending IDs/lines and source digest; `resolve --hub PATH --day DATE --source-sha SHA --id ID --decision accepted|rejected` updates only bookkeeping after the workflow confirms disposition. Use an exclusive per-day lock and atomic state replacement. Reject unknown IDs and stale digest; preserve source `.txt`.
- [ ] Exact workflow rule to install in the resource:

```text
Read pending friction with workflow-friction.py list. Showing a proposal never consumes it. After acceptance, append the confirmed observation to the existing journal with a preceding HTML comment `source-id: ID`; check for that ID before any retry. Then resolve that ID as accepted. After explicit rejection resolve it as rejected without appending. If journal append fails, leave pending. If resolve fails after append, retry only resolve, using the existing journal source-id as evidence. Unresolved sources are never pruned. Do not read all prior journal entries in ordinary day/evening runs.
```

- [ ] Implement `prune --hub PATH` removing only source/state pairs with all entries resolved and state completion older than 14 real days; on unknown/malformed state retain and diagnose. Never let the snapshot script prune friction independently. Historical `.consumed.txt` has unknown disposition; report it for focused reconciliation, not automatic rejection or re-addition.
- [ ] Preserve maturation thresholds 3 episodes/2 in a week, but count distinct source IDs. Replace unbounded weekly full-journal loading with a bounded selected-input read: new dated observations plus references for a candidate being reconsidered; scan metadata locally, report remainder and do not claim the full journal reviewed. Existing entries without IDs remain readable and need a one-time stable line identity before counting duplicates.
- [ ] Preserve the 100-rule cap; day/evening load only applicable learned rules after a compact ID/topic listing. Do not alter preferences by silently shortening them. Mark a rule's effect untested until subsequent relevant observations exist. A follow-up is checked at an existing review, not a new automation.
- [ ] Run `python3 -m unittest discover -s tests -p test_workflow_friction.py -v`, validator tests and assistant workflow tests. Commit `fix: retain learning observations until disposition`.

## R06 — Reproducible safe architecture tests (Terra)

**Modify:** `scripts/apple-calendar-policy-test.sh`, `scripts/hub-smoke-test.sh`, `scripts/check-consistency.sh`, `docs/install.md`.
**Create:** `scripts/architecture-test.sh`.

- [ ] Update missing-environment output to give these exact project-relative setup commands and stop; do not auto-download on every test run:

```bash
python3.11 -m venv calendar-policy/.venv
calendar-policy/.venv/bin/python -m pip install -e calendar-policy 'pytest>=8.0,<9' 'pytest-asyncio>=1.0,<2'
```

The inspected `pyproject.toml` requires Python >=3.11 and declares these two test dependencies under `[dependency-groups].dev`; it has no `test` extra. An available newer Python 3 is acceptable after checking its version. Existing available environment is reused. Dependency installation is a one-time implementation setup action, not a hidden part of every test run.

- [ ] `architecture-test.sh` exposes `--unit`, `--integration`, `--all`. `--unit`: stdlib unittest discovery under `tests/` plus goal/snapshot/memory Bash tests. `--integration`: explicit architecture scripts — assistant workflows, Obsidian generator/sync/watch/legacy bridge, hub release, install, refresh-session-inventory, calendar-policy tests and bridge checksum/build. `--all` runs both. A child failure propagates nonzero and names the failed test.
- [ ] Use an explicit list, not `find every test in projects`. All write tests receive temporary roots. Any tests that invoke Keychain or app database operations are excluded. Do not swallow nonzero pipeline statuses.
- [ ] Keep useful contract checks when updating `check-consistency.sh`; its standalone-specific assertions are retired only in M05. Add a manifest verification call so changed shipped resources cannot be omitted from release generation.
- [ ] Run unit mode. Run integration mode in isolation; an unavailable system compiler/permission is reported with its exact failed check, never labeled an application defect. Commit `test: provide explicit safe architecture test profiles`.
