# Workflows: Day Plan and Reviews — Design

## Goal

Provide three deterministic, read-only workflows for a confirmed set of hub
projects: `day-plan`, `evening-review`, and `weekly-review`. Each workflow
reads canonical `ai/` task records, presents useful planning output, and emits
precise proposals only. It never changes a task, deadline, waiting record,
note, Obsidian file, or Calendar event.

## Scope

The implementation adds one Bash command and one disposable-fixture test suite.
It follows the existing safe projection pattern: absolute paths, registered
project IDs, non-symlink sources, a declared scope file, and no dependencies
beyond standard macOS command-line tools.

Included:

- a day plan for one supplied date;
- an evening review that accepts user-confirmed results from a local input file;
- a weekly review grouped by primary archiproject;
- derived lists for current work, ready future work, waiting/follow-up, and
  dated risk items;
- stable text proposal envelopes and no-write assertions.

Excluded:

- Apple Calendar MCP installation, permission requests, reads, or writes;
- session audit;
- vault migration or a write to the generated Obsidian views;
- automatic task completion, date transfer, follow-up creation, or note write;
- a persistent proposal queue or an apply command.

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
  day-plan|evening-review|weekly-review
```

`--review-input` is required only for `evening-review`. It is a user-provided,
read-only Markdown file with sections `## Done`, `## Carry over`, and
`## Waiting`. The command treats its lines as facts reported by the user; it
does not infer completion from checkboxes or the Obsidian vault.

The scope file contains one registered project ID per line. A scope may be a
proper subset for every command. The command rejects an empty or duplicate
scope, an unknown ID, an unsafe registry/card/task path, relative paths,
symlinks, malformed dates, unsupported energy values, an unexpected flag, and
an input file outside the hub. It reads only each scoped project's card plus
`ai/current-task.md`, `ai/future-tasks.md`, and `ai/paused-tasks.md`; weekly
review may additionally read the hub's canonical `ai/archiprojects.md`.

There is deliberately no `--write`, `--apply`, Calendar argument, Obsidian
argument, network call, or code path that invokes a write operation.

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

## Proposal Contract

Each possible canonical or Calendar change is an output-only YAML block:

```yaml
proposal_id: P-<workflow>-<date>-<ordinal>
action: <create_task|update_task|update_due|update_waiting|calendar-event>
target_kind: <project-task|calendar-event>
target_project: <registered-id|none>
target_path: <exact-ai-path|calendar:not-configured>
summary: <one exact requested change>
due: <YYYY-MM-DD|none>
source: <workflow and source record>
requires_confirmation: true
```

The command emits a proposal only for an explicit line in `--review-input`
that requests a canonical change. It does not turn a ranked action, an overdue
date, or a follow-up into a proposal by itself. For this phase the output ends
with `Apply: unavailable; show an exact diff and request fresh confirmation in
the conversation.` Therefore a proposal has no side effect and cannot be
reused by the command later.

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
archiprojects. Assertions cover:

- all three commands render their required section headings;
- action ranking and the three-action cap;
- waiting/follow-up classification and missing-field risks;
- evening review uses only user-provided facts;
- weekly review does not double-count related archiproject links;
- proposal IDs and every required envelope field;
- no input file changes, including when proposals are emitted;
- rejection of unsafe scope/input paths and any write-like or Calendar flag.

`scripts/hub-smoke-test.sh` gains static checks proving the workflow command
contains no write mode, Calendar invocation, or Obsidian target and that the
focused test is registered or runnable from the documented command.

## Rollback

Reverting the workflow command, test script, and smoke-test contract removes
the feature. No canonical task, vault file, Calendar event, or external account
needs restoration because this phase has no write operation.
