# Guided evening review

## User requirements

Begin with tomorrow's events from the allowed Calendar named exactly
`Важно и срочно`, including events without projects and all-day events.
Show their exact titles and local times. Then review today's project tasks
one event at a time, with one question per reply. Skip events without a
registered active project without asking whether to skip them.

## Approach

Update the existing planning skill and add a small read-only Python helper
that consumes guarded calendar responses and active project registry metadata.
This is preferred to instructions alone because filtering and chronological
ordering can be tested. A persistent review service would add unnecessary
state; the ongoing chat is sufficient to keep the cursor and outcomes.

## Interaction

The initial response has `Важно и срочно на завтра`, followed by the first
eligible task question. If the urgent calendar is unavailable, say so; do not
claim there are no urgent events. Calendar identity is resolved from fresh
metadata; no hardcoded ID or fuzzy name match. Incomplete reads remain partial.

Build today's queue chronologically, with each all-day event preserved.
Eligibility requires an exact active registered project ID in the middle
segment of `category/project/task`; a canonical task link can establish a
project for legacy titles. Ambiguous or unregistered events are skipped.
Matching a project never implies completion or authorizes richer project reads.
When an event has a project but no unique canonical task, ask about the event
and resolve task ownership before writing.

After each response apply the stated completion, progress, waiting, carry-over,
or new task using existing canonical write and paired Calendar rules. Preserve
uncertain dates, owners and times as unknown instead of inventing them.
`дальше`, `ничего не фиксируем` and equivalent requests advance without writes.
An answer covering repeated blocks of the same task consumes those blocks;
distinct tasks in the same project are not merged. Do not re-ask consumed tasks.

Explicit user corrections to events without projects remain authorized
Calendar changes, even though those events receive no proactive questions.
Only deletions need explicit authorization; do not repeat authorization already
given. Changes to a recurring event affect only the requested occurrence.

Retain synchronization, snapshots, learning and goal-progress lifecycles
internally. Do not force the previous six-section report into interactive chat.
Goal amounts and grounded learning issues may be asked after project tasks,
one question per reply. Close with a short factual report of actual writes.

## Code boundaries

Add an installed planning helper for urgent-event selection and project-event
queue construction, using existing registry/path validation. It accepts
complete guarded metadata and event JSON and performs no Calendar writes.
Reject malformed dates, unsafe registry paths and ambiguous metadata. Return
coverage status with each selection so partial reads never imply absence.
The helper prepares data only; semantic outcome interpretation stays with AI.
Update planning module install declarations, skill resources, rules and tests.
Deploy through the normal Hub updater, preserving user project records.

## Verification

Test urgent-before-review ordering, exact calendar identity, empty and missing
urgent calendars, partial coverage, all-day events, projectless events, inactive
and unregistered IDs, distinct tasks versus duplicate blocks, and skip-without-write.
Run planning tests and applicable architecture/install checks. Confirm the
installed Hub files match source and run a read-only smoke test against guarded
Calendar data. Do not create or change real events during verification.
