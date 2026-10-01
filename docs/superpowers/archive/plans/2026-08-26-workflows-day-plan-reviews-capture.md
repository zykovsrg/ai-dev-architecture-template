# Workflows: Day Plan, Reviews, and Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add proposal-only planning, review, and capture workflows with a stable JSON interface from Rolling Audio Recorder.

**Architecture:** `rar` exposes JSON for transcript jobs. A Bash guardrail validates JSON, scope, and paths only. `hub-workflows` performs semantic AI analysis and returns proposals, never writes.

**Tech Stack:** Swift 6, swift-argument-parser, XCTest, Bash, jq, Markdown.

## Global Constraints

- Canonical data stays in `ai/` and explicitly selected knowledge files.
- `rar --json` preserves human-readable output when the flag is absent.
- The only source-side write is user-requested `rar export --minutes N`, where `N` is 1 through 120.
- No project/task/knowledge/Calendar/Obsidian change happens without a fresh exact diff and named confirmation.
- Calendar MCP, session audit, and vault migration remain out of scope.
- Task 5 changes protected hub files only after a separate `Replace this?` approval.

---

### Task 0: Open the recorder implementation task safely

**Files:** Modify `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/rolling-audio-recorder/ai/current-task.md` only through that project's `task-intake` workflow.

- [ ] Before editing recorder code, show its confirmed project header, open its `task-intake` skill, and create a concise task for the JSON export/status contract. Its Done criteria are: exact payload keys, legacy text unchanged, unit tests, and a successful build.
- [ ] Do not overwrite another active recorder task; if one appears, use its `task-switch` workflow and obtain the required confirmation.

### Task 1: Define recorder JSON payloads

**Files:** Create `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/rolling-audio-recorder/Sources/RARCore/RecorderJSON.swift` and `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/rolling-audio-recorder/Tests/RARCoreTests/RecorderJSONTests.swift`.

**Interfaces:** Produces `RecorderExportJSON`, `RecorderStatusJSON`, and `RecorderJSON.encode(_:)`; consumes `Job` and `Job.State`.

- [ ] Write failing tests for exact snake-case keys, `null` optionals, empty warnings, pending/done/failed, and paths with spaces. Run `swift test --filter RecorderJSONTests`; expect FAIL because the types are absent.
- [ ] Implement these `Encodable` payloads: export has `job`, `state`, `audio_path`, `transcript_path`, `requested_minutes`, `exported_seconds`, `warnings`; status has `job`, `state`, `audio_path`, `transcript_path`, `error`. Use CodingKeys and `JSONEncoder.outputFormatting = [.sortedKeys]`.
- [ ] Run `swift test --filter RecorderJSONTests`; expect PASS. Commit `feat: add recorder JSON value contract` with only the two new files.

### Task 2: Add `--json` to recorder commands

**Files:** Modify `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/rolling-audio-recorder/Sources/rar/ExportCommand.swift`, `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/rolling-audio-recorder/Sources/rar/StatusCommand.swift`, and `Tests/RARCoreTests/RecorderJSONTests.swift`.

**Interfaces:** `rar export --minutes N --json` emits exactly one export object after job creation; `rar status <job> --json` emits exactly one status object. Errors remain stderr-only.

- [ ] Write failing renderer tests: JSON has no `job:`/`audio:`/`transcript:` prefix; default output remains unchanged.
- [ ] Add `@Flag(name: .long) var json = false`. Collect export warnings before output, save the job, and choose JSON or legacy text only after success. `status` exposes a transcript path only for an existing done transcript; it preserves the existing dead-worker non-zero exit without partial JSON.
- [ ] Create a temporary-HOME job fixture and assert `rar status "$JOB_ID" --json | jq -e 'keys == ["audio_path", "error", "job", "state", "transcript_path"]'`. Verify pending, failed, and unchanged default output too.
- [ ] Run `swift test`, `swift build`, and `git diff --check`; commit `feat: expose recorder export and status JSON`.

### Task 3: Build a tested Bash guardrail

**Files:** Create `scripts/assistant-workflows.sh` and `scripts/assistant-workflows-test.sh`.

**Interfaces:** Consumes recorder JSON, registered hub, declared scope, and `Kind: meeting|task`; produces validated mechanical summaries only.

- [ ] Build a disposable fixture with mock `rar`, two registered projects, scope, and a temporary recorder exports root. Test unchanged fixture hashes and `Read-only workflow: no changes were made.`, `source_kind: recorder`, `state: done`, `scope: fixture-a,fixture-b`.
- [ ] First run `bash scripts/assistant-workflows-test.sh`; expect FAIL because the script is missing. Add red cases: malformed JSON, minutes 0/121, external or symlink transcript, and flags `--write`, `--apply`, `--calendar`, `--obsidian`.
- [ ] Implement absolute `--hub`, `--scope`, `--date`, one workflow, and one capture source validation. Parse `job`, `state`, `transcript_path` with `jq -er`; canonicalize the transcript parent with `pwd -P`; require a regular non-symlink `.txt` under `$HOME/Library/Application Support/rolling-audio-recorder/exports`.
- [ ] Pending prints job ID and reads no transcript; failed reports JSON error and exits non-zero. Plan/review reads only scoped card/current/future/paused. Capture prints source metadata plus `Semantic analysis: performed by hub-workflows.` It never selects a project, interprets language, emits a proposal, or writes.
- [ ] Run the test and `git diff --check`; expect `PASS: assistant workflow guardrail contract`. Commit `feat: add proposal-only workflow guardrails`.

### Task 4: Add regression checks

**Files:** Modify `scripts/hub-smoke-test.sh` and `scripts/check-consistency.sh`.

- [ ] Add failing static checks: guardrail source must contain `rar export --minutes`, `--json`, `rar status`, and the no-changes line; scan only that script and reject executable `--write`, `--apply`, `Calendar MCP`, `obsidian-vault`, `rar pause`, `rar resume`, `rar install` paths.
- [ ] Require literal backticked `hub-workflows` in a hub rule. Run `bash scripts/hub-smoke-test.sh`; expect FAIL until Task 5 creates and names the skill. Do not weaken this red check.

### Task 5: Apply `hub-workflows` through architecture-update

**Files:** Modify `hub-template/AGENTS.md`, `hub-template/CLAUDE.md`, `hub-template/ai/architecture.md`, `scripts/install-hub.sh`, `scripts/update-installed-hub.sh`, `scripts/hub-smoke-test.sh`, `scripts/check-consistency.sh`; create `hub-template/ai/skills/hub-workflows/SKILL.md`. Later, only after a separate live diff, modify `/Users/zykovsrg/Documents/vibecode/_ai-hub/AGENTS.md`, `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/architecture.md`, and create `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/skills/hub-workflows/SKILL.md`.

- [ ] Show every protected-file replacement and the full new skill; ask exactly `Replace this?`. General plan approval is insufficient.
- [ ] Only after that confirmation, make entry files contain a short route, architecture contain the six-step workflow, and the skill require source selection, recorder JSON, metadata-only candidates, confirmed set before full reads, one meeting-record proposal for `Kind: meeting`, none for `Kind: task`, and one proposal envelope per candidate write. Unknown target remains `create_project` and is never created automatically.
- [ ] Make install/update copy the skill. Test a stale hub upgrade with no project-memory changes. Mutation-test the no-auto-write and skill-name checks by breaking each, observing failure, then restoring.
- [ ] Run `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, `bash scripts/assistant-workflows-test.sh`, and `git diff --check`; expect all PASS. Commit `feat: add proposal-only hub workflows`.

### Task 6: Verify and offer live installation

- [ ] Run `swift test --package-path /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/rolling-audio-recorder` and `swift build --package-path /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/rolling-audio-recorder`.
- [ ] Run `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, `bash scripts/assistant-workflows-test.sh`, and `git diff --check` in this repository.
- [ ] Inspect both worktrees with `git -C /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/rolling-audio-recorder status --short` and `git status --short`.
- [ ] Show a separate exact live-hub diff and ask `Replace this?`; do not install it automatically.

## Rollback

Revert recorder JSON commits, then guardrail and hub-workflow commits. No canonical project, task, knowledge record, Obsidian view, Calendar event, or source transcript is changed by this feature.
