# Task 1 report

## Result

The failing migration contract test was added to `scripts/legacy-hub-obsidian-bridge-test.sh`.

## Commands

```text
chmod +x scripts/legacy-hub-obsidian-bridge-test.sh
bash scripts/legacy-hub-obsidian-bridge-test.sh
```

## Test result

The test failed as intended (exit code 1):

```text
scripts/legacy-hub-obsidian-bridge-test.sh: line 46: .../scripts/install-legacy-hub-obsidian-bridge.sh: No such file or directory
```

This confirms the contract currently fails because the installer required by the interface does not exist yet. No installer was implemented in Task 1.
