# Guarded Apple Calendar MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pinned local EventKit MCP that reads only user-selected calendars and applies one exact future-event change only after a fresh one-time confirmation.

**Architecture:** Vendor the exact `s-morgan-jeffries/apple-calendar-mcp` `v0.9.0` source snapshot, but expose only a hub-owned policy MCP. The policy layer owns the calendar allowlist, timezone validation, event identity checks, preview grants, recurrence scope, and unconditional past-delete denial; the raw upstream MCP is never configured in Codex.

**Tech Stack:** Python 3.10+, FastMCP, Pydantic, pytest, Swift/EventKit helper from the pinned upstream, Bash integration tests, Markdown hub architecture.

## Global Constraints

- Do not download, install, build, configure, or request macOS Calendar access until the user separately confirms the exact preflight.
- Use upstream tag `v0.9.0`; resolve and record its immutable commit before copying files.
- Never run a floating branch, `latest`, `uvx apple-calendar-mcp`, or an automatic updater.
- The raw upstream tools must never be exposed to Codex.
- The default calendar and all-calendars fallback are forbidden.
- Calendar contents must not be written to architecture, task memory, logs, fixtures, or Git.
- Every write requires a fresh preview and a separate explicit user confirmation.
- A preview is single-use, in-memory only, and expires after 600 seconds.
- Past deletion is always rejected; a past event cannot be moved into the future to bypass the rule.
- Recurring writes require explicit `this` or `future` scope and an occurrence date.
- All architecture, skill, installer, updater, and documentation edits require an exact `architecture-update` preview and `Replace this?` confirmation.
- Live hub installation, Codex MCP configuration, macOS permission, calendar allowlist selection, and each live write are separate confirmation gates.

---

### Task 0: Open the Calendar task safely

**Files:**
- Modify through workflow only: `ai/current-task.md`
- Modify through workflow only: `ai/future-tasks.md`
- Preserve: `ai/paused-tasks.md`

**Interfaces:**
- Consumes: confirmed project `ai-dev-architecture` and approved design `docs/superpowers/specs/2026-08-29-apple-calendar-mcp-design.md`.
- Produces: one active Calendar implementation task without losing the existing active personal-assistant specification task.

- [ ] **Step 1: Show the task-switch preview**

  Show the current task ID and exact proposed paused-task entry. Show the exact replacement current task with `Mode: architecture-update`, `Stage: planning`, the Calendar goal, relevant files, and Done criteria. Show the future-task status change from `idea` to `promoted`.

- [ ] **Step 2: Ask for task-switch confirmation**

  Ask for a confirmation that names the current task, paused target, new Calendar task, and future-task entry. General design approval is insufficient.

- [ ] **Step 3: Apply only through `hub-task-switch`**

  Run the project task-switch workflow after confirmation. Do not edit task memory directly outside that workflow.

- [ ] **Step 4: Verify memory**

  Run:

  ```bash
  sed -n '1,220p' ai/current-task.md
  sed -n '1,260p' ai/paused-tasks.md
  rg -n -A 28 'FT-20260826-002' ai/future-tasks.md
  ```

  Expected: the Calendar task is active, the earlier task is preserved once, and the future task is marked `promoted`.

---

### Task 1: Audit and vendor the exact upstream source

**Files:**
- Create after separate download confirmation: `vendor/apple-calendar-mcp/`
- Create: `vendor/apple-calendar-mcp/UPSTREAM.md`
- Create: `scripts/apple-calendar-upstream-test.sh`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Git tag `v0.9.0` from `https://github.com/s-morgan-jeffries/apple-calendar-mcp.git`.
- Produces: immutable reviewed source, `UPSTREAM_COMMIT`, checksum manifest, license, and a test that rejects drift.

- [ ] **Step 1: Show the download preflight and ask confirmation**

  Preview: repository URL, tag `v0.9.0`, temporary clone directory, destination `vendor/apple-calendar-mcp/`, expected Python and Swift build tools, and the fact that no code will run during download. Ask separately before network download.

- [ ] **Step 2: Fetch into a disposable directory without installation**

  Run only after confirmation:

  ```bash
  SAFE_TMP=$(mktemp -d)
  git clone --filter=blob:none --no-checkout https://github.com/s-morgan-jeffries/apple-calendar-mcp.git "$SAFE_TMP/upstream"
  git -C "$SAFE_TMP/upstream" checkout --detach v0.9.0
  git -C "$SAFE_TMP/upstream" rev-parse HEAD
  git -C "$SAFE_TMP/upstream" status --short
  ```

  Expected: one 40-character commit ID and a clean detached checkout. Record the exact ID in the preflight report before copying.

- [ ] **Step 3: Inspect before executing**

  Review `pyproject.toml`, `uv.lock`, `Makefile`, GitHub workflow files, Python entry points, Swift sources, shell scripts, subprocess calls, network calls, update code, telemetry, logging, filesystem access, and MCP tool registration. Search with:

  ```bash
  rg -n 'curl|wget|requests|urllib|socket|http|subprocess|os\.system|Popen|eval\(|exec\(|update|telemetry|analytics|open\(|write|unlink|remove|rmtree' "$SAFE_TMP/upstream"
  ```

  Expected: every match is classified in the audit report. Stop if unexplained network, updater, credential, broad filesystem, or destructive behavior remains.

- [ ] **Step 4: Write the failing integrity test**

  Create `scripts/apple-calendar-upstream-test.sh` that fails unless:

  ```bash
  test -f vendor/apple-calendar-mcp/LICENSE
  test -f vendor/apple-calendar-mcp/pyproject.toml
  test -f vendor/apple-calendar-mcp/uv.lock
  grep -Fqx 'Upstream-Tag: v0.9.0' vendor/apple-calendar-mcp/UPSTREAM.md
  grep -Eq '^Upstream-Commit: [0-9a-f]{40}$' vendor/apple-calendar-mcp/UPSTREAM.md
  grep -Fqx 'Auto-Update: disabled' vendor/apple-calendar-mcp/UPSTREAM.md
  sha256sum -c vendor/apple-calendar-mcp/SHA256SUMS
  ! rg -n 'latest|self-update|auto-update' vendor/apple-calendar-mcp/UPSTREAM.md
  ```

  On macOS, use `shasum -a 256 -c` if `sha256sum` is unavailable.

- [ ] **Step 5: Run the test and observe failure**

  Run: `bash scripts/apple-calendar-upstream-test.sh`

  Expected: FAIL because the reviewed snapshot and manifest do not exist.

- [ ] **Step 6: Copy the reviewed snapshot**

  Copy tracked files only, excluding `.git`, caches, build products, test calendars, and local configuration. Write `UPSTREAM.md` with the resolved commit, tag, source URL, audit date, license, manual update procedure, and `Auto-Update: disabled`. Generate checksums for every tracked vendored file.

- [ ] **Step 7: Verify integrity and upstream tests without Calendar access**

  Run the integrity test, dependency lock validation, upstream unit tests that do not touch EventKit, and `git diff --check`. Do not run live integration tests.

- [ ] **Step 8: Commit**

  Commit only the reviewed source snapshot, audit metadata, integrity test, and ignore rule:

  ```bash
  git add vendor/apple-calendar-mcp scripts/apple-calendar-upstream-test.sh .gitignore
  git commit -m "chore: vendor reviewed Apple Calendar MCP"
  ```

---

### Task 2: Define the fail-closed policy model

**Files:**
- Create: `calendar-policy/pyproject.toml`
- Create: `calendar-policy/src/hub_calendar_policy/__init__.py`
- Create: `calendar-policy/src/hub_calendar_policy/models.py`
- Create: `calendar-policy/src/hub_calendar_policy/policy.py`
- Create: `calendar-policy/tests/test_policy.py`

**Interfaces:**
- Consumes: normalized calendar and event dictionaries from an adapter.
- Produces: `CalendarPolicy`, `CalendarRef`, `EventRef`, `ChangeRequest`, `PolicyError`, and explicit allow/deny decisions.

- [ ] **Step 1: Write failing policy tests**

  Define tests for empty allowlist, unavailable calendar, read-only calendar, unauthorized calendar, invalid IANA timezone, allowed read, past-event detection at `end == now`, future deletion, and denial of moving a past event into the future.

  Core test shape:

  ```python
  def test_past_delete_is_always_denied(clock, policy, past_event):
      with pytest.raises(PolicyError, match="PAST_EVENT_DELETE_DENIED"):
          policy.authorize_delete(past_event, scope=None)

  def test_empty_allowlist_denies_read(policy):
      with pytest.raises(PolicyError, match="CALENDAR_NOT_ALLOWED"):
          policy.authorize_read("calendar-1", "Europe/Kirov")
  ```

- [ ] **Step 2: Run tests and observe failure**

  Run: `uv run --project calendar-policy pytest calendar-policy/tests/test_policy.py -v`

  Expected: FAIL because the package does not exist.

- [ ] **Step 3: Implement strict models**

  Use frozen Pydantic models. Require non-empty IDs, timezone-aware datetimes, IANA timezone names from `zoneinfo.ZoneInfo`, `end > start`, explicit calendar ID, and recurrence scope `this | future | null`.

- [ ] **Step 4: Implement minimal policy**

  `CalendarPolicy` loads only a supplied set of IDs. It has no default calendar and no wildcard. Treat an event as past when `event.end.astimezone(calendar_zone) <= now.astimezone(calendar_zone)`. Deny delete for past events. Deny start/end or recurrence changes when the original event is past.

- [ ] **Step 5: Run tests and commit**

  Run the policy tests and `git diff --check`; expect PASS. Commit:

  ```bash
  git add calendar-policy
  git commit -m "feat: add fail-closed Calendar policy"
  ```

---

### Task 3: Add single-use preview grants

**Files:**
- Create: `calendar-policy/src/hub_calendar_policy/preview.py`
- Create: `calendar-policy/tests/test_preview.py`

**Interfaces:**
- Consumes: canonical `ChangeRequest`, current event fingerprint, injected clock, and cryptographic random source.
- Produces: `PreviewGrantStore.issue()`, `cancel()`, and `consume()`.

- [ ] **Step 1: Write failing preview tests**

  Test exact payload binding, 600-second expiry, cancellation, replay denial, server restart loss, source fingerprint mismatch, and two previews never authorizing each other.

  ```python
  def test_preview_is_single_use(store, request):
      grant = store.issue(request, source_fingerprint="before")
      store.consume(grant.id, request, source_fingerprint="before")
      with pytest.raises(PreviewError, match="PREVIEW_ALREADY_USED"):
          store.consume(grant.id, request, source_fingerprint="before")
  ```

- [ ] **Step 2: Run and observe failure**

  Run: `uv run --project calendar-policy pytest calendar-policy/tests/test_preview.py -v`

  Expected: FAIL because `PreviewGrantStore` is missing.

- [ ] **Step 3: Implement minimal in-memory grants**

  Generate IDs with `secrets.token_urlsafe(32)`. Hash canonical JSON with SHA-256. Store expiry, payload hash, source fingerprint, and state in memory. Mark a grant used before returning success so a failed duplicate call cannot replay it. Never serialize grants to disk or logs.

- [ ] **Step 4: Run tests and commit**

  Run preview and policy tests; expect PASS. Commit:

  ```bash
  git add calendar-policy
  git commit -m "feat: add one-time Calendar previews"
  ```

---

### Task 4: Expose only guarded Calendar tools

**Files:**
- Create: `calendar-policy/src/hub_calendar_policy/backend.py`
- Create: `calendar-policy/src/hub_calendar_policy/server.py`
- Create: `calendar-policy/tests/fake_backend.py`
- Create: `calendar-policy/tests/test_server.py`
- Create: `scripts/apple-calendar-policy-test.sh`

**Interfaces:**
- Consumes: vendored upstream implementation through `CalendarBackend`.
- Produces only: `calendar_status`, `list_calendar_metadata`, `read_events`, `find_free_slots`, `preview_change`, `cancel_preview`, and `apply_change`.

- [ ] **Step 1: Write failing tool-surface tests**

  Assert the server exposes exactly the seven safe tools. Assert it does not expose upstream `create_calendar`, `delete_calendar`, `create_events`, `update_events`, or `delete_events`. Assert empty allowlist permits only status and metadata listing.

- [ ] **Step 2: Write failing behavior tests**

  Cover the required user cases: permission denied, unavailable calendar, wrong timezone, read-only behavior, create after confirmation, update after confirmation, past delete rejection, future delete after confirmation, recurring `this`, recurring `future`, and user cancellation.

- [ ] **Step 3: Run and observe failure**

  Run: `bash scripts/apple-calendar-policy-test.sh`

  Expected: FAIL because the guarded server is absent.

- [ ] **Step 4: Implement the backend boundary**

  Define an async `CalendarBackend` protocol for metadata, event reads, free-time reads, create, update, and delete. Add one adapter that calls the vendored upstream internally. Do not start or register the upstream MCP as a second client-visible server.

- [ ] **Step 5: Implement guarded tools**

  `list_calendar_metadata` returns ID, name, source, and writable only. `read_events` and `find_free_slots` require explicit allowed IDs and timezone and include `source: Apple Calendar / EventKit` plus timezone in every response. `preview_change` rereads existing events and returns the complete preview. `apply_change` consumes one grant, rereads and fingerprints again, then calls exactly one backend write.

- [ ] **Step 6: Add log redaction**

  Logs may contain operation type, result code, calendar ID hash, and duration. They must not contain calendar names, event IDs, titles, notes, locations, URLs, attendees, dates, preview payloads, or tokens.

- [ ] **Step 7: Run tests and commit**

  Run policy tests, tool-surface tests, the shell contract test, upstream unit tests, and `git diff --check`. Commit:

  ```bash
  git add calendar-policy scripts/apple-calendar-policy-test.sh
  git commit -m "feat: expose guarded Apple Calendar tools"
  ```

---

### Task 5: Apply hub rules through `architecture-update`

**Files:**
- Create: `hub-template/ai/skills/hub-calendar/SKILL.md`
- Modify: `hub-template/AGENTS.md`
- Modify: `hub-template/CLAUDE.md`
- Modify: `hub-template/ai/architecture.md`
- Modify: `hub-template/ai/skills/hub-workflows/SKILL.md`
- Modify: `scripts/install-hub.sh`
- Modify: `scripts/update-installed-hub.sh`
- Modify: `scripts/check-consistency.sh`
- Modify: `scripts/hub-smoke-test.sh`
- Modify: `docs/install.md`
- Modify: `docs/uninstall.md`

**Interfaces:**
- Consumes: guarded MCP tool contract from Task 4.
- Produces: hub routing, confirmation, install/update preservation, and documentation rules.

- [ ] **Step 1: Add failing architecture checks**

  Require the literal `hub-calendar` skill, selected-calendar allowlist, source/timezone output, raw-upstream prohibition, one-preview-one-confirmation rule, past-delete denial, recurrence scope, no background work, no secrets/content persistence, pinned local source, and manual updates.

- [ ] **Step 2: Run checks and observe failure**

  Run `bash scripts/check-consistency.sh` and `bash scripts/hub-smoke-test.sh`.

  Expected: FAIL because the Calendar skill and rules are absent.

- [ ] **Step 3: Show exact architecture-update preview**

  Show current Calendar wording, exact replacement wording, full new skill, every affected file, and token impact:

  - `AGENTS.md` / `CLAUDE.md`: short always-loaded route only;
  - `ai/architecture.md`: durable overview;
  - `hub-calendar/SKILL.md`: detailed procedure loaded only for Calendar work;
  - installer, updater, tests, and docs: no model-token impact during normal work.

  Ask exactly: `Replace this?`

- [ ] **Step 4: Apply only after confirmation**

  Add `hub-calendar`; make `hub-workflows` call it only for read context and proposal generation. It must never convert a task into an event automatically. Install/update must copy the policy MCP and skill while preserving the ignored allowlist.

- [ ] **Step 5: Mutation-test safety checks**

  Break each critical rule one at a time—raw tool exposure, wildcard calendar, missing timezone, reusable preview, past delete, implicit recurrence scope, and floating upstream version—observe failure, restore, and rerun.

- [ ] **Step 6: Verify and commit**

  Run:

  ```bash
  bash scripts/apple-calendar-upstream-test.sh
  bash scripts/apple-calendar-policy-test.sh
  bash scripts/check-consistency.sh
  bash scripts/hub-smoke-test.sh
  git diff --check
  ```

  Expected: all PASS. Commit:

  ```bash
  git add hub-template scripts docs
  git commit -m "feat: add guarded hub Calendar workflow"
  ```

---

### Task 6: Prepare a live-hub installation preview

**Files:**
- Proposed create: `/Users/zykovsrg/Documents/vibecode/_ai-hub/tools/apple-calendar-policy/`
- Proposed create: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/skills/hub-calendar/SKILL.md`
- Proposed modify: `/Users/zykovsrg/Documents/vibecode/_ai-hub/AGENTS.md`
- Proposed modify: `/Users/zykovsrg/Documents/vibecode/_ai-hub/CLAUDE.md`
- Proposed modify: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/architecture.md`
- Proposed modify: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/skills/hub-workflows/SKILL.md`
- Proposed ignored runtime file: `/Users/zykovsrg/Documents/vibecode/_ai-hub/.local/apple-calendar/allowlist.json`
- Proposed external change: Codex MCP configuration resolved from official Codex documentation at execution time.

**Interfaces:**
- Consumes: verified source implementation.
- Produces: exact installation diff with an empty allowlist; does not request Calendar access.

- [ ] **Step 1: Run source verification**

  Run every Task 5 command and inspect `git status --short`. Stop on any failure or unrelated change.

- [ ] **Step 2: Resolve the current official Codex MCP configuration format**

  Use official OpenAI documentation. Read the existing configuration only after explicit permission if it is outside the confirmed project. Do not guess or overwrite unrelated MCP entries.

- [ ] **Step 3: Show the exact live-hub and Codex preview**

  Show every copied/modified path, exact MCP command pointing to the local policy server, empty allowlist contents, required macOS permission, Xcode Command Line Tools requirement, tests, risks, and disable sequence.

- [ ] **Step 4: Ask separate installation confirmation**

  This confirmation authorizes only local file installation and Codex configuration. It does not authorize launching the MCP, requesting Calendar permission, reading calendar metadata, selecting calendars, or reading/writing events.

---

### Task 7: Install, grant permission, and select calendars through separate gates

**Files:**
- Modify only after installation confirmation: exact live-hub and Codex files previewed in Task 6.
- Modify only after calendar-selection confirmation: `/Users/zykovsrg/Documents/vibecode/_ai-hub/.local/apple-calendar/allowlist.json`

**Interfaces:**
- Consumes: confirmed install preview and later confirmed calendar IDs.
- Produces: working guarded MCP restricted by its own allowlist.

- [ ] **Step 1: Install with empty allowlist**

  Apply only the confirmed Task 6 diff. Run mock tests. Confirm no Calendar access request occurred.

- [ ] **Step 2: Show the permission request preview**

  Explain that macOS Full Calendar Access is system-wide across calendars, name the responsible process shown by macOS, and show how to revoke it. Ask separately before the first EventKit call.

- [ ] **Step 3: Request permission and list metadata only**

  After confirmation, call `calendar_status`, then `list_calendar_metadata`. Do not call event or free-time tools. Show IDs, names, sources, and writable status.

- [ ] **Step 4: Ask the user to select exact calendar IDs**

  Do not infer selection from names. Reject duplicate or missing IDs. Show the exact allowlist file content without event data and ask for confirmation.

- [ ] **Step 5: Apply the allowlist and run read acceptance tests**

  After confirmation, write only the selected IDs. Test permission absence, unauthorized calendar, timezone, selected-calendar event reads, and free slots. Show source and timezone. Confirm no write backend call occurred.

- [ ] **Step 6: Run write acceptance tests only in a dedicated test calendar**

  Ask the user to choose or create a dedicated writable test calendar. Every create, update, recurrence operation, cancellation, future delete, and cleanup gets its own preview and confirmation. Never use an existing personal calendar for test writes.

- [ ] **Step 7: Final verification**

  Run source tests, live mock tests, read acceptance tests, guarded write acceptance tests, consistency checks, smoke tests, `git diff --check`, and status checks. Show the final diff and list every changed file. Confirm that no calendar content entered Git or architecture files.

## Rollback

Stop safely by clearing the allowlist, disabling the policy MCP entry, restarting Codex, and revoking Calendar access in macOS System Settings. Preserve the vendored source and checksums for audit unless the user separately confirms deletion. Never attempt an automatic Calendar rollback; a compensating update or future-event recreation requires its own preview and confirmation.
