# Obsidian Kanban Card Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render concise project cards with only actionable checklists and canonical due dates.

**Architecture:** Keep the guarded generator, source scope, manifest, and manual-edit detection. Change only Markdown rendering: frontmatter plus seven columns, one project card, nested action checkboxes, and a due date only when canonical `due: YYYY-MM-DD` exists.

**Tech Stack:** Bash 3, awk, sed, shasum, `/usr/bin/jq`, Markdown, existing `obsidian-kanban`.

## Global Constraints

- Architecture records remain canonical; Obsidian edits are proposals only.
- Keep the confirmed source scope and do not infer dates, actions, or completion.
- Do not add a dependency or plugin.
- A fresh explicit confirmation is required before replacing the two copied-vault files.
- Never modify the original vault, architecture records, deadlines, or Calendar from a checkbox.

### Task 1: Test and render concise cards

**Files:**

- Modify: `scripts/generate-obsidian-projects-kanban.sh:239-264`
- Modify: `scripts/obsidian-projects-kanban-test.sh:74-171`

**Interfaces:**

- Consumes: existing `ACTIONS`, `DUES`, `COLUMNS`, `NAMES`, and `IDS` arrays.
- Produces: a `BOARD_RENDER` string accepted by `obsidian-kanban`.

- [ ] **Step 1: Add failing contract assertions**

Add an explicit fixture date and assertions:

```bash
$'Status: active\ndue: 2026-08-26\n\n## Next steps\n\n1. First structured action'
assert_not_contains "$TMP_DIR/preview.txt" '# Projects Kanban (generated)'
assert_contains "$TMP_DIR/preview.txt" '- [ ] First structured action'
assert_contains "$TMP_DIR/preview.txt" '  - 📅 2026-08-26'
assert_not_contains "$TMP_DIR/preview.txt" '  - id: active-project'
assert_not_contains "$TMP_DIR/preview.txt" '  - purpose:'
assert_not_contains "$TMP_DIR/preview.txt" '  - status:'
assert_not_contains "$TMP_DIR/preview.txt" 'нет следующего действия'
```

- [ ] **Step 2: Prove the test fails**

Run `bash scripts/obsidian-projects-kanban-test.sh`.

Expected: FAIL because the old output includes a title, technical fields, placeholders, plain bullets, and `due:`.

- [ ] **Step 3: Implement minimal renderer change**

Retain frontmatter and headings. Remove the title and explanatory paragraph. Replace each card body with:

```bash
printf '\n- [ ] %s\n' "$(field "$id" name)"
while IFS= read -r action; do
  [ -n "$action" ] || continue
  [ "$count" -lt 7 ] || break
  printf '  - [ ] %s\n' "$action"
  count=$((count + 1))
done <<< "$actions"
[ -z "$due" ] || printf '  - 📅 %s\n' "$due"
```

Delete rendering of `id`, `purpose`, `status`, `actions:`, and all fallback action rows. Do not change classification, source readers, manifest source data, or write guards.

- [ ] **Step 4: Verify and commit**

Run `bash scripts/obsidian-projects-kanban-test.sh`, `bash -n scripts/generate-obsidian-projects-kanban.sh`, and `git diff --check`.

Expected: contract PASS, no syntax error, clean whitespace.

Commit:

```bash
git add scripts/generate-obsidian-projects-kanban.sh scripts/obsidian-projects-kanban-test.sh
git commit -m "feat: simplify generated Kanban cards"
```

### Task 2: Preview and confirmed copied-vault update

**Files:**

- Generate only after confirmation: `tmp/obsidian-vault-copy/Obsidian/AI-архитектура/Projects/_views/Projects-Kanban.md`
- Generate only after confirmation: `tmp/obsidian-vault-copy/Obsidian/AI-архитектура/Projects/_views/Projects-Kanban.manifest.json`

**Interfaces:**

- Consumes: the tested generator and temporary scope file of all 35 registry IDs.
- Produces: a no-write preview, then exactly two copied-vault files after confirmation.

- [ ] **Step 1: Preview all confirmed projects**

Run the generator with `--preview`. Verify 35 cards, seven columns, no technical fields or placeholder rows, and only explicit `📅 YYYY-MM-DD` dates.

- [ ] **Step 2: Request fresh write confirmation**

Show the exact two target paths. Do not call `--write` before a direct confirmation.

- [ ] **Step 3: Write and verify after confirmation**

Run:

```bash
bash scripts/generate-obsidian-projects-kanban.sh --hub "$HUB" --scope "$SCOPE" --vault "$COPIED_VAULT" --write --confirm-generated-write
```

Then run `bash scripts/obsidian-projects-kanban-test.sh`, `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, and `git diff --check cb901a3..HEAD`.

Expected: all pass; only board and manifest change in the copied vault; a manual edit blocks replacement with `proposal pending`.

## Rollback

Revert the renderer commit. After a new explicit confirmation, replace only the same board and manifest in the copied vault; never change the original vault or canonical records.
