# Low-cost session review

## Purpose

Review each closed task and a user-selected session without spending model
tokens on facts a deterministic check can establish.

## Flow

1. Run deterministic checks first: task-record syntax, review-file format,
   references, dates, required fields, and duplicate proposal links.
2. If they pass, give Luna only the selected task goal, outcome, relevant user
   corrections, and the smallest available evidence range. Luna identifies
   misunderstanding, needless work, ignored corrections, unsupported claims,
   forgotten promises, and boundary violations.
3. Escalate to Terra only when Luna explicitly marks the evidence ambiguous or
   finds a potentially material risk. Do not escalate for a clean review,
   formatting failure, or missing evidence that can be reported directly.
4. Save evidence-backed findings and proposals. Nothing is applied without the
   user's approval.

## Constraints

- A partial history is recorded as partial; it never triggers a broad history
  scan automatically.
- An on-demand review uses only the session or range the user selected.
- Deterministic failures stop before any model call.
- The same review is reused on a closure retry unless new evidence exists.

## Verification

The session-review validator rejects malformed or unsupported review records;
the workflow-friction tests preserve unresolved observations; the task record
checker validates all registered projects before a model review begins.
