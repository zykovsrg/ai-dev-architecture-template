# evening-review

This resource defines only the `evening-review` scenario. The core `SKILL.md`
remains authoritative for scope, security, canonical-source rules, proposal
envelopes, write policy and learning lifecycle. Nothing here widens permissions.

## Default: guided conversation

Start with tomorrow's events from the exact calendar name `Важно и срочно`.
Resolve its ID through a successful fresh `list_calendar_metadata`; never hardcode
an ID, infer it from a similar name, or substitute another calendar. Read the
requested review date D and tomorrow D+1 through guarded `read_events`, with
exactly the allowed IDs and the calendar timezone. Tomorrow is relative to D,
including when the conversation crosses midnight; do not silently change D.
Inspect `availability_complete` and `unavailable_calendar_ids` for every read.
Name unavailable calendars, do not infer a free day from incomplete coverage,
and skip full-window task sync when coverage is partial.

The first reply renders `## Важно и срочно на завтра` and every event of that
calendar for D+1, including events without projects. Render each timed event
separately as `- HH:MM–HH:MM — <exact title>` and each all-day event separately
as `- весь день — <exact title>`. Keep event titles verbatim: do not shorten, translate, group, or paraphrase them. If access is complete and there are no
such events, say `- Нет.`. Missing or ambiguous calendar identity means
unavailable, not empty. Then ask about the first eligible event of D.
Do not ask about tomorrow's outcomes. Do not require an acknowledgement just
because the urgent list was shown. A user request to discuss it takes priority.

Use the compact task index for discovery and only canonical task files for
richer task facts, under the `hub-task-overview` personal-assistant boundary.
Prepare inputs with `scripts/evening_review.py --hub <hub> --day <D>`; pipe a
JSON object with `metadata`, `today`, `tomorrow` guarded responses and
`sync_window` on stdin. `sync_window` is `{start, end, response}`: the guarded
`read_events` response for a window covering [D-30, D+31). On the first run
(no `consumed` keys) the helper refuses to start without it, so the sync check
cannot be skipped. The helper validates active registered roots and reads only
the three canonical task files. It returns urgent events, a chronological
project-event queue, coverage flags, review keys and `sync` (`complete` with
discrepancy items, or `incomplete` with no items). It performs no writes. Its output is selection
evidence, not proof of completion. Report discovery warnings from the compact
index. On a helper failure, state the failure and use only independently
verified input; never invent an empty queue.

### One project task at a time

Ask only about today's events that have one unambiguous active registered
project: the project resolved from the nested title by
`scripts/archiprojects.py resolve-title` (legacy `category/<project-id>/task`
titles included), or one unique canonical event link. Skip projectless, inactive,
unregistered and conflicting matches silently; never ask “skip this?” about
sleep, travel, meals, broadcasts or other unmatched events. Do not infer a
project from the category alone. A project event without a unique canonical
task may still be reviewed, but resolve ambiguity before writing a task.

Present one exact event title and its time, followed by exactly one short
question about its outcome. Wait for the user's answer. No full calendar,
six-section report, confidence list or batch questionnaire in interactive chat.
The one-question limit applies to the entire reply, including ownership,
waiting, synchronization, learning and goal-progress clarification.

Apply the user's stated completion, progress, carry-over, waiting or new task
immediately through existing write rules; report the exact target path and diff
briefly, then ask the next eligible question in the same reply. `дальше`,
`ничего не фиксируем`, and equivalent replies advance without writes or another
question about that event. Matching Calendar never proves completion.

### Project memory capture

User decision (2026-10-07): after each answered project question, the agent
decides on its own whether the answer holds something worth keeping in that
project's memory, and writes it without asking. Sources are only the user's
answer and what this same conversation already established about that project
(for example a meeting handled earlier in the chat); never read other sessions'
transcripts for this. Targets are the reviewed project's own files:

- `ai/decisions.md` — a decision or agreement that changes how the work is
  done (what is needed, not needed, or deferred, and why), as
  `### YYYY-MM-DD — <short title>` under `## Current decisions`;
- `ai/changelog.md` — a notable outcome (meeting held, material received or
  saved, scope changed), as a paragraph under `### YYYY-MM-DD` in
  `## Current changelog` (reuse today's date heading when present);
- `ai/project-context.md` — a stable fact about the project (people, page
  structure, constraints) that later work must know.

Do not record what the task records already hold (status, dates, stage moves),
routine logistics, unverified claims stated as facts, third-party medical or
personal data, or secrets. Replace a `No ... yet.` placeholder on the first
entry; otherwise append, never rewrite or delete an existing entry (a
correction is a new dated entry that names what it corrects). Most answers
produce nothing; never pad. Report each write in one line with the exact path
inside the same reply as the next question; capture never adds a question.

Keep consumed review keys in conversation state. A user answer about one task
consumes repeated blocks of the same task for D; do not re-ask the second block.
Do not merge distinct tasks merely because they share a project. If the answer
explicitly covers only part of a repeated task, keep its remaining work open.
The helper accepts optional `consumed` keys on stdin to exclude covered tasks;
no durable queue is created. Each subsequent turn advances from the current
cursor; reread affected task files/dates after writes, not the full window.

Explicit user requests can still correct Calendar events without projects,
such as actual sleep or travel times. Those events receive no proactive outcome
questions. Keep approximate times labelled approximate, do not invent end times,
wait owners, follow-up dates or task completion. Changing a recurring event
uses the exact occurrence and `this` scope unless the user requests otherwise.
An explicit deletion request authorizes that exact deletion without asking
again; other deletions still require an explicit yes.

## Internal preparation and learning

Retain snapshots, calendar learning, sync and module gates behind the dialogue.
After a complete D read, pipe one `HH:MM|HH:MM|<title>|<calendar>` per event in
start order to `bash scripts/snapshot-calendar.sh --hub <hub> --at <D>-<HHMM>`.
List prior snapshots with `--list --day <D>`.

Only when learning is listed in `ai/modules.md`, run
`python3 scripts/calendar_drift.py --hub <hub> diff --day <D> --write`
after the snapshot. Report the recorded observation count briefly at the end;
fewer than two snapshots means drift cannot be compared.
Only when `learning` is listed in `ai/modules.md`, read pending friction
with `python3 scripts/workflow_friction.py --hub <hub> list --day <D>`.
Each grounded issue may yield one `add_observation` proposal; display leaves it
pending. Acceptance, rejection, journal ordering and append failure follow
`resources/learning-lifecycle.md`. Ask at most one learning question per turn.

The sync check is the helper's `sync` result; handle its items as in the
`resources/day-plan.md` Sync section, before the first project question. Apply
unambiguous task-time changes directly and report actual writes briefly; with
`sync.status: incomplete`, say sync was skipped because coverage was partial.
The final report always states the sync result in one line. Ambiguous/missing occurrences remain questions;
do not replace a project-outcome question with a batch of sync questions.
Never change status merely because Calendar changed; `Due:` moves only through
`scheduled_after_due`, to a later block date, as in `resources/day-plan.md`.

Only when goals is listed in `ai/modules.md`, record user-stated amounts as
`goal_progress`. Ask for an amount only while reviewing a relevant project task;
do not add unrelated questions after the project queue. Do not infer publications
from work blocks. Learning and sync questions also require a grounded project
task in guided mode. After the queue, close with a short factual report.

## Optional explicit full report

Only if the user explicitly requests a full report, render these headings:
`## Сегодняшний календарь`, `## События и проекты`, `## Ожидания`,
`## Follow-ups`, `## Завтрашний Calendar`, `## Подтвердить`, in that order,
preceded by `## Важно и срочно на завтра`. Render today's and tomorrow's exact
events, including each all-day event separately. Project mappings are inference,
not completion: show project, evidence, and high/low confidence; unmatched
entries create no proactive questions or task proposals.

Waiting facts come only from user statements/selected review-input `## Waiting`
or structured canonical waiting fields with citations. Follow-ups come only
from structured canonical fields. Selected `## Done` and `## Carry over` yield
exact task changes, not calendar-inferred outcomes. Each change uses its own
core proposal envelope, exact target path and diff. Full-report headings do not
apply to the default guided conversation or its subsequent turns.

## Canonical writes

For a direct, unambiguous user statement, apply exactly one `update_task`,
`update_due`, or `update_waiting` change with the project ID, exact target path
and diff. Calendar pairing is required only for schedule changes, new dated
tasks and closing tasks with future events. If the task reference is ambiguous,
change nothing and ask which task is meant. Validate each task write through
`scripts/check-all-task-records.sh` and repair failures before claiming success.
All Calendar changes go through `hub-calendar`, preview then apply, with fresh
verification and subscriber snapshots. Unknown ownership creates no task.
