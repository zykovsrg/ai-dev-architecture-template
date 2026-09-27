# capture

This resource defines only the `capture` scenario. The core `SKILL.md` remains authoritative for scope, security, canonical-source rules, proposal envelopes, confirmation, and learning lifecycle. Nothing here widens those permissions.

Read the first non-empty source line as the declared kind. Accept only `Kind: meeting` or `Kind: task`.

For `Kind: meeting`, the first proposal is exactly one canonical meeting-record proposal. Task, project, knowledge, deadline, and waiting proposals may refer to that meeting record but remain independent proposals.

For `Kind: task`, emit no meeting-record proposal. Allow only task or knowledge proposals grounded in the selected source and permitted canonical records.

If no registered project fits, keep the unknown target as an `action: create_project` proposal. Do not create, register, inspect, or read the proposed project automatically.

Before proposals, report source type and separate sections for source facts, stated decisions, action candidates, likely project candidates, knowledge candidates, dates, waiting/follow-up, and ambiguities. Ground every item in the selected source or permitted canonical records and label inference explicitly.

Then emit proposal envelopes in source order using the core `SKILL.md` schema. Each candidate write keeps its own exact target path and diff. A capture result may present independent proposals as one selectable package, but this only reduces confirmation count; it does not merge writes, widen scope, or authorize changed diffs.
