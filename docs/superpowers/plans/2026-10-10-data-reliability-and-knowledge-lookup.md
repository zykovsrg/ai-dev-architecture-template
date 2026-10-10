# Reliability and topical knowledge lookup

User-approved scope: both review bots, both goal planners, snapshot publication, 48 placeholder project contexts, and relevant knowledge discovery before development.

1. Reproduce and repair bounded TTL cache behavior and query indexes in both bots. Use synthetic SQLite fixtures and verify repeated schema initialization.
2. Coordinate atomic storage writes and reject stale full-state saves in both planners; test concurrent saves, conflict handling, failure preservation, and bundled UI compatibility.
3. Publish snapshot pointers atomically; reject unsafe/empty/non-file targets and preserve previous publication on failure.
4. Replace only placeholder context using registered metadata and verified local structure, retaining unknowns explicitly. Update creation instructions to require evidence-backed context without placeholders.
5. Add a small conditional lookup rule. Search confirmed-project knowledge and explicitly published generic Hub references. Read only matches, respect status and sources, continue if absent. Do not turn every article into a skill.
6. Check module boundaries, installation behavior, synthetic regression suites, task records, and scoped diffs. Close the tasks only after verification and save scoped local history.

Material lessons: local bounded TTL instead of unjustified Redis; indexes chosen from actual queries; stable identifiers and atomic publication; no unnecessary service split or Firecracker deployment. Preserve historical data rather than treating every duplicate as a normalization error.

No live databases, medical records, credentials, or external APIs are needed.
