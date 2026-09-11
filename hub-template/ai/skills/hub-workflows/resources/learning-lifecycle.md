# Learning observation lifecycle

Canonical sequence: proposal shown → still pending → accepted/rejected → resolved.

Read pending friction with `workflow-friction.py list`. Showing a proposal never consumes it. After explicit acceptance, append the confirmed observation to the existing journal with a preceding `source-id: <ID>` comment, checking for that ID first. Only after the journal write succeeds, resolve it as accepted. After explicit rejection, resolve it as rejected without adding it to the journal. If appending fails, leave it pending. Unresolved sources are never pruned.
