# Task Records and Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans`. Execute T01–T05 after R06. Apply the global constraints and exact roots in [the complete plan](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-complete.md).

**Goal:** Prevent invisible tasks, normalize dates, preserve original meaning, and route every calendar-relevant change through one approved task/event preview.
**Architecture:** One task reader serves generated views, reverse sync and compact context. Canonical Markdown stays authoritative. The existing guarded Calendar service remains the only calendar writer; the workflow coordinates the confirmed task change.
**Tech Stack:** Existing Bash/jq adapters plus a standard-library Python reader and tests.

## T01 — Define and implement one task reader (Terra)

**Create:** `scripts/task_records.py`, `tests/test_task_records.py`, `hub-template/ai/skills/hub-task-intake/resources/task-record-format.md`.
**Read:** current `future_records`, `paused_records`, `current_task_id` and `source_record` functions. Keep the existing task ID grammar and pair identity `(project_id, task_id)`.
**Interface:** `python3 scripts/task_records.py read --project-id ID --file PATH --kind current|future|paused --format json|tsv`. File may be a validated temporary copy; kind is explicit, never inferred from temporary filename. Return code 0 means completely understood source, 2 means malformed record, 3 means source contains unclassified candidate records. Diagnostics go to stderr and JSON `diagnostics`; no partial TSV on nonzero.

JSON v1 contains `project_id`, `kind`, `source_sha256`, `records`, `diagnostics`. Each record has `task_id`, `title`, `status`, `due` (ISO date or null), `schedule` (raw existing timed field or null), `start_line`, `end_line`; diagnostics have code, line and a safe explanation. The adapter may project records to its old TSV order; JSON is the complete interface.

- [ ] Add fixture strings for uppercase/lowercase Due, equal duplicate dates, conflicting dates, leap day, legacy IDs, same ID in two projects, duplicate ID within one file, `open`, `complete`, missing IDs, bullet-style paused fields and non-task headings. Use synthetic text.
- [ ] Implement exact date behavior with this pure function and unit assertions:

```python
import re
from datetime import date

def read_due(lines):
    values = []
    for line in lines:
        match = re.fullmatch(r"\s*(?:Due|due):\s*(.*?)\s*", line)
        if match:
            value = match.group(1)
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("invalid_due")
            date.fromisoformat(value)
            values.append(value)
    if len(set(values)) > 1:
        raise ValueError("conflicting_due")
    return values[0] if values else None

def test_due_case(self):
    self.assertEqual(read_due(["Due: 2026-09-10"]), "2026-09-10")
    self.assertEqual(read_due(["due: 2026-09-10"]), "2026-09-10")
    with self.assertRaises(ValueError):
        read_due(["Due: 2026-09-10", "due: 2026-09-11"])
    with self.assertRaises(ValueError):
        read_due(["Due: 2026-02-30"])
```

- [ ] Parse only top-level task fields, excluding fenced code, indented historical copies and explicitly marked template/schema blocks. Future task boundaries are third-level headings with recognized task IDs; paused records support current date headings and legacy task-ID headings. Normalize bullet-prefixed field labels only within a recognized task record, preserving the body.
- [ ] Read legacy `open` as `ready` with diagnostic `legacy-status` (warning, not failure); `complete` as `done`. Empty slot `none` can map to `empty` only if there is no concrete goal or task record. Missing/unknown statuses with real task content are errors; do not invent `done`. `done (comment)` is historical metadata requiring classification, not a new active task.
- [ ] For an unrecognized nonempty task section/list outside rules/template/history sections, emit `unclassified-section` with line range. Mechanical parsing flags the section for T04; it does not claim that every bullet is actionable. Keep existing source intact.
- [ ] Write the format resource: writer uses `Task ID:`, `Status:`, `Due:` and existing timed schedule field; future statuses `idea|ready|blocked|promoted|done|dropped`, current statuses as currently supported; migration aliases are read compatibility only. Empty slots need no fabricated date/ID. Every scheduled record must be parseable as a real date; timed fields also require valid hour/minute and end after start.
- [ ] Run `python3 -m unittest discover -s tests -p test_task_records.py -v`; commit `feat: centralize task record parsing`.

## T02 — Wire both Obsidian directions to the reader (Terra)

**Modify:** `scripts/generate-obsidian-projects-kanban.sh`, `scripts/obsidian-task-sync.sh`, `scripts/obsidian-projects-kanban-test.sh`, `scripts/obsidian-task-sync-test.sh`, `release/hub-files.json`.
**Consumes:** T01 JSON/TSV contract. **Produces:** existing board/manifest interface remains v4; this task does not redefine board identity.

- [ ] Extend existing shell fixtures: identical future tasks with `Due:` and `due:` must generate the same card date; after set_due there is exactly one `Due:` field. Conflicting dates must leave board and source unchanged. Add paused bullet-fields and future `open` fixture; explicit diagnostics for a free-form heading instead of silently hiding it.
- [ ] Replace local record parsing in generator and sync with T01 calls; check subprocess exit before generating or writing. Do not bury reader failure in a pipeline/process substitution where the exit status is lost. Use a captured temporary JSON result and check return code before projection.
- [ ] Preserve current filter semantics: `promoted`, `done`, `dropped` are not new future work; current/paused rendering retains applicable statuses. A failure in a selected project stops its refresh and leaves prior boards intact, with a clear project/line diagnostic. Unrelated project selection remains isolated.
- [ ] Rewrite due fields only in the chosen record, removing both exact aliases and adding a single canonical field. Pure transformation for an already isolated record body:

```python
def replace_due(body, value):
    if value is not None:
        read_due(["Due: " + value])
    kept = [line for line in body.splitlines()
            if not re.fullmatch(r"\s*(?:Due|due):.*", line)]
    result = "\n".join(kept).rstrip() + "\n"
    return result + ("\nDue: " + value + "\n" if value else "")
```

Expose this as `task_records.py set-due --file PATH --kind KIND --project-id ID --task-id ID --due DATE` (or `--clear`) writing transformed content to stdout only. Sync stages that output into its existing temporary file. Preserve code blocks/history by using the parsed top-level field spans, not applying this illustrative body operation to the entire source file.

- [ ] Change create/promote writers to `Due:`. Update trusted refresh fixtures to canonical spelling while retaining dedicated lowercase compatibility fixtures. Keep source-hash, manifest, pending manual edit, watcher lock and rollback protections.
- [ ] Run reader tests, both Obsidian test suites and watcher test suites; commit `fix: preserve task dates across Obsidian sync`.

## T03 — Close the calendar bypass and support the joint workflow (Terra)

**Modify:** `scripts/obsidian-task-sync.sh`, `scripts/obsidian-task-sync-test.sh`, `hub-template/ai/skills/hub-task-intake/SKILL.md`, `hub-task-switch/SKILL.md`, `hub-task-finish/SKILL.md`, `hub-calendar/SKILL.md`, `hub-template/ai/architecture.md`.
**Create:** `hub-template/ai/skills/hub-calendar/resources/joint-task-change.md`, `tests/fixtures/joint-task-change.md`.

Decide calendar relevance using validated source records plus proposed after-state, not a user-supplied `calendar=false` flag. Relevant: set/clear deadline; create/promote a dated task; change title/status/schedule of a task with an associated or expected event; replace a dated current task. Until exact event mapping is available, conservative routing to joint preview is correct. Undated changes keep the existing direct path.

- [ ] Add a shell regression: scan a dated change; direct `apply` exits 3 with `calendar-confirmation-required`, leaving every canonical file, proposal and board hash unchanged. Add an undated rename that still applies successfully. A mixed batch routes as a whole, avoiding half-application.
- [ ] Insert the guard in `apply()` after source/proposal/hash validation, before `apply_operations_to_temporary_files`. Also expose the derived `requires_calendar_confirmation` summary at scan/preview. Do not trust it during apply; recompute from source.

```text
verify current source and exact proposal hash
derive before/after record dates, titles, states and event references
if any operation is calendar-relevant:
    report joint-task-change workflow, proposal hash and affected task IDs
    exit 3 before staging or modifying anything
otherwise continue the existing file-only apply
```

- [ ] Install this exact workflow behavior in `joint-task-change.md`:

```text
1. Read the selected pending proposal and validate its source/board hashes. Prepare the complete task diff without writing it.
2. Use only the guarded Calendar tools to identify the exact event. If identity is ambiguous, stop this change and state the competing candidates. Never infer identity from title alone when several matches exist.
3. Build the event preview with exact calendar, title, dates, timezone, event ID and recurrence scope. Show it together with the task diff as one confirmation.
4. After confirmation, recheck source hashes and preview validity. Save a recoverable local journal under the existing vault .ai-architecture-sync directory with proposal digest, task identities and operation phase; never store preview grants or credentials.
5. Apply the guarded calendar change once. Record returned event ID and phase calendar-applied. If the result is uncertain, read the event state and reconcile before retrying; do not blindly create another event.
6. Recheck source hashes, then apply exactly the shown canonical task diff using normal file editing. If source changed, preserve it and report the already-applied event as partial completion. Never silently undo somebody else's event or file change.
7. Verify the task after-state and event after-state, refresh the generated board through the trusted direction, and mark the journal complete. If a manual board conflict remains, retain the pending proposal and report it. No overwrite of an unrelated manual edit.
8. A retry reads the existing journal: after calendar-applied it attempts only the remaining file/refresh steps. Missing/uncertain journal evidence requires reconciliation. Any changed desired event or task diff gets a new combined preview.
```

The journal is recovery metadata under the existing ignored sync runtime, not a new task store or a Calendar authorization token. This plan deliberately uses the existing agent-mediated guarded workflow; it does not invent a parallel Calendar writer or claim a multi-system transaction is atomic.

- [ ] Extend `dismiss` or add `complete-joint --project-id ID --confirm-proposal SHA` so it can clear only a proposal whose canonical after-state matches every requested operation. It checks the digest and task after-state; the workflow remains responsible for actual Calendar verification. It must not accept a fake receipt as authority for Calendar changes. If requested after-state differs, leave proposal present and return nonzero.
- [ ] Run synthetic workflow scenarios: declined combined preview; Calendar denied; stale source before event apply; event applied/source write failed; unknown event response; retry without duplicate create; board refresh conflict; past task closure leaves past event unchanged. Record the model's chosen actions and compare with each expected outcome. Automated shell tests verify file guards; semantic scenario review verifies the procedure.
- [ ] Run Obsidian sync/watch tests and existing calendar-policy tests. Commit `fix: route dated task edits through joint calendar approval`.

## T04 — Normalize all registered project records without rewriting meaning (Terra; exact edits may use Luna)

**Read:** current `HUB_ROOT/ai/project-registry.md`; three task files per registered project. Read decisions/changelog only when needed to verify a specific completion or owner.
**Modify:** only selected project `ai/current-task.md`, `future-tasks.md`, `paused-tasks.md`, and relevant local `changelog.md`/`decisions.md`.
**Create:** per-project `ai/migrations/2026-09-09-task-format.md` and an architecture-level summary `docs/audits/2026-09-09-task-normalization.md`. Private details remain in the project; summary contains IDs/counts/status only.

- [ ] Enumerate current registry IDs, including archived projects without changing their status. Run T01 on each source; inventory recognized, intentionally historical and unclassified ranges separately. Refresh the old 57-project count rather than assuming it is still current.
- [ ] For one project at a time, map every source record/range to keep, canonicalize, link completion, assign missing ID, or needs-user-meaning. A new missing ID uses `TASK-<registered-id>-<actual migration YYYYMMDD>-NNN`, next unused ordinal; keep existing IDs. Uncertain source is preserved verbatim and visibly listed; never silently mark it completed.
- [ ] Normalize deterministic aliases/dates only when values agree. Preserve timed schedules and their meaning. Do not create calendar events merely because a legacy field spelling changed. A true date/status change uses T03.
- [ ] Verify `promoted` by linked current/paused/changelog evidence. Already implemented architecture features get a completion reference; partial rollout remains an open rollout task. App completion is not inferred from filenames or a passing architecture check.
- [ ] For cross-project duplicates designate the explicit owner from task context; leave references from other projects. When evidence cannot distinguish ownership, record one concise user question and continue other projects. Approval of migration does not choose a business owner that was never stated.
- [ ] Compare each original block against its mapped after-state. All blocks have dispositions; no task body disappears. Re-run reader and project-scoped generated preview, preserving user board edits. Record meaningful count differences (historical items are not missing work).
- [ ] Commit each selected project's exact changed memory files through its repository; skip no-Git projects with an explicit local-only record rather than initializing a repository unexpectedly. Do not group 57 projects into one giant commit. Commit message `chore: normalize task memory without changing scope`.

**Completion:** every registry project has a status in the normalization summary; unresolved meaning is reported as unresolved rather than claiming full normalization. Such questions block only their rows, not independent code tasks.

## T05 — Compact task context without a second source of truth (Terra)

**Modify:** `scripts/task_records.py`, `scripts/assistant-workflows.sh`, `hub-template/ai/skills/hub-workflows/SKILL.md`, `tests/test_task_records.py`, `scripts/assistant-workflows-test.sh`.
**Runtime:** optional cache `HUB_ROOT/ai/tmp/task-index.json`; never stored under project cards or used before routing permission.

- [ ] Add `summary --hub PATH --scope PATH --date YYYY-MM-DD` to the reader. Scope file contains already authorized registry IDs. Return compact records of active/ready/blocked/waiting/paused work, relevant deadlines and source references; ideas remain available via explicit lookup. Include source hashes, registry hash and unclassified diagnostics. Do not pre-read excluded project content.
- [ ] Cache validity is exact equality of registry/scope/source digests; no TTL-only freshness. If a source changes, rebuild before reading the cached records. The cache may be discarded at any time; original Markdown is sufficient to regenerate it.

```python
def cache_is_current(cached, registry_sha, scope_sha, source_shas):
    return (cached.get("registry_sha") == registry_sha
            and cached.get("scope_sha") == scope_sha
            and cached.get("source_shas") == source_shas)
```

- [ ] Teach the workflow to read compact summaries first and full text only for selected tasks or ambiguity. An invalid task source is reported, not cached as an empty project. Keep full-source semantic access for the approved scope, but do not require loading hundreds of KB for every small overview.
- [ ] Add tests: changed source invalidates; changed scope cannot expose another project; missing source gives error; cache deletion regenerates the same records; no absolute personal text in a cross-project diagnostic. Verify the recorder adapter's existing source-consent behavior still passes.
- [ ] Run reader and assistant-workflow tests; commit `perf: derive fresh compact task summaries`.
