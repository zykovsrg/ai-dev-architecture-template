# Hub consolidation and session learning design

Status: prepared for implementation handoff; no runtime changes applied.

Implementation: [complete plan and four ordered parts](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-complete.md). This supersedes the earlier reconciliation-only handoff.

## Authority and scope

The user authorized correcting architectural defects, removing redundant mechanisms, merging standalone architecture into the hub, and introducing semantic session review. The user explicitly assigned specification and implementation planning to Astra and implementation to Terra or Luna. Stop before production implementation so the user can switch models.

The previous conversation settles the major design choices: keep project-specific memory, preserve task/calendar learning, review agent behavior at every task closure, save a separate review document, support explicit selected-session review, and require confirmation before applying improvements proposed by learning. Application functionality and application code review are excluded.

## Architecture and alternatives

Use incremental consolidation. The architecture repository owns the release source; the installed hub consumes a verified release. Project-specific knowledge and memory stay in each project. Generic workflows are maintained centrally. A deployed copy is not an independent rule-authoring source.

Minimal stabilization alone costs less initially but leaves independent rule copies and does not meet the approved scope. Replacing the architecture in one migration requires a larger simultaneous verification surface and makes rollback harder. Incremental consolidation preserves useful differences and produces individually verifiable releases; it is the selected approach.

## 1. Release integrity

Before any update, compare live hub content with distribution content and preserve useful live changes: goal progress, task/calendar learning, calendar naming/permissions, active-project preservation, and support for adding project boards after the previous generated manifest. A matching version number must never be described as matching contents.

Generate an explicit release file list with content hashes. Include scripts, shared skill resources and tests required by the release. Exclude canonical user/project data and credentials. The updater must preview all writes, including ignore-file edits and explicit removals. It must detect local divergence and allow merging it rather than silently reverting it. Repeated apply must be idempotent. Save sufficient before-state to restore changed files; report partial external failures honestly.

Do not execute the current updater against the live hub before reconciliation is complete. Test fresh install, upgrade and repeated upgrade in disposable installations first. Preserve currently useful behaviors rather than accepting whichever copy has the latest timestamp.

## 2. Task representation and calendar

Canonical written task fields are `Task ID:`, `Status:`, `Due: YYYY-MM-DD`, and the existing `Запланировано: YYYY-MM-DD HH:MM-HH:MM` when a time range exists. Read legacy lowercase `due:` during migration. Equal duplicate dates normalize to one field; conflicting dates block the affected change and report the record. Reject impossible dates using calendar arithmetic.

IDs remain stable. Existing valid legacy IDs remain readable. An unrecognized status, heading or actionable list entry must produce a diagnostic instead of silently disappearing. Do not count every contextual heading as an unfinished task. Keep source text and references when semantics are uncertain. `promoted` needs a trace to current, paused or completed work.

A dated task changed through Obsidian obeys the same task/calendar approval as a change through the shared workflow. Initially block direct application of calendar-relevant proposals and route them to the existing joint preview. Do not silently disable calendar sync to obtain a passing test. A later unified writer may use the existing exact proposal hash and source hashes; it must prevent duplicate events on retry and expose any partial success. Cross-file/external atomicity must not be promised.

## 3. Existing task/calendar learning is preserved

Keep observations, learned preferences, daily/evening/weekly workflows and their confirmation semantics. Fix the reproduced cache faults: snapshots do not overwrite each other, and retention uses actual capture age rather than the future day being planned. Legacy snapshot names remain readable during transition; records with unknown capture age are retained until a conservative migration decision.

An observation is not consumed merely because a proposal was shown. Mark its disposition after acceptance or explicit rejection; interruption leaves it available without duplicate insertion. Retention must not delete an unresolved observation solely because its source cache aged out. Calendar/task preferences stay in their existing learning store and do not become universal project rules.

The existing learning was reportedly launched on 2026-09-08. Its effectiveness is not established yet; that is not a defect. Historical draft session-audit documents are a different evidence source.

## 4. Standalone retirement

Inventory all registered projects using the prior 57-project inventory as a baseline, refreshing counts before changes. Compare entire generic skill packages, including supporting resources. Generate a per-project manifest: keep, merge, remove, reason, hash and recovery location. Do not delete entire configuration or skill directories just because they contain legacy files.

Pilot one simple legacy project, one with nonstandard memory and one with custom skills. Migrate memory compatibility before removing its reader. Preserve custom behavior in selected project-local resources or a narrowly routed shared extension; do not globalize one project's preferences. Test opening a project in supported clients. If a client requires a local entry pointer, it contains only routing to the hub, not duplicated general rules.

After pilots, process remaining projects one at a time. Disable obsolete standalone install/update paths with a clear migration message. Keep migration utilities only while they have a named consumer; retire them after final verification. Archive historical methodology instead of keeping two active session-audit owners. No blanket folder deletion and no silent loss of custom resources.

## 5. Semantic review at every task closure

This is an AI review of how the agent worked, not merely a file/date validator. Extend `hub-task-finish` to call one shared review procedure before clearing task context. Reuse that procedure for the user's explicit request to review a selected session.

### Inputs and coverage

For closure: selected project ID, task ID, current session/thread identifier when available, the task's visible conversation span, relevant active instructions, and the recorded outcome/checks. Review the task's work in the current session. Do not automatically fetch unrelated sessions or all project history.

For manual review: the exact user-selected session and optional task/range. A session selection is not authorization to crawl all sessions. Use an available reader within allowed paths; unavailable history is reported as missing coverage. Never manufacture a session ID. When no stable ID is available, mark it unavailable and use a local review identifier.

Context compaction or truncated outputs reduce coverage: report `partial` and the missing material. A summary supports only the evidence it preserves. Absence of an observed mistake is not proof of a complete-session pass.

### Review questions

1. Did the agent understand the user's goal, constraints and expected result?
2. Did it perform unnecessary work, ask repeated unnecessary questions or miss important instructions?
3. Did it respect the selected project and authority boundaries?
4. Were user corrections incorporated, and were promises or unresolved defects recorded?
5. Was the claimed outcome supported by actual verification?
6. Was the cause an agent mistake, conflicting instructions, a missing procedure, a tool limitation, or insufficient evidence?

A preference, new request or legitimate clarification is not automatically a failure. Evidence must precede a recommendation. Distinguish the observed error from an inferred root cause. Do not introduce a global rule when a local fix or removal of an obsolete rule is sufficient.

### Storage and interface

Add a lazy-loaded shared `hub-session-review` procedure and one shared review template in its resources. `hub-task-finish` references it instead of duplicating its instructions.

Store reviews under the selected project's `ai/session-reviews/`. This keeps closure writes within its existing project-memory boundary. File naming: `<UTC timestamp with seconds>-<task-id or session>-<short unique suffix>.md`. The suffix prevents collisions; it is a local identifier, not a fabricated source session ID. Do not preload this folder at task start.

Each document contains review ID; project/task/session; trigger `task-close` or `user-request`; evidence range and coverage `complete` or `partial`; result `no-issue-observed`, `issues-found` or `insufficient-evidence`; findings with source references; proposed improvement, rationale and affected scope; disposition; verification of any later accepted improvement. Record a short review even when no issue is observed. Never store secrets or raw private transcripts.

The proposal section is authoritative for the review proposal's disposition (`proposed`, `accepted`, `rejected`, `implemented`, `effect-verified`). A remediation task is created only after acceptance, in its actual owner project. It points back to the review; the review points to the task. No second automatically populated backlog or cross-project automatic write is introduced.

Check the current task record and closure changelog for an existing review reference before creating another review. Repeated closure reuses the completed review unless new evidence requires a labeled supplement. Manual re-review explicitly records that it supersedes or supplements the earlier review.

### Closure and failure behavior

Order: verify task completion → review the current task session → persist review/reference → perform the existing approved closure/calendar flow → report outcome. The review is part of closure, so it does not add a separate approval for an ordinary review document. A review finding about a wider architecture improvement does not block closing otherwise completed work. An unfulfilled task requirement still blocks closure.

If review persistence fails, preserve task state and report closure incomplete. If the calendar step fails after review persistence, keep the review and retry closure without generating duplicate findings or events. Partial history can produce a saved partial review and does not itself prevent a legitimately completed task from closing.

### Approval and learning

Review and proposal do not authorize changes to shared rules. Show the concrete change, reason, impact, verification and recovery method; implement after user confirmation. Existing task/calendar learning remains independent in purpose but may be referenced when the same incident is already recorded. Do not count duplicate processing as another occurrence.

After implementation, evaluate effect at the next applicable task closure or explicit review. No recurring model wakeup is required. If no relevant episode occurred, mark effect untested. One reproduced serious defect does not need three repetitions; a broad preference rule needs evidence that it generalizes.

### Cost

Use current task context already available to the agent. Read additional rules and history only to substantiate a finding. Keep an ordinary review short (target about 40 lines); allow more when evidence requires it. Do not silently drop findings to meet a text budget. No automatic rereading of all previous reviews, no automatic second agent, no scheduled whole-history sweep. This still consumes model tokens at every closure; do not claim it is free.

## 6. Retirement and verification

Remove the identified old Codex self-audit schedule during implementation, preserving recovery parameters and using the product's automation controls. Do not touch unrelated planning/calendar automations. If the exact target cannot be established, report that operation pending and continue independent implementation.

Architecture acceptance includes targeted regression tests, three migration pilots, a final per-project manifest, release/install checks, and semantic review scenarios with synthetic conversations. Include: correct completion; misunderstanding corrected by user; ordinary new preference; unsupported success claim; unavailable history; repeated closure; failed review write; declined improvement; accepted improvement later checked for effect.

Live Calendar, Obsidian, recorder and GitHub checks remain separately labeled read/write evidence. Application tests are excluded. A18's historical Google key concern remains an explicit separate risk; do not read or revoke credentials as part of generic cleanup.

## Completion

The programme is complete when included findings have verified resolutions, all registered projects are reconciled, standalone rules no longer return on update, closure review and explicit review both work, existing learning is preserved, and pending architecture proposals remain approval-gated. A clean task list is not evidence that unknown defects do not exist.
