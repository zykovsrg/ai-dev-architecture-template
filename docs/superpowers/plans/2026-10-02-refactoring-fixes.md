# Architecture corrections

User approved the recommended scope in the audit on 2026-10-02.

1. Add regression tests for calendar identity, recurrence, unrelated titles, competing tasks, and invalid schedules; run them before implementation.
2. Match linked events by calendar and event ID. Multiple occurrences require the exact synchronized span; otherwise emit a non-mutating ambiguity. Match unlinked tasks by exact project and task title, unique event and unique task, excluding recurring events and occupied links.
3. Validate schedule and event-link dates and times centrally; reject malformed fields and reversed/equal ranges.
4. Consolidate write policy and project readiness instructions without introducing modules or altering other projects. Keep legacy cleanup explicit and separately confirmed.
5. Run source checks and release preview; apply only a conflict-free release with no removals. Verify installed managed files. Record remaining limitations.
