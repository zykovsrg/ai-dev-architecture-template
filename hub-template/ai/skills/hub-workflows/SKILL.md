---
name: hub-workflows
type: worker
description: |
  Use for proposal-only day plans, evening reviews, weekly reviews, and capture
  from one user-selected text, transcript, dictated task, review file, or
  Rolling Audio Recorder period. Performs semantic analysis after scope
  confirmation and never applies a proposal automatically.
---

# Hub Workflows

Use this skill for `day-plan`, `evening-review`, `weekly-review`, or `capture`.
It is proposal-only. Never write or apply a proposal automatically.

Do not run Calendar MCP, perform a vault migration, start a session audit, scan
for arbitrary transcripts, or copy source text into project memory. Do not add
an apply command or a persistent proposal queue.

## Fixed sequence

1. **Select one source.** Receive exactly one user-selected source and name its
   type and purpose. Allowed sources are pasted text, one explicitly selected
   regular non-symlink text file, a dictated task, one explicitly selected
   review file, or a requested Rolling Audio Recorder period. Do not discover
   other files. Do not read project data yet.
2. **Handle recorder JSON only.** For a requested period, the only allowed
   source-side write is the user's requested
   `rar export --minutes <1..120> --json`. Poll only with
   `rar status <job-id> --json`. Parse the returned JSON; never infer job state
   from human-readable output. If state is pending, show the job ID and stop.
   If state is failed, show the recorder error and stop. In either case, do not
   read project data. On success, accept only the explicitly returned regular,
   non-symlink `.txt` transcript below the recorder exports directory.
3. **Find candidates from metadata.** Run a metadata-only candidate search.
   Show at most the useful candidate IDs, their exact registered paths, the
   evidence for each match, and the intended purpose of any later read. A card,
   link, or inferred match is not permission to read project memory, knowledge,
   code, Git, or linked targets.
4. **Confirm scope before full reads.** Wait for an explicit confirmation of a
   confirmed project or named confirmed set. Repeat every project ID and exact
   registered path. Only then may you read the smallest required canonical
   `ai/` records for that scope and explicitly selected project-local
   `knowledge/` paths. Never widen the confirmed set silently.
5. **Perform semantic analysis.** The AI agent, not the Bash guardrail, performs
   semantic analysis. First render separate sections for source facts, stated
   decisions, action candidates, likely projects, knowledge candidates, dates,
   waiting or follow-up, and ambiguities. Ground every item in the selected
   source or confirmed canonical records. Label inference and never treat it as
   approval.
6. **Return exact proposals only after analysis.** Emit one proposal envelope
   per possible write, followed by one exact per-file diff or replacement
   block. Keep proposals independent; if an exact allowed target file is not
   known, ask a question instead of guessing or emitting an actionable
   proposal. Before any later write, show a fresh exact diff for that proposal
   and wait for explicit confirmation that repeats the named proposal ID and
   exact target. A named proposal confirmation authorizes only that exact diff;
   any changed diff needs new confirmation.

## Capture rules

- Read the first non-empty source line as the declared kind. Reject any kind
  other than `Kind: meeting` or `Kind: task`.
- For `Kind: meeting`, the first proposal is exactly one canonical
  meeting-record proposal. Task, project, knowledge, deadline, and waiting
  proposals refer to that meeting record but remain independent.
- For `Kind: task`, emit no meeting-record proposal. Allow only a grounded task
  or knowledge proposal.
- If no registered project fits, keep the unknown target as an
  `action: create_project` proposal. Do not create, register, or inspect a new
  project automatically.

## Workflow outputs

`day-plan` ranks grounded work and separates waiting, follow-up, risks, dates,
and unavailable Calendar context. It does not convert ranking into a write.

`evening-review` treats only the user's declared results as completion facts.
Carry-over, task completion, waiting, and deadline changes remain proposals.

`weekly-review` groups confirmed scope by canonical primary archiproject data.
Related links do not imply contribution and missing data stays an explicit
risk.

`capture` first reports source type, decisions, actions, project candidates,
knowledge candidates, dates, waiting, and ambiguity. Then it reports proposal
envelopes in source order, subject to the meeting/task rules above.

## Proposal envelope

Use one complete envelope for every candidate change:

```yaml
proposal_id: P-<workflow>-<date>-<ordinal>
action: <create_project|update_project|create_task|update_task|update_due|update_waiting|create_knowledge|update_knowledge|calendar-event>
target_kind: <project|project-task|project-knowledge|shared-meeting|calendar-event>
target_project: <registered-id|none>
target_path: <exact-project-or-knowledge-path|calendar:not-configured>
summary: <one exact requested change>
due: <YYYY-MM-DD|none>
source: <workflow and selected source record>
requires_confirmation: true
```

After the envelopes, state that apply is unavailable. A possible project,
task, meeting, knowledge, deadline, waiting, or Calendar write must never be
combined with another write to reduce confirmation count. Immediately after
each envelope, show the exact proposed diff or full replacement block for its
single `target_path`. A create-project proposal must name the exact proposed
direct-child path and list each planned scaffold, registry, and card file, but
must not create or inspect that target.

## Confirmation boundary

Source selection, recorder export consent, scope confirmation, and proposal
confirmation are separate gates. None substitutes for another. A proposal can
be applied only by its owning confirmed project workflow after a fresh exact
diff and named proposal confirmation. Unknown, pending, failed, or ambiguous
targets remain read-only proposals or questions.
