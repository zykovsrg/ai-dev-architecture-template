# Task 2 report — safe central bridge installer

Status: complete.

## TDD record

1. Expanded `scripts/legacy-hub-obsidian-bridge-test.sh` first to cover a
   registered 7.3 project, a 7.4 project, an unregistered 7.3 directory,
   meaningful `AGENTS.md`/`CLAUDE.md` divergence, allowed tool-header
   divergence, dry-run, apply, and idempotence.
2. Ran the test before creating the installer:

   ```text
   scripts/legacy-hub-obsidian-bridge-test.sh: line 66: .../scripts/install-legacy-hub-obsidian-bridge.sh: No such file or directory
   ```

   This is the expected RED state: the contract invoked the missing production
   script.
3. Added the minimal installer and re-ran the contract until green.

## Checks

Command:

```bash
bash -n scripts/install-legacy-hub-obsidian-bridge.sh scripts/legacy-hub-obsidian-bridge-test.sh
bash scripts/legacy-hub-obsidian-bridge-test.sh 2>&1
git diff --check
```

Actual focused-test output:

```text
SKIP: broken-project AGENTS.md/CLAUDE.md differ beyond their tool heading
SKIP: broken-project AGENTS.md/CLAUDE.md differ beyond their tool heading
SKIP: broken-project AGENTS.md/CLAUDE.md differ beyond their tool heading
PASS: legacy hub Obsidian bridge contract
```

`bash -n` and `git diff --check` exited successfully.

## Behaviour verified

- Validates an absolute Git hub and regular, non-symlink registry and scope.
- Selects only registry entries whose canonical path is exactly
  `<hub>/projects/<id>` and whose architecture is 7.3.
- Ignores unregistered and non-7.3 directories.
- Allows the standard first-line Codex/Claude header difference, but skips a
  pair with any other content difference without writing either file.
- Inserts the fixed bridge only once, reports selected IDs and entry files in
  dry-run, and does not change an already bridged pair.

## Scope

Committed files: `scripts/install-legacy-hub-obsidian-bridge.sh` and
`scripts/legacy-hub-obsidian-bridge-test.sh` only. This report is intentionally
not committed.

## Follow-up hardening — 2026-08-29

Expanded the contract first. The pre-fix RED run attempted the externally
registered `../outside-project`, which exposed that the installer ignored the
scope and trusted canonicalized paths. The focused contract now also proves:

- Registry and scope IDs use `^[a-z0-9][a-z0-9-]*$`; traversal IDs are rejected.
- A selected project must be a physical, non-symlink direct child of
  `<hub>/projects`; symlink targets outside the directory are skipped.
- A selected 7.3 project not in the scope is not written.
- Entry files require the exact Codex and Claude first headers and equal bodies.
- Existing bridges are accepted only as one complete canonical block; malformed
  and duplicate blocks are skipped without rewriting either entry file.
- A deterministic `PATH`-local test stub fails only the second `mv`. The
  installer restores the first file and continues; no production failure hook
  was added.

Fresh verification:

```bash
bash -n scripts/install-legacy-hub-obsidian-bridge.sh
bash -n scripts/legacy-hub-obsidian-bridge-test.sh
bash scripts/legacy-hub-obsidian-bridge-test.sh
git diff --check
```

All commands exited 0; the focused contract printed
`PASS: legacy hub Obsidian bridge contract`.
