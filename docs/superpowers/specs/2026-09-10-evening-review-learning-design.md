# Automatic Evening Review Learning Design

## Goal

Make the evening-review workflow invoke its calendar snapshot and learning-data
collection through one required tool call, while preserving explicit user
confirmation for every durable learning change.

## Decision

Add a read-oriented `prepare_evening_review` tool to the existing guarded
calendar MCP server. The tool receives a requested date, uses only already
allowlisted calendars, reads that day's events, writes the permitted
noncanonical calendar snapshot, finds prior snapshots for the same day, reads
unconsumed workflow-friction entries, and returns one structured response.

The response contains the calendar events, the path and content of the new
snapshot, previous snapshots, and pending friction records. It does not infer a
completion, edit a task, consume friction, append an observation, or change a
learned rule. The assistant uses this response when composing the nine-section
evening review and emits only confirmation-gated learning proposals.

## Boundaries

- The new tool may read only calendars already exposed by the calendar policy.
- It may write only the existing noncanonical snapshot cache.
- Friction records remain pending until an explicit accepted or rejected
  disposition.
- Task records, calendar events, observations, and learned rules remain
  unchanged by this tool.
- The existing `read_events` tool remains available for other workflows.

## Integration

`hub-workflows` will require this tool as the first data source for every
calendar-only evening review. The prior shell guardrail remains a scope
validator; it is not the lifecycle coordinator. A contract test will fail if
the skill stops naming the required tool, and an integration test will exercise
the tool with a fake calendar backend and verify its snapshot and pending
friction response.

## Error Handling

If calendar metadata or event reading fails, the tool returns the underlying
calendar-policy error and makes no snapshot. Invalid dates, empty allowlists,
and malformed cached friction data fail safely. Existing snapshots and pending
friction are never deleted by a failed run.

## Verification

The test suite will prove: a successful call produces one snapshot and returns
events and pending friction; a repeated call preserves earlier snapshots; and a
calendar failure leaves the snapshot cache unchanged. Existing calendar-policy
and friction tests must remain green.
