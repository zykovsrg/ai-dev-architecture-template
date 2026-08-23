# Unified AI Assistant Discovery and Architecture Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an evidence-backed, implementation-ready architecture for the unified AI assistant and split its delivery into independently testable subsystem plans.

**Architecture:** This plan is the required discovery and architecture phase before code or data migration. It inventories the current hub and copied Obsidian vault, fixes the minimum data contracts, preserves routing as the primary security boundary, researches current integrations, and ends with separate implementation plans for the foundation, Obsidian views, workflows, Calendar MCP, and self-audit.

**Tech Stack:** Markdown, Bash, Git, existing hub validators, Obsidian Markdown/Canvas/Kanban formats, MCP research using primary documentation, macOS Apple Calendar.

## Global Constraints

- Run this work in confirmed `architecture-update` mode because the approved outcome may propose changes to protected architecture files.
- Do not implement architecture changes, migrate notes, change the live Obsidian vault, or write Calendar events during this plan.
- Use `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/tmp/obsidian-vault-copy/Obsidian` only as a read-only research copy.
- The AI architecture remains the sole source of truth for projects and tasks.
- Obsidian may display project and task data but must not own an independent copy.
- Preserve hub routing: compact cross-project indexes may be searched, but full project reads require explicit confirmed scope.
- Every proposed write, deadline, move, deletion, and Calendar change needs a user approval gate.
- Never copy secrets, personal data, or client-confidential content into reports, fixtures, Git, or command output.
- One project has one primary archiproject; secondary links never count progress twice.
- A task may wait for an external response while its project remains active.
- Use `Inbox` only for ambiguous, deferred, or unprocessed material.
- Use current primary sources when researching MCP and Apple Calendar capabilities.

## Planned file structure

- `docs/superpowers/research/2026-08-23-current-system-inventory.md` — redacted facts about the hub and copied vault.
- `docs/superpowers/specs/2026-08-23-work-model-design.md` — exact archiproject, project, task, waiting, and index contracts.
- `docs/superpowers/specs/2026-08-23-routing-and-search-design.md` — routing, compact indexes, confirmation, and cross-project reads.
- `docs/superpowers/specs/2026-08-23-obsidian-projection-design.md` — read model, Kanban projection, PARA/Zettelkasten structure, and migration map.
- `docs/superpowers/specs/2026-08-23-assistant-workflows-design.md` — capture, daily review, weekly review, waiting, and approvals.
- `docs/superpowers/research/2026-08-23-calendar-mcp-options.md` — verified Apple Calendar integration options and recommendation.
- `docs/superpowers/specs/2026-08-23-session-audit-integration-design.md` — safe use of `hub-session-audit`.
- `docs/superpowers/specs/2026-08-23-unified-assistant-architecture.md` — consolidated approved architecture and dependency order.
- `docs/superpowers/plans/2026-08-23-unified-assistant-foundation.md` — first executable implementation plan.
- Later executable plans, created only after the relevant design is approved: Obsidian projection, assistant workflows, Calendar MCP, and session audit integration.

---

### Task 1: Create a redacted current-system inventory

**Files:**
- Create: `docs/superpowers/research/2026-08-23-current-system-inventory.md`
- Read: `ai/project-context.md`
- Read: `hub-template/ai/project-registry.md`
- Read: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/project-registry.md`
- Read: `tmp/obsidian-vault-copy/Obsidian/**`

**Interfaces:**
- Consumes: approved design `docs/superpowers/specs/2026-08-23-unified-ai-assistant-obsidian-design.md`.
- Produces: verified counts, current file roles, vault structure, plugin list, and explicitly labelled hypotheses used by Tasks 2–7.

- [ ] **Step 1: Capture repository and vault structure without note bodies**

Run:

```bash
git status --short
find tmp/obsidian-vault-copy/Obsidian -type f | awk -F. 'NF>1 {print tolower($NF)}' | sort | uniq -c | sort -nr
find tmp/obsidian-vault-copy/Obsidian -type f -name '*.md' -not -path '*/.trash/*' | wc -l
jq -r '.[]' tmp/obsidian-vault-copy/Obsidian/.obsidian/community-plugins.json | sort
```

Expected: repository status is recorded without modifying files; vault counts and exactly the installed community plugin IDs are returned. Do not print note bodies or raw frontmatter values.

- [ ] **Step 2: Write the inventory with fact/hypothesis separation**

Create the report with these exact top-level sections:

```markdown
# Current System Inventory

## Scope and safety
## Verified AI architecture facts
## Verified Obsidian facts
## Existing project and task model
## Existing knowledge model
## Existing plugins and views
## Data quality risks
## Hypotheses requiring validation
## Constraints carried into design
```

Include the already verified baseline: 716 Markdown files in the copied vault, 457 notes in the main notes folder, 95 archived Markdown files, 632 wiki links, 3,792 Markdown checkbox lines, and plugins `calendar`, `obsidian-hider`, and `obsidian-kanban`. Label checkbox lines as syntax occurrences, not active tasks.

- [ ] **Step 3: Verify the report contains no exposed secrets or note bodies**

Run:

```bash
rg -n -i 'password|token|api[_ -]?key|private[_ -]?key|BEGIN [A-Z ]+ PRIVATE KEY' docs/superpowers/research/2026-08-23-current-system-inventory.md
rg -n '^## (Scope and safety|Verified AI architecture facts|Verified Obsidian facts|Existing project and task model|Existing knowledge model|Existing plugins and views|Data quality risks|Hypotheses requiring validation|Constraints carried into design)$' docs/superpowers/research/2026-08-23-current-system-inventory.md
```

Expected: the first command returns no matches; the second returns nine headings.

- [ ] **Step 4: Commit the inventory**

```bash
git add docs/superpowers/research/2026-08-23-current-system-inventory.md
git commit -m "docs: inventory assistant source systems"
```

### Task 2: Specify the minimum work model

**Files:**
- Create: `docs/superpowers/specs/2026-08-23-work-model-design.md`
- Read: `template/ai/current-task.md`
- Read: `template/ai/future-tasks.md`
- Read: `hub-template/ai/project-registry.md`
- Read: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/project-cards/*.md`

**Interfaces:**
- Consumes: verified inventory from Task 1.
- Produces: exact schemas and invariants consumed by routing, Obsidian, workflow, and foundation plans.

- [ ] **Step 1: Compare the requested hierarchy with existing entities**

Document a field-by-field table for `archiproject`, `project`, `task`, `subtask`, and `waiting`. For every proposed field mark one of: `existing`, `new-required`, or `rejected`.

- [ ] **Step 2: Define the archiproject contract**

Use this minimum candidate and change it only with written evidence:

```yaml
id: august-32-pages
name: Выпустить 32 страницы за август
status: active
target: 32
unit: pages
due: 2026-08-31
```

Specify that every project has at most one `primary_archiproject` and zero or more `related_archiprojects`; only the primary relationship contributes to progress.

- [ ] **Step 3: Define task waiting without overloading project status**

Use this minimum candidate:

```yaml
status: waiting
waiting_for: contractor
waiting_since: 2026-08-23
follow_up: 2026-08-26
next_after_response: Review the contractor's answer
```

Specify project-level `waiting` only when the project has no currently actionable work.

- [ ] **Step 4: Resolve compatibility with one `ai/current-task.md` per project**

Choose and justify exactly one option:

1. extend the existing current/future task files with machine-readable fields;
2. add a separate compact task index derived from existing memory;
3. introduce a new canonical task store and migrate existing memory.

Reject any option that creates two writable sources of truth. Include a compatibility and rollback section.

- [ ] **Step 5: Validate and commit**

Run:

```bash
rg -n 'primary_archiproject|related_archiprojects|waiting_for|waiting_since|follow_up|source of truth|rollback' docs/superpowers/specs/2026-08-23-work-model-design.md
rg -n 'T[B]D|T[O]DO|F[I]XME|implement[[:space:]]+later' docs/superpowers/specs/2026-08-23-work-model-design.md
```

Expected: the first command finds every required contract; the second returns no matches.

```bash
git add docs/superpowers/specs/2026-08-23-work-model-design.md
git commit -m "docs: specify assistant work model"
```

### Task 3: Specify routing and flexible search

**Files:**
- Create: `docs/superpowers/specs/2026-08-23-routing-and-search-design.md`
- Read: `/Users/zykovsrg/Documents/vibecode/_ai-hub/AGENTS.md`
- Read: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/architecture.md`
- Read: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/cross-project-signals.md`

**Interfaces:**
- Consumes: entity IDs and source-of-truth decision from Task 2.
- Produces: permission matrix and compact index contract consumed by Obsidian and workflows.

- [ ] **Step 1: Define three read scopes**

Specify exact behavior for:

```text
metadata-search  -> registered IDs, names, tags, status, brief purpose
confirmed-project -> full memory and explicitly selected knowledge in one project
confirmed-set     -> named set of projects approved for one comparison request
```

- [ ] **Step 2: Define link behavior**

State that a note-to-project link is a discovery hint only. It never upgrades `metadata-search` to a full read. Multi-project notes list IDs, and the agent must ask before following them into project content.

- [ ] **Step 3: Define approval and expiry**

Specify that confirmed multi-project scope applies only to the current explicit request. A new unrelated request routes again. Do not create a permanent global read permission.

- [ ] **Step 4: Add failure cases and acceptance examples**

Include tests in prose for unknown IDs, archived projects, links outside allowed roots, symlink escapes, personal/work mixed search, and a user declining expanded scope.

- [ ] **Step 5: Validate and commit**

Run:

```bash
rg -n 'metadata-search|confirmed-project|confirmed-set|discovery hint|allowed roots|symlink|declin' docs/superpowers/specs/2026-08-23-routing-and-search-design.md
rg -n 'T[B]D|T[O]DO|F[I]XME' docs/superpowers/specs/2026-08-23-routing-and-search-design.md
```

Expected: all contracts are found; no placeholder is found.

```bash
git add docs/superpowers/specs/2026-08-23-routing-and-search-design.md
git commit -m "docs: specify routed cross-project search"
```

### Task 4: Design the Obsidian projection and migration map

**Files:**
- Create: `docs/superpowers/specs/2026-08-23-obsidian-projection-design.md`
- Read: `tmp/obsidian-vault-copy/Obsidian/.obsidian/**`
- Read: `tmp/obsidian-vault-copy/Obsidian/3. Канбан/**`
- Read: `docs/superpowers/specs/2026-08-23-work-model-design.md`
- Read: `docs/superpowers/specs/2026-08-23-routing-and-search-design.md`

**Interfaces:**
- Consumes: canonical data fields and permission scopes.
- Produces: a read-model contract and safe migration phases for a later Obsidian implementation plan.

- [ ] **Step 1: Choose a projection mechanism**

Compare exactly three options: generated Markdown views, an Obsidian plugin/script reading compact indexes, and a vault layout that directly opens approved folders. Score setup cost, write safety, routing safety, offline use, and duplicate-data risk. Recommend one clean option and name the cheaper fallback.

- [ ] **Step 2: Specify the common project board**

Define columns `Incoming`, `Planned`, `Active`, `Waiting`, `Paused`, and `Completed`. One card equals one project. A card shows goal, primary archiproject, nearest deadline, blockers, waiting count, last/next review, and three to seven next actions.

State which fields are read-only projections and how a user edit becomes a proposed architecture change rather than a silent second write.

- [ ] **Step 3: Specify knowledge organization**

Define `Areas`, `Resources/Meetings`, `Inbox`, and `Archives`. Explain when knowledge remains project-local, when it is shared, and how one canonical multi-project meeting note links to projects.

- [ ] **Step 4: Produce a no-write migration map**

Classify existing vault content into `keep`, `add metadata`, `review manually`, `archive candidate`, and `duplicate/conflict candidate`. Do not list private note bodies in the document. Do not perform moves.

- [ ] **Step 5: Validate and commit**

Run:

```bash
rg -n 'generated Markdown|plugin|approved folders|Incoming|Waiting|three to seven|Areas|Resources/Meetings|archive candidate|rollback' docs/superpowers/specs/2026-08-23-obsidian-projection-design.md
rg -n 'T[B]D|T[O]DO|F[I]XME' docs/superpowers/specs/2026-08-23-obsidian-projection-design.md
```

Expected: all required decisions are present; no placeholder is found.

```bash
git add docs/superpowers/specs/2026-08-23-obsidian-projection-design.md
git commit -m "docs: design Obsidian project projection"
```

### Task 5: Specify assistant workflows and approval gates

**Files:**
- Create: `docs/superpowers/specs/2026-08-23-assistant-workflows-design.md`
- Read: `docs/superpowers/specs/2026-08-23-work-model-design.md`
- Read: `docs/superpowers/specs/2026-08-23-routing-and-search-design.md`

**Interfaces:**
- Consumes: canonical fields and read scopes.
- Produces: deterministic input/output contracts for later workflow skills or commands.

- [ ] **Step 1: Define one shared proposal envelope**

Use this minimum shape for every suggested write:

```yaml
action: create_task
target_project: hadassah-seo-analytics
target_path: ai/current-task.md
summary: Проверить отчёт подрядчика
due: 2026-08-26
source: meeting-note-id
requires_confirmation: true
```

Define rejection, partial approval, changed destination, and expired proposal behavior. Keep proposals in the conversation unless persistence is proven necessary.

- [ ] **Step 2: Specify daily planning and 15-minute review**

Define required inputs, exact output sections, and the rule that Calendar/task writes remain proposals. The review must cover completed work, carry-over, waiting, follow-ups, tomorrow's Calendar, and three main actions.

- [ ] **Step 3: Specify the 30-minute weekly review**

Start with archiproject target, actual progress, forecast, project contribution, waiting, and risks. Drill into projects only when a metric or blocker requires it.

- [ ] **Step 4: Specify capture and meeting processing**

Define text, audio, and transcript inputs; one canonical meeting record; multiple linked project IDs; project-specific tasks; owner/deadline uncertainty; and approval before every write.

- [ ] **Step 5: Specify follow-up behavior**

Define how `follow_up` appears in the day plan and Calendar proposal. A missed follow-up becomes a recommendation, not an automatic message or status change.

- [ ] **Step 6: Validate and commit**

Run:

```bash
rg -n 'proposal envelope|partial approval|three main actions|archiproject|canonical meeting|follow_up|automatic message' docs/superpowers/specs/2026-08-23-assistant-workflows-design.md
rg -n 'T[B]D|T[O]DO|F[I]XME' docs/superpowers/specs/2026-08-23-assistant-workflows-design.md
```

Expected: every workflow and failure path is present; no placeholder is found.

```bash
git add docs/superpowers/specs/2026-08-23-assistant-workflows-design.md
git commit -m "docs: specify assistant review workflows"
```

### Task 6: Research and select the Apple Calendar MCP path

**Files:**
- Create: `docs/superpowers/research/2026-08-23-calendar-mcp-options.md`
- Read: `ai/external-tools.md`

**Interfaces:**
- Consumes: proposal envelope and approval rules from Task 5.
- Produces: a verified recommendation and permission contract for a separate Calendar implementation plan.

- [ ] **Step 1: Research current options from primary sources**

Use current official project repositories, manifests, and platform documentation. Record URL, version/date, maintenance status, supported read/write operations, macOS compatibility, authentication, requested permissions, and whether writes can be previewed before execution.

- [ ] **Step 2: Test local availability without installation**

Inspect configured MCP servers and installed tools read-only. Do not install or connect anything. Record `available`, `available but disconnected`, or `not installed` without exposing configuration values.

- [ ] **Step 3: Compare clean and cheap options**

The clean option must support explicit read and write tools, least privilege, structured event IDs, timezone-aware dates, preview before write, and safe update/delete semantics. The cheap option may use a local macOS bridge but must state its security and maintenance cost.

- [ ] **Step 4: Define integration acceptance tests**

Include read-only list, timezone conversion, duplicate prevention, create-after-confirmation, update-after-confirmation, declined write, unavailable Calendar, and rollback/delete behavior. Never test against the live Calendar during this research task.

- [ ] **Step 5: Validate and commit**

Run:

```bash
rg -n 'URL|maintenance|read|write|macOS|permission|timezone|duplicate|declined|rollback' docs/superpowers/research/2026-08-23-calendar-mcp-options.md
rg -n 'T[B]D|T[O]DO|F[I]XME' docs/superpowers/research/2026-08-23-calendar-mcp-options.md
```

Expected: evidence and acceptance cases are present; no placeholder is found.

```bash
git add docs/superpowers/research/2026-08-23-calendar-mcp-options.md
git commit -m "docs: research Apple Calendar MCP options"
```

### Task 7: Design safe session-audit integration

**Files:**
- Create: `docs/superpowers/specs/2026-08-23-session-audit-integration-design.md`
- Read: `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/hub-session-audit/knowledge/runbooks/session-audit-procedure.md`
- Read: `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/hub-session-audit/knowledge/research/checked-sessions.md`

**Interfaces:**
- Consumes: routing and approval model from Task 3.
- Produces: validated trigger and evidence contract for later automation work.

- [ ] **Step 1: Preserve the explicit trigger**

Specify that the system may offer an audit every few days, but reading chats begins only after confirmation. The confirmation names the number or exact set of recent chats.

- [ ] **Step 2: Define a pilot for the draft runbook**

Use three small, recent, non-sensitive sessions as the initial sample. Validate whether all eight current audit points produce useful evidence. The pilot changes no foreign project files.

- [ ] **Step 3: Define outcomes**

Use exactly: `no systemic issue`, `candidate future task`, and `architecture change candidate`. The last outcome still requires separate `architecture-update` confirmation. No finding without evidence may create a proposal.

- [ ] **Step 4: Define privacy and retention**

Do not copy secrets, personal data, patient information, or client-confidential text into summaries. Store only minimal evidence and session identifiers required to avoid duplicate review.

- [ ] **Step 5: Validate and commit**

Run:

```bash
rg -n 'offer|confirmation|three small|eight|no systemic issue|candidate future task|architecture change candidate|secret|patient|duplicate' docs/superpowers/specs/2026-08-23-session-audit-integration-design.md
rg -n 'T[B]D|T[O]DO|F[I]XME' docs/superpowers/specs/2026-08-23-session-audit-integration-design.md
```

Expected: trigger, pilot, outcomes, and privacy rules are present; no placeholder is found.

```bash
git add docs/superpowers/specs/2026-08-23-session-audit-integration-design.md
git commit -m "docs: design session audit integration"
```

### Task 8: Consolidate the architecture and write the first executable plan

**Files:**
- Create: `docs/superpowers/specs/2026-08-23-unified-assistant-architecture.md`
- Create: `docs/superpowers/plans/2026-08-23-unified-assistant-foundation.md`
- Modify: `ai/current-task.md`

**Interfaces:**
- Consumes: all artifacts from Tasks 1–7.
- Produces: one approved architecture and the first TDD implementation plan; later subsystem plans depend on its contracts.

- [ ] **Step 1: Build a requirement-to-design matrix**

Map every requirement from `2026-08-23-unified-ai-assistant-obsidian-design.md` to one exact decision in Tasks 2–7. If a requirement has no decision, stop and resolve it before writing implementation tasks.

- [ ] **Step 2: Write the consolidated architecture**

Include these exact sections:

```markdown
# Unified Assistant Architecture

## Goals and non-goals
## Source-of-truth boundaries
## Work model
## Knowledge model
## Routing and search
## Obsidian projection
## Assistant workflows
## Calendar integration
## Session audit integration
## Error handling and rollback
## Test strategy
## Delivery sequence
## Decisions still requiring approval
```

- [ ] **Step 3: Obtain user approval before planning protected-file edits**

Present the consolidated architecture and exact proposed protected/controlled files. Do not create the foundation implementation plan until the user approves this architecture section.

- [ ] **Step 4: Write the foundation implementation plan**

The plan must use the `superpowers:writing-plans` header and TDD task structure. It covers only canonical work-model fields, compact indexes, validators, updater preservation, documentation, and tests. It must not include Obsidian writes, Calendar writes, vault migration, or recurring automation.

- [ ] **Step 5: Update task memory**

Set `Stage: planning` while plans are being written. Record exact approved design files and the next execution choice. Do not change `ai/future-tasks.md` unless the user separately confirms new future-task entries.

- [ ] **Step 6: Run final checks**

Run:

```bash
rg -n 'T[B]D|T[O]DO|F[I]XME|implement[[:space:]]+later|similar[[:space:]]+to[[:space:]]+Task' docs/superpowers/specs/2026-08-23-unified-assistant-architecture.md docs/superpowers/plans/2026-08-23-unified-assistant-foundation.md
bash scripts/check-consistency.sh
bash scripts/smoke-test.sh
bash scripts/hub-smoke-test.sh
git diff --check
git status --short
```

Expected: placeholder scan returns no matches; all three scripts exit 0; diff check is clean; status contains only intentionally modified task memory before its matching workflow commit/cleanup.

- [ ] **Step 7: Commit the architecture and foundation plan**

```bash
git add docs/superpowers/specs/2026-08-23-unified-assistant-architecture.md docs/superpowers/plans/2026-08-23-unified-assistant-foundation.md
git commit -m "docs: plan unified assistant foundation"
```

## Execution order after this plan

After the foundation implementation passes its tests and is approved, write and execute separate plans in this order:

1. Obsidian read-only projection and project Kanban.
2. Daily planning, daily review, weekly archiproject review, and waiting follow-ups.
3. Text/audio/transcript capture and shared meeting records.
4. Apple Calendar MCP read path, then separately confirmed write path.
5. Session-audit offer and confirmed pilot.
6. Existing vault migration in small, previewed, reversible batches.

Each later plan must have its own approval, tests, rollback, and completion gate.
