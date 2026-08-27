# Task 5 report — optional local watcher and workflow integration

## Scope

Implemented only Task 5:

- local `--once` watcher that only scans and respects `refresh.lock`;
- read-only plist preview and explicitly confirmed launchd install/uninstall;
- ignored local runtime state;
- Task ID template fields;
- trusted `ai/` → Obsidian refresh and confirmed Obsidian → `ai/` direction in
  hub workflows and user documentation.

No launchd job was installed. No live vault was written.

## RED

Before adding either executable, the new watcher contract failed exactly because
the requested command was absent:

```text
scripts/obsidian-task-sync-test.sh: line 94: .../scripts/obsidian-task-sync-watch.sh: No such file or directory
```

The new smoke assertions also failed before documentation/template work. Its
first failure was an existing stale assertion: `scripts/check-consistency.sh`
reported `16 declared skills exist`, while `scripts/smoke-test.sh` expected 15.
The smoke contract now asserts the verified count of 16.

## GREEN

- A matching board makes watcher `--once` leave no proposal.
- A changed board creates only the ignored local proposal; canonical source
  hashes remain unchanged.
- `refresh.lock` makes watcher `--once` exit before a scan.
- Preview prints a user plist with `StartInterval` 10. Bare install and
  uninstall commands are rejected unless their distinct confirmation flag is
  present.
- A guarded architecture refresh preserves manifest validation; instructions
  require reporting a pending manual Obsidian edit instead of overwriting it.

## Fresh verification

```text
$ bash scripts/obsidian-projects-kanban-test.sh
PASS: Obsidian task Kanban and project overview contract

$ bash scripts/obsidian-task-sync-test.sh
PASS: Obsidian confirmed task sync contract

$ bash scripts/smoke-test.sh
Smoke tests passed.

$ bash -n scripts/*.sh
exit 0

$ git diff --check
exit 0
```

## Concerns

The installer deliberately was tested only through `--preview` and rejected
unconfirmed actions. Installing or unloading the user launchd job remains a
separate user decision. The optional watcher performs only `scan`; it cannot
apply a proposal.

## P1/P2 remediation — RED

The new lifecycle contract invoked the watcher immediately after the real
generated task-board move. Before the fix it failed with:

```text
refresh lock was absent during generated board write
```

The installer contract also creates `vault/.ai-architecture-sync` as a
directory symlink and requires `--preview` to reject it before constructing
the log path or performing an install.

## P1/P2 remediation — GREEN

- Guarded refresh creates `vault/.ai-architecture-sync/refresh.lock` with an
  exclusive `mkdir` before any temporary/generated board write. The lock is a
  directory, so its creation is atomic and does not follow a lock symlink.
- The refresh EXIT cleanup removes only the lock it acquired, on both a
  successful write and an injected board-move failure.
- During the actual generated board move, the contract runs the real watcher;
  it sees the lock and creates no feedback proposal.
- The installer rejects an existing runtime-directory symlink in preview mode
  and uses non-recursive runtime creation for install.

Fresh verification:

```text
$ bash scripts/obsidian-projects-kanban-test.sh
PASS: Obsidian task Kanban and project overview contract

$ bash scripts/obsidian-task-sync-test.sh
PASS: Obsidian confirmed task sync contract

$ bash scripts/smoke-test.sh
Smoke tests passed.
Hub smoke tests passed.

$ bash -n scripts/generate-obsidian-projects-kanban.sh scripts/install-obsidian-task-sync.sh scripts/obsidian-task-sync-test.sh
exit 0

$ git diff --check
exit 0
```
