# Project Knowledge

This local knowledge base is optional reference material. Read it only when a
task, a selected workflow, or the user explicitly needs it. It is not default
context and is not an automatic archive of conversations.

Store records in the category that matches their purpose:

- `research/` — investigated questions and evidence.
- `decisions/` — durable choices and their rationale.
- `risks/` — known risks, assumptions, and mitigations.
- `runbooks/` — repeatable operational procedures.

Create and update records through `knowledge-capture` or `knowledge-review`
after the required confirmation.

## Safety and status

Knowledge records must be secret-free. They must contain no personal data or client data. Never store credentials, passwords, tokens, private keys, raw
environment values, personally identifying material, or client-confidential
material. Omit or redact prohibited content without echoing the rejected value;
refer to an approved secure location instead of recording it.

The only allowed statuses are `draft`, `verified`, `needs-review`, `stale`, or
`superseded`:

- `draft` — incomplete or not yet checked.
- `verified` — supported by current evidence.
- `needs-review` — ready for a focused check.
- `stale` — may no longer be current.
- `superseded` — replaced by a related record.

Retain stale and superseded records at their original paths and link each one
to its replacement under `Related records`; never silently delete it.
