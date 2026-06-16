# Canonical Lists Dedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the protected-files and controlled-memory lists have a single, machine-verified source of truth, and remove their duplicate copies from human docs.

**Architecture:** A few "holder" files keep each list inline, wrapped in invisible `<!-- canon:NAME -->` HTML-comment markers. A new `scripts/check-consistency.sh` extracts the file-path tokens between markers and fails if any holder disagrees. Pure human docs drop the lists and link to `docs/file-roles.md` instead. The precedence list is deduplicated by reference only (no script).

**Tech Stack:** POSIX-ish Bash (must run on macOS `/bin/bash` 3.2 — no `mapfile`, no associative arrays), GNU/BSD `grep`, `awk`, `sed`, `diff`, Git.

**Spec:** `docs/superpowers/specs/2026-06-16-canonical-lists-dedup-design.md`

---

## Canonical definitions (used by every task)

**Holders for BOTH lists** (list stays inline + markers, verified by script):
- `template/ai/architecture.md`
- `template/CLAUDE.md`
- `template/AGENTS.md`
- `docs/file-roles.md`
- `template/ai/skills/release-check/SKILL.md`

**Marker names:** `canon:protected-files`, `canon:controlled-memory`

**Canonical order — protected-files** (do not reorder):
```
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`
```

**Canonical order — controlled-memory** (do not reorder):
```
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
```

**Link-only files** (remove the inline protected/controlled block, replace with a reference line):
`README.md`, `docs/concepts.md`, `docs/install.md`, `docs/update.md`, `docs/update-installed-projects.md`, `docs/prompts.md`, `docs/start-prompts.md`.

**Reference line to use** (Russian, for human docs):
```
Полные списки защищённых файлов и controlled memory — в [docs/file-roles.md](file-roles.md).
```
(Adjust the relative path per file location: docs/* use `file-roles.md`; `README.md` uses `docs/file-roles.md`.)

---

### Task 1: Create the consistency-check script

**Files:**
- Create: `scripts/check-consistency.sh`

- [x] **Step 1: Write the script**

Create `scripts/check-consistency.sh` with exactly this content:

```bash
#!/usr/bin/env bash
# Verify that every canonical list (wrapped in <!-- canon:NAME --> markers)
# holds the same ordered set of file paths across all files that contain it.
# macOS bash 3.2 compatible: no mapfile, no associative arrays.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MARKERS="canon:protected-files canon:controlled-memory"
fail=0

# extract_block FILE MARKER -> prints one path per line (first `backtick` token)
extract_block() {
  awk -v open="<!-- $2 -->" -v close="<!-- /$2 -->" '
    index($0, open)  { inb=1; next }
    index($0, close) { inb=0 }
    inb { print }
  ' "$1" \
  | grep -E '^[[:space:]]*[-*][[:space:]].*`' \
  | sed -E 's/^[^`]*`([^`]+)`.*/\1/'
}

for marker in $MARKERS; do
  files=""
  while IFS= read -r f; do
    files="$files$f"$'\n'
  done < <(grep -rlF --include='*.md' --exclude-dir=superpowers "<!-- $marker -->" . | sort)

  files="$(printf '%s' "$files" | sed '/^$/d')"
  if [ -z "$files" ]; then
    echo "WARN: no holders found for $marker"
    continue
  fi

  ref=""
  ref_list=""
  marker_ok=1
  while IFS= read -r f; do
    cur_list="$(extract_block "$f" "$marker")"
    if [ -z "$ref" ]; then
      ref="$f"
      ref_list="$cur_list"
      continue
    fi
    if [ "$cur_list" != "$ref_list" ]; then
      fail=1
      marker_ok=0
      echo "MISMATCH [$marker]"
      echo "  reference: $ref"
      echo "  differs:   $f"
      diff <(printf '%s\n' "$ref_list") <(printf '%s\n' "$cur_list") | sed 's/^/    /' || true
    fi
  done <<EOF
$files
EOF

  if [ "$marker_ok" -eq 1 ]; then
    n="$(printf '%s\n' "$files" | grep -c . || true)"
    echo "OK [$marker] — $n holders consistent"
  fi
done

if [ "$fail" -ne 0 ]; then
  echo ""
  echo "Consistency check FAILED. Make the marked lists identical (same paths, same order)."
  exit 1
fi
echo ""
echo "All canonical lists are consistent."
```

- [x] **Step 2: Make it executable**

Run: `chmod +x scripts/check-consistency.sh`

- [x] **Step 3: Run it on the current repo (no markers yet)**

Run: `bash scripts/check-consistency.sh`
Expected: prints `WARN: no holders found for canon:protected-files` and the same for `canon:controlled-memory`, then `All canonical lists are consistent.` and exits 0. (No markers exist yet, so there is nothing to compare.)

- [x] **Step 4: Commit**

```bash
git add scripts/check-consistency.sh
git commit -m "feat: add canonical-lists consistency check script"
```

---

### Task 2: Wrap the protected-files list in markers in all 5 holders

**Files (Modify):**
- `template/ai/architecture.md` (section "Protected architecture files")
- `template/CLAUDE.md` (section "File classes" → protected list)
- `template/AGENTS.md` (same section as CLAUDE.md)
- `docs/file-roles.md` (section "## 1. Protected architecture files")
- `template/ai/skills/release-check/SKILL.md` (after "Protected architecture files and directories:")

- [x] **Step 1: Add markers around each protected-files bullet list**

In each file, locate the existing protected-files bullet list and wrap it. The bullets must be exactly the canonical order above. Insert the opening marker on its own line immediately before the first bullet and the closing marker immediately after the last bullet. Example (architecture.md / CLAUDE.md / AGENTS.md / release-check — plain list):

```markdown
<!-- canon:protected-files -->
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`
<!-- /canon:protected-files -->
```

For `docs/file-roles.md`, the bullets carry Russian annotations on `.claude/` and `.codex/` — keep the annotations; the script reads only the backticked path. The block there looks like:

```markdown
<!-- canon:protected-files -->
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/` (создаётся проектом по необходимости; в шаблоне отсутствует)
- `.codex/` (создаётся проектом по необходимости; в шаблоне отсутствует)
<!-- /canon:protected-files -->
```

Do not change any path or its order. If a holder currently has a different order, reorder it to match the canonical order.

- [x] **Step 2: Run the consistency check**

Run: `bash scripts/check-consistency.sh`
Expected: `OK [canon:protected-files] — 5 holders consistent`, plus the `WARN` line for `canon:controlled-memory` (still no markers), then `All canonical lists are consistent.`, exit 0.

If instead you see `MISMATCH [canon:protected-files]`, read the printed `diff`: it names the file and the differing path. Fix that holder's list to match the canonical order, then re-run until it says OK.

- [x] **Step 3: Commit**

```bash
git add template/ai/architecture.md template/CLAUDE.md template/AGENTS.md docs/file-roles.md template/ai/skills/release-check/SKILL.md
git commit -m "refactor: mark protected-files list as canonical in holders"
```
- Note: Script had a bug — `close` is a reserved word in macOS system awk. Renamed to `endmark` in the awk block. Fix included in this commit alongside Task 2 changes.

---

### Task 3: Wrap the controlled-memory list in markers in all 5 holders

**Files (Modify):** same 5 holder files as Task 2. In `release-check`, the controlled-memory list is currently in a different order and must be normalized.

- [x] **Step 1: Add markers around each controlled-memory bullet list**

Wrap the existing controlled-memory list in each holder with the canonical order:

```markdown
<!-- canon:controlled-memory -->
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
<!-- /canon:controlled-memory -->
```

In `template/ai/skills/release-check/SKILL.md` the list currently reads `current-task, project-context, decisions, changelog, paused-tasks, future-tasks` — reorder it to the canonical order above before adding markers.

- [x] **Step 2: Run the consistency check**

Run: `bash scripts/check-consistency.sh`
Expected: `OK [canon:protected-files] — 5 holders consistent`, `OK [canon:controlled-memory] — 5 holders consistent`, then `All canonical lists are consistent.`, exit 0.

If `MISMATCH`, fix the named file per the printed diff and re-run until OK.

- [x] **Step 3: Commit**

```bash
git add template/ai/architecture.md template/CLAUDE.md template/AGENTS.md docs/file-roles.md template/ai/skills/release-check/SKILL.md
git commit -m "refactor: mark controlled-memory list as canonical in holders"
```

---

### Task 4: Prove the script catches drift (test the test)

**Files:** none committed — this is a deliberate-break-and-revert verification.

- [x] **Step 1: Break one holder on purpose**

In `template/CLAUDE.md`, inside the `canon:protected-files` block, delete the `` - `.codex/` `` line (leave the markers).

- [x] **Step 2: Run the check and confirm it fails**

Run: `bash scripts/check-consistency.sh`
Expected: exit code non-zero; output contains `MISMATCH [canon:protected-files]`, names `template/CLAUDE.md` as `differs`, and the diff shows `.codex/` missing.

Verify exit code: `bash scripts/check-consistency.sh; echo "exit=$?"` → `exit=1`.

- [x] **Step 3: Revert the break**

Run: `git checkout -- template/CLAUDE.md`

- [x] **Step 4: Confirm green again**

Run: `bash scripts/check-consistency.sh; echo "exit=$?"`
Expected: both `OK` lines, `All canonical lists are consistent.`, `exit=0`.

(No commit — nothing changed in the tree.)

---

### Task 5: Remove the duplicated lists from link-only human docs

**Files (Modify):** `README.md`, `docs/concepts.md`, `docs/install.md`, `docs/update.md`, `docs/update-installed-projects.md`, `docs/prompts.md`, `docs/start-prompts.md`.

- [x] **Step 1: Find every duplicated block**

Run: `grep -rn "ai/external-tools.md\|ai/paused-tasks.md" README.md docs/*.md | grep -v file-roles.md`

This lists the human-doc locations that still inline a protected-files or controlled-memory block. (`docs/file-roles.md` is the canonical human page — never strip it.)

- [x] **Step 2: Replace each inline block with a reference line**

For each protected-files or controlled-memory bullet block found in Step 1, delete the bullet list and put in its place:

```markdown
Полные списки защищённых файлов и controlled memory — в [docs/file-roles.md](file-roles.md).
```

Use href `file-roles.md` from inside `docs/`; use `docs/file-roles.md` from `README.md`. Keep any surrounding explanatory sentence that is still useful; only the repeated bullet list is removed. Do not remove incidental single-file mentions in prose (e.g. a sentence about `ai/current-task.md`) — only the enumerated lists.

- [x] **Step 3: Verify no stray blocks remain and the check still passes**

Run: `grep -rn "ai/external-tools.md" README.md docs/install.md docs/update.md docs/start-prompts.md | grep -v file-roles.md || echo "no protected blocks left in link-only docs"`
Run: `bash scripts/check-consistency.sh`
Expected: still both `OK` lines and exit 0 (link-only docs have no markers, so they are not compared).

- [x] **Step 4: Commit**

```bash
git add README.md docs/concepts.md docs/install.md docs/update.md docs/update-installed-projects.md docs/prompts.md docs/start-prompts.md
git commit -m "refactor: link human docs to canonical file-roles instead of duplicating lists"
```
- Note: docs/concepts.md, docs/install.md, docs/update-installed-projects.md, docs/prompts.md had no full enumerated protected-files or controlled-memory bullet blocks (only incidental prose or code-block mentions). Only README.md, docs/update.md, and docs/start-prompts.md had the actual enumerated lists that were replaced.

---

### Task 6: Deduplicate the precedence list by reference

**Files (Modify):** remove the inline 5-level precedence list and add a reference where it appears outside the kept holders.

Keep the precedence list inline ONLY in: `template/ai/architecture.md`, `template/CLAUDE.md`, `template/AGENTS.md`, `docs/concepts.md`.

Remove it (replace with a one-line reference) from: `README.md`, `docs/prompts.md`, `docs/update-installed-projects.md`, `template/ai/external-tools.md`, `template/ai/skills/release-check/SKILL.md`, `template/ai/skills/environment-check/SKILL.md` — wherever the numbered 1–5 precedence list is repeated.

- [x] **Step 1: Find precedence copies**

Run: `grep -rln --include='*.md' "relevant base skill\|нужный базовый skill" . | sort`

- [x] **Step 2: Replace copies outside the 4 kept files**

In each file NOT in the keep-list, delete the numbered precedence list and insert:

```markdown
Порядок приоритета правил см. в `ai/architecture.md` → раздел "Skill precedence".
```

(For English AI files like the skills, use: `See ai/architecture.md → "Skill precedence" for rule priority.`)

- [x] **Step 3: Verify**

Run: `bash scripts/check-consistency.sh`
Expected: both `OK` lines, exit 0 (precedence is not script-checked; this confirms nothing else broke).

- [x] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: keep precedence list in 4 canonical files, link the rest"
```
- Note: The precedence list was only found in README.md outside the 4 kept files (template/ai/external-tools.md, docs/prompts.md, docs/update-installed-projects.md, release-check/SKILL.md, environment-check/SKILL.md did not have the numbered precedence list). Only README.md was changed.

---

### Task 7: Wire the check into the agent workflows

**Files (Modify):**
- `template/ai/skills/architecture-update/SKILL.md`
- `template/ai/skills/release-check/SKILL.md`

- [x] **Step 1: Add a step to architecture-update**

In `template/ai/skills/architecture-update/SKILL.md`, in the `## Steps` list, after the final step (step 10 "Sync the architecture repository documentation…"), add:

```markdown
11. After editing any canonical list (a `<!-- canon:... -->` block), run `bash scripts/check-consistency.sh` and confirm it passes before finishing. If it fails, fix the named holder so all copies match.
```

- [x] **Step 2: Add the check to release-check**

In `template/ai/skills/release-check/SKILL.md`, in the numbered `Check:` list near the top, add a new item:

```markdown
12. Do the canonical lists pass `bash scripts/check-consistency.sh`? If the script fails, mark `Safe to merge: no`.
```

- [x] **Step 3: Verify the script still passes (markers were added to release-check earlier)**

Run: `bash scripts/check-consistency.sh`
Expected: both `OK` lines, exit 0.

- [x] **Step 4: Commit**

```bash
git add template/ai/skills/architecture-update/SKILL.md template/ai/skills/release-check/SKILL.md
git commit -m "feat: run consistency check in architecture-update and release-check"
```

---

### Task 8: Document the system and update the changelog

**Files (Modify):**
- `template/ai/architecture.md` (new subsection + version bump)
- `CHANGELOG.md`

- [x] **Step 1: Add a "Canonical lists and the consistency check" subsection**

In `template/ai/architecture.md`, after the "Architecture files and task memory" section, add:

```markdown
## Canonical lists and the consistency check

The protected-files and controlled-memory lists are duplicated in a few "holder"
files: `ai/architecture.md`, `CLAUDE.md`, `AGENTS.md`, `docs/file-roles.md`, and the
`release-check` skill. Each copy is wrapped in invisible markers, for example
`<!-- canon:protected-files -->` … `<!-- /canon:protected-files -->`.

`scripts/check-consistency.sh` compares the file paths inside matching markers across
all holders and fails if any copy drifts. Run it after editing any marked list. It is
also run by `architecture-update` and `release-check`.

Human docs (`README.md`, other `docs/*`) do not repeat these lists; they link to
`docs/file-roles.md`. When you add a new copy of a canonical list, wrap it in the same
markers so the check covers it.
```

- [x] **Step 2: Bump the architecture version**

In `template/ai/architecture.md`, change the version header from `Version: 6.5` to `Version: 6.6`.

- [x] **Step 3: Add a changelog entry**

At the top of `CHANGELOG.md` (above `## v6.5`), add:

```markdown
## v6.6 — 2026-06-16

- Single source of truth for the protected-files and controlled-memory lists: holders now wrap each list in `<!-- canon:... -->` markers, and `scripts/check-consistency.sh` verifies all copies match.
- Removed the duplicated lists from human docs (`README.md`, `docs/*`); they now link to `docs/file-roles.md`.
- Deduplicated the skill-precedence list to 4 canonical files; the rest link to `ai/architecture.md`.
- Wired the consistency check into `architecture-update` and `release-check`.
- Documented the system in `ai/architecture.md` and bumped it to `6.6`.
```

- [x] **Step 4: Final full verification**

Run: `bash scripts/check-consistency.sh; echo "exit=$?"`
Expected: both `OK` lines, `All canonical lists are consistent.`, `exit=0`.

- [x] **Step 5: Commit**

```bash
git add template/ai/architecture.md CHANGELOG.md
git commit -m "docs: document canonical-lists system; bump architecture to 6.6"
```
- Note: The plan's example prose for the new section used `<!-- canon:protected-files -->` verbatim. This triggered the awk marker-detection in the check script (the exact marker string appeared inline in the new section text). Fixed by rephrasing to `<!-- canon:NAME -->` … `<!-- /canon:NAME -->` which is clear but doesn't match the awk extraction pattern.

---

## Done criteria

- `scripts/check-consistency.sh` exists, is executable, and exits 0 on the repo.
- Deliberately breaking one holder makes the script exit 1 and name the file (verified in Task 4).
- The protected-files and controlled-memory lists appear inline only in the 5 holders, each inside `canon:` markers, in identical order.
- Human docs link to `docs/file-roles.md` instead of repeating the lists.
- The precedence list is inline only in 4 files; others link to `ai/architecture.md`.
- `architecture-update` and `release-check` instruct the agent to run the check.
- `ai/architecture.md` documents the system and is version `6.6`; `CHANGELOG.md` has the `v6.6` entry.
