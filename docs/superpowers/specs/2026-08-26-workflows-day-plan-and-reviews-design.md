# Workflows: Day Plan, Reviews, and Capture — Design

## Goal

Provide four deterministic workflows for a confirmed set of hub projects:
`day-plan`, `evening-review`, `weekly-review`, and `capture`. Planning and
capture read canonical `ai/` task records, present useful output, and emit
precise proposals only. They never change a project, task, deadline, waiting
record, note, knowledge record, Obsidian file, or Calendar event themselves.

## Scope

The implementation adds one Bash command and one disposable-fixture test suite.
It follows the existing safe projection pattern: absolute paths, registered
project IDs, non-symlink sources, a declared scope file, and a machine-readable
Rolling Audio Recorder contract. Workflow parsing uses `jq`, which is already
used by the repository's shell-contract tests.

Included:

- a day plan for one supplied date;
- an evening review that accepts user-confirmed results from a local input file;
- a weekly review grouped by primary archiproject;
- capture from pasted text, a supplied transcript, a meeting summary, a short
  dictated task, or a selected time period from Rolling Audio Recorder;
- derived lists for current work, ready future work, waiting/follow-up, and
  dated risk items;
- stable text proposal envelopes and no-write assertions for architecture data.

Excluded:

- Apple Calendar MCP installation, permission requests, reads, or writes;
- session audit;
- vault migration or a write to the generated Obsidian views;
- automatic task completion, date transfer, follow-up creation, or note write;
- a persistent proposal queue or an apply command.

Rolling Audio Recorder audio export and transcription are a separate local
source operation, not an architecture write. The user's direct capture request
authorizes that one source operation; the resulting transcript still has no
authority to change any project or knowledge file.

## Rolling Audio Recorder JSON Contract

Modify `rolling-audio-recorder` so these commands accept a `--json` flag:

```text
rar export --minutes <1..120> --json
rar status <job-id> --json
```

On a successful export, `rar export --json` writes exactly one JSON object to
standard output and no human-readable warnings. Its keys are `job`, `state`,
`audio_path`, `transcript_path`, `requested_minutes`, `exported_seconds`, and
`warnings`. `state` is `pending` when transcription was launched and `done`
only when `--no-transcribe` was explicitly requested by a human. `warnings` is
always an array of strings, including an empty array.

`rar status <job-id> --json` also writes exactly one JSON object and no other
standard-output text. Its keys are `job`, `state`, `audio_path`,
`transcript_path`, and `error`. `state` is exactly `pending`, `done`, or
`failed`; `error` is JSON `null` unless `state` is `failed`; and
`transcript_path` is JSON `null` when no transcription file is available. Both
commands retain their current exit statuses and preserve the existing
human-readable output when `--json` is absent. Errors still go to standard
error and do not produce a partial JSON object.

The recorder change includes Swift unit tests for the two JSON shapes, empty
warnings, pending/done/failed states, paths with spaces, and unchanged default
human-readable output. It does not add network access, Calendar access, a
daemon change, or a new persistence store.

## Hub Workflow Layer

Semantic extraction and routing remain the responsibility of the AI agent, not
Bash. The reusable hub skill `hub-workflows` performs this fixed sequence:

1. Receive one user-selected source: pasted summary/transcript, dictated task,
   or a requested Rolling Audio Recorder period.
2. For a recorder period, call only the JSON contract above and show a pending
   or failed result without reading project data.
3. Run metadata-only project search and show candidate IDs, registered paths,
   and the intended purpose of the read.
4. Wait for a confirmed project or named confirmed set; only then read its
   allowed canonical `ai/` records and explicitly selected knowledge paths.
5. Produce the specified plan, review, or capture analysis. The AI agent may
   identify decisions, action candidates, likely project matches, knowledge
   candidates, due-date ambiguity, and waiting/follow-up; it never infers that
   an action is approved.
6. Emit one proposal envelope per possible project, task, meeting, knowledge,
   deadline, waiting, or Calendar write. Before any later application, show a
   fresh exact diff and wait for the named proposal's confirmation.

The optional Bash adapter is a guardrail only. It validates paths, declared
scope, JSON shape, and recorder transcript containment; it renders mechanical
lists for tests but does not classify natural language or select a project.

## Architecture-update Scope

The hub workflow is reusable architecture, so its installation is a separate
`architecture-update` after this design and implementation plan are approved.
It must show an exact diff and receive `Replace this?` approval before touching
any protected file. The expected source changes are:

| Class | Exact files | Purpose |
| --- | --- | --- |
| Hub rules | `hub-template/AGENTS.md`, `hub-template/CLAUDE.md`, `hub-template/ai/architecture.md` | Name `hub-workflows`, state the proposal-only boundary, and route capture/reviews to the skill. |
| Hub skill | `hub-template/ai/skills/hub-workflows/SKILL.md` | Define the six-step AI workflow and its read/write confirmations. |
| Installation | `scripts/install-hub.sh`, `scripts/update-installed-hub.sh` | Copy and preserve the hub workflow during install/update. |
| Contracts | `scripts/check-consistency.sh`, `scripts/hub-smoke-test.sh` | Enforce skill naming, no auto-write, exact-confirmation, and recorder JSON guardrails. |
| Live hub | `/Users/zykovsrg/Documents/vibecode/_ai-hub/AGENTS.md`, `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/architecture.md`, `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/skills/hub-workflows/SKILL.md` | Apply the already approved template contract only after a separately shown live-hub diff. |

The recorder implementation belongs to its confirmed project. Before editing
it, `rolling-audio-recorder` receives its own `task-intake` record; that record
is not a substitute for this architecture task's confirmation gates.

## Command Contract

Create `scripts/assistant-workflows.sh` with this shape:

```text
assistant-workflows.sh \
  --hub <absolute-hub-path> \
  --scope <absolute-project-id-file> \
  --date YYYY-MM-DD \
  [--available-minutes <positive-integer>] \
  [--energy low|normal|high] \
  [--review-input <absolute-markdown-file>] \
  [--capture-input <absolute-text-file>] \
  [--recorder-minutes <integer-1-to-120>] \
  day-plan|evening-review|weekly-review|capture
```

`--review-input` is required only for `evening-review`. It is a user-provided,
read-only Markdown file with sections `## Done`, `## Carry over`, and
`## Waiting`. The command treats its lines as facts reported by the user; it
does not infer completion from checkboxes or the Obsidian vault.

`capture` takes exactly one source: `--capture-input` for a user-supplied
summary or transcript, or `--recorder-minutes` for the most recent selected
period. A short dictated task is represented by a `--capture-input` file whose
first non-empty line is `Kind: task`; a meeting summary or transcript uses
`Kind: meeting`. The input must be an explicitly supplied regular,
non-symlink file; the command never discovers or scans arbitrary transcripts.
The command validates the requested recorder duration as an integer from 1
through 120 minutes.

The scope file contains one registered project ID per line. A scope may be a
proper subset for every command. The command rejects an empty or duplicate
scope, an unknown ID, an unsafe registry/card/task path, relative paths,
symlinks, malformed dates, unsupported energy values, an unexpected flag, and
an unsafe capture/review input file. It reads only each scoped project's card plus
`ai/current-task.md`, `ai/future-tasks.md`, and `ai/paused-tasks.md`; weekly
review may additionally read the hub's canonical `ai/archiprojects.md`.

For `--recorder-minutes`, the command invokes the already installed
`rar export --minutes <N> --json`, reads its `job` and `state` with `jq`, then
polls `rar status <job> --json` until `state` is `done` or `failed`. On success
it reads only `transcript_path` from the JSON object; the path must be a regular
non-symlink `.txt` file under
`~/Library/Application Support/rolling-audio-recorder/exports/`. A pending job
is reported with its ID and no architecture proposal. A failed job is reported
with the recorder's error, and no project data is changed. The workflow never
uses `rar pause`, `rar resume`, `rar install`, or an audio export with
`--no-transcribe`.

There is deliberately no architecture `--write` or `--apply`, Calendar
argument, Obsidian argument, or network call. The only permitted source-side
write is the documented user-requested `rar export --minutes <N>` operation.

## Canonical Reading and Classification

The command extracts only the structured fields already used by the generated
Obsidian views: task state, task title, `due: YYYY-MM-DD`, future-task status,
and waiting fields when present. It does not treat a checkbox, a Kanban card,
or unstructured prose as canonical completion or a new deadline.

Ranking is deterministic:

1. overdue dated actionable work;
2. actionable work due on the requested date;
3. active current tasks;
4. ready future tasks with the earliest date;
5. undated ready work.

Waiting work is not included in the three main actions. A follow-up is due
today when a waiting task has `follow_up: <requested-date>`; it is overdue when
that date is earlier. Missing structured waiting fields are reported as a
risk, never filled automatically.

## Outputs

All outputs start with `Read-only workflow: no changes were made.` and state
the requested date and confirmed scope IDs.

`day-plan` renders, in this order:

1. `Сегодня: контекст`;
2. `Три главных действия` (at most three ranked executable results);
3. `Остальные действия`;
4. `Ожидания и follow-up`;
5. `Риски и сроки`;
6. `Календарь` with the fixed text `Недоступен в этом этапе: Calendar не
   подключён.`;
7. `Нужны решения`.

`evening-review` renders:

1. `Сделано` from `## Done` only;
2. `Перенос` from `## Carry over` only;
3. `Ожидания` from `## Waiting` and scoped canonical waiting records;
4. `Follow-ups`;
5. `Завтрашний Calendar` with the same unavailable notice;
6. `Три главных действия завтра`;
7. `Подтвердить`.

`weekly-review` renders each scoped archiproject first, with target, primary
project contribution, due/forecast assumptions, waiting/follow-ups, and risk.
It shows project detail only when a dated risk, blocker, or waiting record is
present, then concludes with three proposed weekly results and `Нужны решения`.
If no scoped archiproject is available, it reports that fact and still renders
the safe project-level risks.

`capture` first renders `Разбор источника`: source type, speaker labels when
present, stated decisions, action candidates, project candidates, potential
knowledge, due dates, waiting, and ambiguities. It then renders `Предложения
по распределению`. For `Kind: meeting`, the first proposal is exactly one
canonical meeting record. All task, project, and knowledge proposals reference
that record and are independent. For `Kind: task`, there is no meeting record:
only a task or knowledge proposal is allowed. A pasted ChatGPT transcript and
a recorder transcript use the same capture path after their source text is
available.

## Proposal Contract

Each possible canonical, project, knowledge, or Calendar change is an
output-only YAML block:

```yaml
proposal_id: P-<workflow>-<date>-<ordinal>
action: <create_project|update_project|create_task|update_task|update_due|update_waiting|create_knowledge|update_knowledge|calendar-event>
target_kind: <project|project-task|project-knowledge|shared-meeting|calendar-event>
target_project: <registered-id|none>
target_path: <exact-project-or-knowledge-path|calendar:not-configured>
summary: <one exact requested change>
due: <YYYY-MM-DD|none>
source: <workflow and source record>
requires_confirmation: true
```

The command emits a proposal only for an explicit line in `--review-input`
that requests a canonical change, or for a capture candidate grounded in the
supplied source text. It does not turn a ranked action, an overdue date, or a
follow-up into a proposal by itself. A new project is proposed only when no
registered project candidate fits; its proposal names the exact new path and
the required registry/card changes. For this phase the output ends with
`Apply: unavailable; show an exact diff and request fresh confirmation in the
conversation.` Therefore a proposal has no side effect and cannot be reused by
the command later.

## Error Handling

Validation failures exit non-zero before outputting a workflow result. A source
record with an unknown state is omitted from actions and reported in `Риски и
сроки`. Missing `ai/archiprojects.md` makes weekly review show only the safe
project-level result; it does not synthesize an archiproject. An unavailable
Calendar is a normal fixed notice, not an error and never a permission request.

## Tests

Create `scripts/assistant-workflows-test.sh` using a disposable hub fixture.
The fixture covers active, ready, overdue, waiting-with-follow-up,
waiting-without-follow-up, paused, and malformed records plus two primary
archiprojects, one meeting transcript, and one short dictated task. Assertions
cover:

- all four commands render their required section headings;
- action ranking and the three-action cap;
- waiting/follow-up classification and missing-field risks;
- evening review uses only user-provided facts;
- weekly review does not double-count related archiproject links;
- meeting capture proposes one shared meeting record before independent task,
  project, and knowledge proposals, while dictated task capture proposes no
  meeting record;
- recorder duration accepts 1 through 120 only, handles pending/failed status,
  and rejects a transcript path outside the recorder exports directory;
- proposal IDs and every required envelope field;
- no input file changes, including when proposals are emitted;
- rejection of unsafe scope/input paths and any write-like or Calendar flag.

`scripts/hub-smoke-test.sh` gains static checks proving the workflow command
contains no architecture write mode, Calendar invocation, or Obsidian target,
permits only the documented JSON `rar export` and `rar status` source calls, and
that the focused test is registered or runnable from the documented command.

## Rollback

Reverting the workflow command, test script, and smoke-test contract removes
the feature. No canonical project, task, knowledge file, vault file, Calendar
event, or external account needs restoration. The recorder's `--json` flag can
be reverted independently; a recorder export may remain as the user's local
source artifact, and the integration never deletes it.
