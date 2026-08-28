---
name: session-audit
type: implementation
description: |
  Use for the periodic review of confirmed `_ai-hub` session transcripts to
  assess whether the AI development architecture helps the user reach the
  intended result efficiently.
---

# Session Audit

Open this skill only for a session audit. It does not authorize transcript
reading by itself.

## Boundaries

- Refresh only `knowledge/research/session-inventory.md` before asking the user
  whether to show it. The refresh reads file metadata only.
- Read a transcript only when the user gives its exact ID in the current audit.
  Never treat “recent sessions” or a count as authorization.
- Read only the confirmed IDs. Missing, malformed, or unavailable IDs stop the
  audit before any journal write.
- Record safe results for the confirmed IDs immediately in
  `knowledge/research/checked-sessions.md`.
- Never copy secrets, tokens, raw environment values, personal data, client
  data, or long transcript text into inventory, evidence, or the journal.
- Findings may propose a future task or architecture change, but never apply
  one. Protected changes require `architecture-update` and new confirmation.

## Procedure

1. Run `scripts/refresh-session-inventory.sh`.
2. Offer the metadata inventory. Do not open transcripts before exact IDs.
3. Validate every selected ID against the current inventory.
4. Read only those selected transcripts and apply all nine checks in
   `knowledge/runbooks/session-audit-procedure.md`.
5. Write one concise, evidence-backed, secret-free result per confirmed ID to
   `knowledge/research/checked-sessions.md`.
6. Report the result. If a systemic change is indicated, show a proposal and
   wait for its separate confirmation.

## Failure handling

If the transcript directory, inventory refresh, ID validation, or transcript
read fails, report the failure and do not modify the journal. If evidence is
unsafe to retain, write `<опущено>` or `evidence withheld`; do not infer a
systemic issue from withheld evidence alone.
