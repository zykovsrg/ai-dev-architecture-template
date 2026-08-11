# Personal AI Hub Design

Date: 2026-08-11

Status: approved in conversation; awaiting review of this written specification

## 1. Objective

Add an optional personal AI hub to the AI development architecture. The hub is the single supported AI entry point for users who manage multiple independent projects. It routes a natural-language request to the most likely project, explains the choice, and waits for explicit confirmation before reading that project's memory or code.

The design must remain understandable and maintainable by a non-developer. It must work with Codex and Claude Code, minimize token use, preserve project isolation, and support both software and personal projects.

## 2. Product Modes

The template supports two mutually exclusive installation modes for a given set of projects.

### 2.1 Standalone mode

The existing single-project architecture remains supported. The project contains its own `AGENTS.md`, `CLAUDE.md`, architecture rules, skills, and memory.

### 2.2 Hub mode

The user works through a dedicated `_ai-hub` Git repository. The hub contains the only supported `AGENTS.md` and `CLAUDE.md` entry files for its registered projects. Registered projects retain project-specific memory but do not maintain independent copies of hub rules or base skills.

Direct AI startup inside a registered project is not a guaranteed workflow in hub mode. The supported workflow always starts in `_ai-hub`.

The installer asks whether the user wants the optional personal hub. Declining keeps the existing standalone flow unchanged. The choice is not repeatedly requested during normal updates.

## 3. Filesystem Layout

Example local layout:

```text
<allowed-root>/
├── _ai-hub/
│   ├── AGENTS.md
│   ├── CLAUDE.md
│   ├── ai/
│   │   ├── architecture.md
│   │   ├── active-project.md
│   │   ├── project-registry.md
│   │   ├── project-cards/
│   │   ├── cross-project-signals.md
│   │   ├── archive/
│   │   └── skills/
│   │       ├── project-router/
│   │       ├── project-switch/
│   │       ├── project-register/
│   │       ├── registry-check/
│   │       └── info-update/
│   └── .git/
├── analytics-seo/
│   ├── ai/
│   │   ├── current-task.md
│   │   ├── paused-tasks.md
│   │   ├── future-tasks.md
│   │   ├── project-context.md
│   │   ├── decisions.md
│   │   ├── changelog.md
│   │   └── local-router/
│   └── .git/
└── another-project/
    ├── ai/
    └── .git/
```

Paths are configured during installation and are never hardcoded to one user's computer.

## 4. Ownership and Rule Precedence

The hub owns cross-project routing, allowed roots, confirmation gates, shared workflows, project cards, and cross-project signals. Each project owns its tasks, project context, durable decisions, and changelog.

The hub never copies a project's `current-task`. A project never edits the global registry directly.

Rule precedence is:

1. System constraints and the user's direct request.
2. Hub security and routing rules.
3. The selected project's current-task boundary.
4. The selected project's durable decisions.
5. The selected project's project context.
6. The explicitly activated workflow skill.
7. Cross-project signals as non-authoritative hints.

Project content cannot override project confirmation, allowed-root restrictions, secret protections, or project-memory isolation.

## 5. Registry and Project Cards

### 5.1 Registry

The registry is a compact first-pass index. Each entry contains:

- stable project ID;
- display name;
- type;
- status;
- local path;
- three to seven tags;
- path to the project card.

The registry contains no working documents, task details, medical records, financial details, credentials, or source code.

Supported statuses are:

- `active` — participates in normal routing;
- `paused` — considered only on strong evidence;
- `archived` — excluded from normal routing;
- `missing` — registered path is unavailable;
- `registration-pending` — discovered but not confirmed.

### 5.2 Project card

A card contains:

- stable ID, name, type, status, and last-updated date;
- concise purpose;
- typical tasks;
- optional `Boundaries` for real ambiguities with similar projects;
- explicit related-project links;
- path to the project's local memory entry point.

`Boundaries` is omitted when unnecessary, contains at most three to five items, and never lists obviously unrelated topics.

## 6. Project Selection Algorithm

For each unscoped user request, the hub:

1. Reads only the compact registry.
2. Selects at most three candidates using name, tags, type, and status.
3. Reads only those candidates' cards.
4. Compares purpose, typical tasks, boundaries, and explicit relationships.
5. Reads only relevant active cross-project signals.
6. Assigns `high`, `medium`, or `low` confidence.
7. Shows the candidate, reason, and exact path or asks one focused clarification question.
8. Waits for explicit confirmation.
9. Only after confirmation validates the path and loads the selected project's memory.

High confidence produces one candidate and a confirmation question. Medium confidence produces two candidates or one short clarifying question. Low confidence offers manual selection or creation of a new project.

An exact project name does not bypass confirmation. Rejection leaves all project files unread and unchanged. Repeated routing mistakes may trigger a proposal to update a card, but never an automatic edit.

## 7. Active Project and Project Switching

`active-project.md` stores only project ID, path, selection time, and the rule that a new chat requires confirmation. It never contains the project's task details.

At the start of a new chat, the hub may say which project was last active, but it cannot read that project's memory until the user confirms continuation.

`project-switch`:

1. Shows the current and proposed projects.
2. Checks whether the current project has an unfinished task.
3. Warns without changing or pausing that task.
4. Requests confirmation.
5. Validates the new path and allowed root.
6. Updates `active-project.md`.
7. Runs the hub's project environment check.
8. Reads the selected project's `current-task.md`.
9. Hands the request to `task-intake`.

`project-switch` changes projects but never changes tasks. `task-switch` operates only inside the confirmed active project. Each project has at most one active task, while several projects may independently retain unfinished tasks.

## 8. Local Routing in Large Projects

Hub mode implements the hybrid design: global project routing plus an optional second routing level inside a large project.

The hub may propose a local router when a project has at least three stable independent areas, its card becomes difficult to keep concise, requests repeatedly match multiple internal areas, or irrelevant local context is repeatedly loaded. Installation always requires explicit confirmation through architecture-update.

A local router contains a compact index and area cards, for example `technical`, `analytics`, and `content`. It is not a separate project, has no independent `current-task`, and never changes repository selection. It only selects the relevant part of the already confirmed project's context.

## 9. Cross-Project Signals

A signal is a concise, user-confirmed fact that may matter in another project. Required fields are:

- stable ID;
- creation date;
- source project;
- related project IDs;
- kind;
- concise summary;
- `active` or `archived` status;
- optional source reference.

Hypotheses are optional and must be explicitly separated from facts. Signals have no automatic `expected_effect`, `review_after`, or `expires_at` fields.

Old signals are never deleted or archived automatically. `registry-check` may propose archiving stale signals; the user decides. Only active, relevant signals are read during normal routing.

## 10. Info Update Workflow

`info-update` is a workflow, not a new work mode. Before approval it behaves as review; approved writes occur in implementation mode.

The user may paste a meeting summary and transcript. The workflow:

1. Treats source text as temporary input and does not save it by default.
2. Identifies all affected projects.
3. Shows a short meeting summary.
4. Separates facts, decisions, tasks, current-task changes, future ideas, signals, hypotheses, and uncertain interpretations.
5. Shows proposed edits grouped by project and target file.
6. Requests separate confirmation for each project.
7. Applies only approved edits.

Allowed targets are `project-context.md`, `decisions.md`, `current-task.md`, `future-tasks.md`, `changelog.md`, and hub cross-project signals, subject to each file's existing workflow rules.

`info-update` may refine an existing current task after explicit approval. It cannot replace it with a new task, close it without `task-finish`, switch projects without `project-switch`, save an assumption as a fact, or copy sensitive details into global memory.

Saving the original transcript or summary requires a separate explicit request.

## 11. Security Boundaries

The hub operates only within explicitly registered allowed roots. It never scans the full home directory.

Before project confirmation, it may read only hub configuration, the compact registry, candidate cards, relevant active signals, and names of direct child directories during an explicitly approved inventory.

Classification must not read `.env`, credentials, keychains, source code, working documents, backup contents, or unregistered directories. Symlink resolution must not allow traversal outside an allowed root.

Before reading a selected project, the hub shows its project ID and exact path. Missing or moved paths stop work. The hub may search for a moved project only inside allowed roots and may update the path only after confirmation.

## 12. Installation and Update

### 12.1 First installation

The universal installer asks whether the user wants standalone mode or the optional personal hub.

Hub installation:

1. Creates or prepares a dedicated `_ai-hub` Git repository.
2. Requests one or more allowed roots.
3. Lists direct child directory names only.
4. Classifies candidates as likely project, backup, or unknown.
5. Registers only user-confirmed projects.
6. Checks whether confirmed projects contain required memory files.
7. Offers to add missing memory files but never creates them without confirmation.
8. Performs no moves, archival, or deletion.

If a confirmed project already has a standalone architecture, conversion to hub mode is a separate previewed migration. The migration identifies legacy project entry files and duplicated base rules or skills, explains which files become unnecessary, and waits for explicit confirmation before removing or archiving them. Until that migration is approved, the project remains in standalone mode and is not treated as a fully hub-managed project.

### 12.2 Updates

Updates check versions and show a dry run. They update only shared hub rules, skills, scripts, tests, and documentation. They preserve registry data, project cards, signals, active-project state, allowed roots, and all project memory.

Schema changes require a separate previewed migration. Existing standalone installations remain supported.

README and user-facing documentation must explain both installation modes, the confirmation boundary, migration, updates, direct-project limitations in hub mode, and how to opt into or decline the hub.

## 13. Maintenance and Archival

`registry-check` is read-only until the user approves specific fixes. It checks missing or moved paths, stale cards and relationships, newly discovered direct child folders, archive candidates, and old signals.

An optional weekly reminder may offer to run `registry-check`. It does not run the audit automatically.

Migration of an existing project root is separate from hub implementation:

1. Run read-only inventory.
2. Let the user confirm classifications and registrations.
3. Test routing with real requests.
4. Plan archival separately.

Archival never deletes data. It previews exact source and destination paths, moves only confirmed folders, updates registry status and paths, verifies recovery, and remains reversible.

## 14. Token Budget

Target estimates:

| Context | Estimated tokens |
|---|---:|
| Stable hub instructions | 700–1,200 |
| Registry with 5 projects | 150–300 |
| Registry with 20 projects | 600–1,200 |
| Registry with 50 projects | 1,500–3,000 |
| Registry with 100 projects | 3,000–6,000 |
| Up to three candidate cards | 300–900 |
| Ten active signals | 400–800 |
| Selected project memory before task files/code | 1,000–4,000 |

Typical routing for the current project count should remain near 1,900–5,000 tokens before confirmation. Full reading of 20 project memories could consume roughly 60,000–160,000 tokens. Staged loading should therefore save approximately 85–95% in representative multi-project scenarios.

The implementation must measure generated fixtures at 5, 20, 50, and 100 projects. Semantic search is excluded. If a compact flat index becomes unreliable, first split it by broad type or status and measure again.

## 15. Verification Scenarios

Tests must verify both routing output and forbidden reads.

Required scenarios:

1. Request clearly belongs to one project.
2. Request names a project directly.
3. Request omits the name but uses characteristic terms.
4. Request fits two projects.
5. New idea has no project.
6. New chat continues an unfinished task.
7. Registered project was moved or deleted.
8. One project has technical and analytics areas.
9. User rejects the proposed project.
10. User confirms and the project workflow starts.
11. Agent attempts to read an unregistered directory.
12. Registry contains 50–100 projects.
13. A meeting affects multiple projects.
14. A transcript contains a secret.
15. A signal distinguishes a fact from a hypothesis.
16. A backup directory resembles a project.
17. A project qualifies for a proposed local router.
18. The weekly reminder offers but does not run maintenance.

Fixtures must contain synthetic data only.

## 16. Implementation Phases

### Phase 1: template architecture

Implement the optional hub template, installer and updater changes, compact entry files, registry/card schemas, router workflows, local-router support, consistency checks, fixtures, tests, README, and user instructions.

### Phase 2: local migration

Create the user's `_ai-hub`, inventory `/Users/zykovsrg/Documents/vibecode` without reading project contents, register confirmed projects, add missing memory only after approval, and test routing. Do not move folders.

For projects that currently use standalone architecture, preview their conversion separately. Preserve controlled project memory, and remove or archive duplicated entry files and base workflow files only after explicit approval.

### Phase 3: archival

Preview and perform only confirmed reversible moves of backup or archived folders. No deletion.

### Phase 4: reminder

After manual maintenance is proven, optionally add a weekly reminder that only offers to run `registry-check`.

## 17. Explicit Non-Goals

The first implementation excludes semantic search, RAG, embeddings, databases, servers, Obsidian, automatic project reading, automatic archival, multiple active tasks in one project, and mandatory external relationship skills.

`code-review-graph` remains an optional tool for code relationships inside a selected software project; it does not participate in global routing.
