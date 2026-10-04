# Current Task

Status: review
Stage: review
Task ID: TASK-ai-dev-architecture-20261004-001

## Goal

Session learning for the Hub: cheap models scan new Claude Code and Codex
session transcripts, record cases against one Hub-wide rule catalog, a script
computes confidence and project/global scope, and learned rules reach new chats
through plain files.

## Relevant files

docs/superpowers/specs/2026-10-04-session-learning-design.md;
modules/learning/ (rules, skills, scripts); modules/planning day-plan resource.

## Done criteria

Design approved by the user; deterministic tests for collection, deduplication,
confidence formula, promotion, validation and injection limits pass; live scan
of the cutover-day sessions works in Claude Code (Haiku 4.5) and Codex
(GPT-6-Luna) and the second run reports no new sessions.

## Verification

2026-10-04: branch session-learning (spike, 6 tasks, final review with 8
Important fixes, Hub-side calendar/evening-review work ported, collector
review-date and duplicate fixes). Learning tests 48 OK; architecture-test.sh
and check-consistency pass; strict module boundaries 0 warnings. Installed
into the Hub. Live scan of cutover-day sessions: Claude batch via a Haiku
subagent (general-purpose role; the new hub-session-scanner agent loads only
in a new chat) produced R-1..R-3; Codex batches via codex exec gpt-6-luna
(model confirmed in exec log) returned valid empty results; second status
reports 0 pending. Not yet checked: day-plan scan line in a live day plan;
the hub-session-scanner agent in a fresh Claude chat; this session's own
corrections (picked up by the next scan).

## Agent handoff

Last agent: Claude Code
Last completed task: TASK-ai-dev-architecture-20261003-001.
Guided evening review (urgent-first, one event at a time, only events with
active registered projects) installed in the Hub on 2026-10-03 and closed by
user request on 2026-10-04. Task records pass.
Session review: ai/session-reviews/2026-10-04-guided-evening-review-closure.md
(insufficient-evidence: implementation session not visible at closure).
Local changes are on codex/architecture-corrections-2026-10-02; no push or merge
is recorded.
