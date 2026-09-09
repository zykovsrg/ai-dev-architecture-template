# Project rule consolidation inventory

Date: 2026-09-09

## Verified facts

- Registered projects contain 106 root-entry or local-architecture files
  (`AGENTS.md`, `CLAUDE.md`, and `ai/architecture.md`).
- The same general workflow rules occur in at least 110 matches across those
  files: task lifecycle, Superpowers, confirmation, review, and self-audit.
- The duplicated files fall into repeated, byte-identical groups. They are
  shared operating rules, not evidence of a project-specific requirement.
- Several projects have uncommitted unrelated work. A consolidation must not
  overwrite or bundle that work.

## Migration rule

The hub is the sole owner of shared operating rules. A project may retain only
its task data and genuinely project-specific constraints. During migration, a
project entry file becomes a short compatibility pointer; it must not copy the
hub's workflow, routing, review, or self-improvement rules.

## Safe rollout

1. Create a shared, versioned compatibility pointer in the hub template.
2. Replace only byte-identical local rule copies in a first batch.
3. Inventory non-identical local additions and preserve any project-specific
   constraints before replacing the shared portion.
4. Validate entry-file parity, registry integrity, and task records after each
   batch. Do not combine these changes with a project's unrelated dirty work.
