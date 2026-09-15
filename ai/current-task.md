# Current Task

Status: done
Task ID: TASK-ai-dev-architecture-20260915-001
Stage: task-finish

## Goal

Support a single confirmed project in the guarded Obsidian board refresh,
without reading or modifying other projects, while preserving full refresh.

## Done criteria

- Partial writes update only scoped boards and their shared metadata entries.
- Registration, path, manual-edit and rollback protection remains enabled.
- Single-project and full-registry fixture tests pass.
- Approved workflow instructions are installed in the working Hub.

## Agent handoff

Last agent: Codex

What changed: Scoped refresh implemented and installed; task closed by explicit
user instruction. This task ID was allocated at closure, not during execution.

Verification: 15 fixture tests, full generator contract, installed/source parity,
Bash syntax, and diff checks passed. Release metadata was rebuilt at closure.

Open risks: Existing consistency/smoke local-rule-directory failure and the
baseline reverse-sync calendar gate remain outside this task's scope.

Session review: ai/session-reviews/2026-09-15-scoped-obsidian-refresh-closure.md
Result details: docs/superpowers/specs/2026-09-15-scoped-obsidian-refresh.md
