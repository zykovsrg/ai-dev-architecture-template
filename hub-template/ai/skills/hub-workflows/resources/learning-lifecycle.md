# Learning observation lifecycle

Canonical sequence: proposal shown → still pending → accepted/rejected → resolved.

## Invariants

- `proposal_display: pending`
- `accepted: journal_append -> resolve_accepted`
- `rejected: no_journal_append -> resolve_rejected`
- `append_failure: pending`

Read pending friction with `workflow-friction.py list`. Showing a proposal never consumes it. After explicit acceptance, check for the observation's `source-id: <ID>` first, append the confirmed observation to the existing journal with that preceding source-id comment when absent, and resolve it as accepted only after the journal write succeeds. After explicit rejection, resolve it as rejected without adding it to the journal. If appending fails, leave it pending. Unresolved sources are never pruned.
