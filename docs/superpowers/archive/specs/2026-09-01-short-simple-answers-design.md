# Short And Simple Agent Answers — Design

Date: 2026-09-01
Status: approved by user

## Problem

Agent answers are too long and too technical. The user has to work hard to
extract the point.

Two causes, verified in the files:

1. The brevity rule is a single soft line in `Core Principles`
   ("concise, direct, informational style with very simple words"). Soft wording
   loses against concrete instructions elsewhere, including instructions brought
   in by external methodologies such as Superpowers.
2. The `Output` section in the entry files, and the two matching sections in
   `ai/architecture.md` ("Output format before changes", "Output format after
   changes"), require 7+7 mandatory report items in every answer. These are
   concrete, so they win. They are the main source of bloat.

## Decision

Replace both with one hard rule: a numeric default limit plus a short list of
techniques. Numeric limits are enforceable; the techniques say what to cut.

## New `Output` section

Placed in `AGENTS.md` and `CLAUDE.md`, written in English (persistent
AI-facing instructions are English in this project).

- Default answer: at most 5 lines. Go longer only when the user asks, or when
  comparing options — then give the 5-line answer first and details below it.
- Answer first, reason second. No preamble about what was analyzed.
- Replace technical terms with everyday words. If a term is unavoidable,
  explain it in brackets at first use.
- Keep internal machinery out of the answer: mode labels, memory file names,
  workflow names, status fields — only when the user asks for them.
- One question per message. Lists: at most 5 items.
- Never declare a task closed. Propose `task-finish` and wait.
- This holds under any external methodology, including Superpowers.

## Removals

- Old `Output` section in `AGENTS.md` and `CLAUDE.md`.
- Old brevity line in `Core Principles` of both entry files (superseded).
- `ai/architecture.md`: sections "Output format before changes" and
  "Output format after changes", removed in full.
- The requirement to state whether task memory changed. The user accepted the
  risk and wants to work without it.

Kept: the `File Classes` line about naming the workflow that allowed a memory
change. It fires rarely and only for protected files.

## Files to change

Working copy:
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`

Template for new projects:
- `template/AGENTS.md`
- `template/CLAUDE.md`
- `template/ai/architecture.md`

Hub (separate repository, user approved the change):
- `_ai-hub/CLAUDE.md` — same `Output` section, without the `task-finish` line,
  because the hub has its own task mechanics.

## Verification

- `bash scripts/check-consistency.sh`
- `bash scripts/smoke-test.sh`
- Manual read: no leftover reference to the removed sections.

## Notes

`AGENTS.md` and `CLAUDE.md` are protected architecture files. The change must go
through the `architecture-update` workflow with explicit confirmation.
