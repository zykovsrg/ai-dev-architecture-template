# Nested Project Promotion Implementation Plan (Part B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the six standalone projects nested inside three registered hub projects into first-class hub projects, so every unit of work is routable, validated, and backed by its own repository.

**Architecture:** `hadassah-analytics` holds a single nested project and is flattened in place, keeping its id and repository. The five nested projects under `hadassah-seo-tech` and `hadassah-content` each move to `<hub>/projects/<new-id>`, get their own repository and GitHub remote, a card, and a registry entry. The two emptied containers stay in the registry with `Status: archived`, preserving their git history.

**Tech Stack:** git, GitHub CLI (`gh`, already authenticated as `zykovsrg`), the hub registry files, `scripts/check-hub-registry.sh`.

## Global Constraints

- Hub: `/Users/zykovsrg/Documents/vibecode/_ai-hub`. All project paths are direct children of `<hub>/projects`.
- **Prerequisite: Part A is complete.** This plan uses the post-rename skill names (`hub-project-register`, `hub-environment-check`). If it is executed before Part A, drop the `hub-` prefix from those names.
- Every promotion needs its own explicit user confirmation naming the id and the exact source and destination paths. Never promote two projects on one confirmation.
- Reading a nested project's memory requires its own confirmation and happens in Task 1, before any move.
- Registry ends at 28 entries: 23 existing + 5 new. The two emptied containers remain as `archived`.
- Card `Status` must equal registry `Status` — `check-hub-registry.sh` compares them.
- Destination directory names are ASCII slugs. Source names contain Cyrillic, spaces, and colons; always quote them.
- After every task: `bash /Users/zykovsrg/Documents/vibecode/_ai-hub/scripts/check-hub-registry.sh /Users/zykovsrg/Documents/vibecode/_ai-hub` must pass.
- **Both containers must have a clean working tree before any move.** `hadassah-seo-tech` currently has two uncommitted files, one of them inside a directory this plan moves. The container commit steps use `git add -A`, which would sweep those unrelated changes into a promotion commit. Resolving them is audit item 5, deferred by the user; it must be settled in Task 1 before Task 3 starts.
- Card content produced by Task 1 lives at `CARD_CONTENT=/private/tmp/claude-501/-Users-zykovsrg-Documents-vibecode--ai-hub/3650b03c-db1b-468a-a1de-ed65b09034d4/scratchpad/promotion-card-content.md`. Promotion tasks copy the two lines from the section matching their id.

---

## The five promotions

| # | Source | New id | Name | Tags |
|---|---|---|---|---|
| 1 | `hadassah-seo-tech/seo-audit-13-jul` | `hadassah-seo-audit-jul` | Hadassah SEO Audit — July | work, hadassah, seo, audit |
| 2 | `hadassah-seo-tech/вся техничка:работа с подрядчиком` | `hadassah-seo-tech-contractor` | Hadassah SEO Tech — Contractor | work, hadassah, seo, technical, contractor |
| 3 | `hadassah-content/кц:онкология` | `hadassah-content-oncology` | Hadassah Content — Oncology | work, hadassah, content, oncology |
| 4 | `hadassah-content/цк:детская хирургия` | `hadassah-content-pediatric-surgery` | Hadassah Content — Pediatric Surgery | work, hadassah, content, pediatric-surgery |
| 5 | `hadassah-content/цк:центр коррекции веса и метаболизма` | `hadassah-content-weight-metabolism` | Hadassah Content — Weight And Metabolism | work, hadassah, content, weight, metabolism |

All five are `Type: workspace`.

## Shared promotion procedure

Every promotion task runs this procedure with its own values. The function is
defined once here; each task supplies concrete arguments and its own
verification. Paste it into the shell before running promotion tasks.

```bash
promote_nested_project() {
  local source_rel="$1" new_id="$2" name="$3" tags="$4" purpose="$5" typical="$6"
  local hub=/Users/zykovsrg/Documents/vibecode/_ai-hub
  local source="$hub/projects/$source_rel"
  local dest="$hub/projects/$new_id"
  local today
  today="$(date +%Y-%m-%d)"

  [ -d "$source" ] || { echo "ERROR: missing source: $source" >&2; return 1; }
  [ ! -e "$dest" ] || { echo "ERROR: destination exists: $dest" >&2; return 1; }
  [ ! -e "$source/.git" ] || { echo "ERROR: source already has its own repository" >&2; return 1; }

  mv "$source" "$dest"

  ( cd "$dest" \
    && git init -q \
    && git add -A \
    && git commit -q -m "chore: import project promoted from $source_rel" )

  if gh repo view "$new_id" >/dev/null 2>&1; then
    echo "WARNING: GitHub repository $new_id already exists; leaving local only (pending-sync)"
  else
    ( cd "$dest" \
      && gh repo create "$new_id" --private --source=. --remote=origin --push ) \
      || echo "WARNING: remote provisioning failed; local repository retained (pending-sync)"
  fi

  cat >> "$hub/ai/project-registry.md" <<REGISTRY

## $new_id
Name: $name
Type: workspace
Status: active
Path: $dest
Tags: $tags
Card: ai/project-cards/$new_id.md
REGISTRY

  cat > "$hub/ai/project-cards/$new_id.md" <<CARD
# $name

Project ID: $new_id
Name: $name
Type: workspace
Status: active
Last updated: $today
Purpose: $purpose
Typical tasks: $typical
Memory entry point: $dest/ai/current-task.md
CARD

  bash "$hub/scripts/check-hub-registry.sh" "$hub"
}
```

---

### Task 1: Verify preconditions and collect card content

**Files:**
- Read: `ai/current-task.md` and `ai/project-context.md` in each of the six nested directories and in `hadassah-analytics`
- Create: the `$CARD_CONTENT` file named in Global Constraints (scratch, not committed)

**Interfaces:**
- Produces: one `Purpose:` line and one `Typical tasks:` line per promotion, used verbatim as arguments 5 and 6 of `promote_nested_project`.

- [ ] **Step 1: Ask for the reading confirmation**

Ask the user, naming all six directories and the two files to be read, for permission to read their memory in order to write accurate cards. This is a hub confirmation gate; do not read before the answer.

- [ ] **Step 2: Check for cross-references between nested projects**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
grep -rn --include='*.md' -e 'seo-audit-13-jul' -e 'вся техничка' -e 'кц:онкология' \
  -e 'цк:детская хирургия' -e 'цк:центр коррекции' \
  "$HUB/projects/hadassah-seo-tech" "$HUB/projects/hadassah-content" \
  "$HUB/projects/hadassah-analytics" 2>/dev/null
```

Expected: no output. Any hit means a nested project names a sibling or its container — **stop and report to the user before moving anything**, per the spec precondition.

- [ ] **Step 3: Check whether `hadassah-analytics` has live work of its own**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
grep -n '^Status:' "$HUB/projects/hadassah-analytics/ai/current-task.md"
```

Expected: `Status: empty`. If it is anything else, the container has its own unfinished task, flattening would overwrite it, and Task 2 must be replaced by a normal promotion of `воронка по сингл-доз на июль` to its own id — report this to the user and get a decision before continuing.

- [ ] **Step 3b: Require a clean working tree in both containers**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
for id in hadassah-seo-tech hadassah-content hadassah-analytics; do
  printf '%-24s %s\n' "$id" "$(git -C "$HUB/projects/$id" status --porcelain | tr '\n' ';')"
done
```

Expected: all three empty. `hadassah-seo-tech` is known to be dirty — two modified files, one of them inside a directory Task 4 moves. A `git add -A` in a promotion commit would sweep those unrelated edits in. Show the diff to the user and let them decide whether to commit or discard; do not decide for them, and do not start Task 3 until all three are clean.

- [ ] **Step 4: Write the card content file**

Write `$CARD_CONTENT` with exactly five sections, in this format — one blank line
after each section, because the extraction command reads from the heading to the
next blank line:

```markdown
## hadassah-seo-audit-jul
Purpose: One sentence stating what this project is for, taken from its own project-context.md.
Typical tasks: One sentence naming the recurring work, taken from its own recorded tasks.

## hadassah-seo-tech-contractor
Purpose: ...
Typical tasks: ...
```

Neither line may contain a colon-newline, a secret, a client name that the
project itself does not already record, or copied task text.

If the user declined Step 1, use the convention already present in the existing
cards instead, for example
`Purpose: Workspace for the Hadassah July SEO audit; the purpose is inferred from the folder name.`

- [ ] **Step 5: Report and stop for confirmation**

Present the precondition results and the five card blocks. Do not start Task 2 until the user confirms them.

---

### Task 2: Flatten `hadassah-analytics`

**Files:**
- Move: `projects/hadassah-analytics/воронка по сингл-доз на июль/*` → `projects/hadassah-analytics/`
- Modify: `projects/hadassah-analytics/ai/*`

- [ ] **Step 1: Record the before state**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
P="$HUB/projects/hadassah-analytics"
ls -a "$P"; ls -a "$P/воронка по сингл-доз на июль"
grep -c '' "$P/ai/current-task.md"
```

Expected: the container holds `ai/`, `knowledge/`, and the one nested directory.

- [ ] **Step 2: Replace the container's memory with the nested project's memory**

Verified in Task 1 on 2026-08-15: the container's own `ai/current-task.md` is a three-line stub reading "No active task is recorded yet." with no `Status:` field at all — not the standard template the plan assumed, but equally empty of work. The nested project's `ai/current-task.md` carries `Status: active` with a live goal. The nested memory is therefore the real one and must be the survivor; deleting the container's `ai/` loses nothing.

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
P="$HUB/projects/hadassah-analytics"
N="$P/воронка по сингл-доз на июль"
rm -rf "$P/ai"
mv "$N/ai" "$P/ai"
for entry in "$N"/* "$N"/.[!.]*; do
  [ -e "$entry" ] || continue
  mv "$entry" "$P/"
done
rmdir "$N"
```

- [ ] **Step 3: Verify the flattened project**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
P="$HUB/projects/hadassah-analytics"
ls "$P"
for f in current-task paused-tasks future-tasks project-context decisions changelog; do
  [ -f "$P/ai/$f.md" ] && echo "ok $f" || echo "MISSING $f"
done
bash "$HUB/scripts/check-hub-registry.sh" "$HUB"
```

Expected: six `ok` lines, no nested directory left, `Registry check passed: 23 projects`.

- [ ] **Step 4: Commit**

```bash
cd /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/hadassah-analytics
git add -A
git commit -m "refactor: flatten nested project into the project root"
git push origin main
```

---

### Task 3: Promote `seo-audit-13-jul`

**Files:**
- Move: `projects/hadassah-seo-tech/seo-audit-13-jul` → `projects/hadassah-seo-audit-jul`
- Modify: `ai/project-registry.md`; Create: `ai/project-cards/hadassah-seo-audit-jul.md`

- [ ] **Step 1: Get the per-project confirmation**

Show the user the exact source path, destination path, and id, and wait for an explicit yes.

- [ ] **Step 2: Run the promotion**

```bash
promote_nested_project \
  "hadassah-seo-tech/seo-audit-13-jul" \
  "hadassah-seo-audit-jul" \
  "Hadassah SEO Audit — July" \
  "work, hadassah, seo, audit" \
  "$(sed -n "/^## hadassah-seo-audit-jul$/,/^$/p" "$CARD_CONTENT" | sed -n "s/^Purpose: //p")" \
  "$(sed -n "/^## hadassah-seo-audit-jul$/,/^$/p" "$CARD_CONTENT" | sed -n "s/^Typical tasks: //p")"
```

- [ ] **Step 3: Verify**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
ls "$HUB/projects/hadassah-seo-audit-jul"
git -C "$HUB/projects/hadassah-seo-audit-jul" log --oneline -1
git -C "$HUB/projects/hadassah-seo-audit-jul" remote -v
bash "$HUB/scripts/check-hub-registry.sh" "$HUB"
```

Expected: `Registry check passed: 24 projects`, one commit, an `origin` remote (or an explicit `pending-sync` warning from Step 2).

- [ ] **Step 4: Commit the container and the hub**

```bash
cd /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/hadassah-seo-tech
git add -A && git commit -m "refactor: promote seo-audit-13-jul to its own project" && git push origin main
cd /Users/zykovsrg/Documents/vibecode/_ai-hub
git add ai/project-registry.md ai/project-cards/hadassah-seo-audit-jul.md
git commit -m "feat: register hadassah-seo-audit-jul"
```

---

### Task 4: Promote `вся техничка:работа с подрядчиком`

**Files:**
- Move: `projects/hadassah-seo-tech/вся техничка:работа с подрядчиком` → `projects/hadassah-seo-tech-contractor`
- Modify: `ai/project-registry.md`; Create: `ai/project-cards/hadassah-seo-tech-contractor.md`

- [ ] **Step 1: Get the per-project confirmation**

Show the exact source path, destination path, and id, and wait for an explicit yes.

- [ ] **Step 2: Run the promotion**

```bash
promote_nested_project \
  "hadassah-seo-tech/вся техничка:работа с подрядчиком" \
  "hadassah-seo-tech-contractor" \
  "Hadassah SEO Tech — Contractor" \
  "work, hadassah, seo, technical, contractor" \
  "$(sed -n "/^## hadassah-seo-tech-contractor$/,/^$/p" "$CARD_CONTENT" | sed -n "s/^Purpose: //p")" \
  "$(sed -n "/^## hadassah-seo-tech-contractor$/,/^$/p" "$CARD_CONTENT" | sed -n "s/^Typical tasks: //p")"
```

- [ ] **Step 3: Verify**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
ls "$HUB/projects/hadassah-seo-tech-contractor"
git -C "$HUB/projects/hadassah-seo-tech-contractor" log --oneline -1
bash "$HUB/scripts/check-hub-registry.sh" "$HUB"
```

Expected: `Registry check passed: 25 projects`.

- [ ] **Step 4: Commit the container and the hub**

```bash
cd /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/hadassah-seo-tech
git add -A && git commit -m "refactor: promote contractor workspace to its own project" && git push origin main
cd /Users/zykovsrg/Documents/vibecode/_ai-hub
git add ai/project-registry.md ai/project-cards/hadassah-seo-tech-contractor.md
git commit -m "feat: register hadassah-seo-tech-contractor"
```

---

### Task 4b: Move the archived predecessor into the promoted contractor project

**Files:**
- Move: `projects/hadassah-seo-tech/archive/` → `projects/hadassah-seo-tech-contractor/archive/`
- Modify: `projects/hadassah-seo-tech-contractor/archive/README.md`, `projects/hadassah-seo-tech-contractor/archive/inp-may/ai/current-task.md`, `projects/hadassah-seo-tech-contractor/ai/changelog.md`

**Why this task exists:** Task 1 found a seventh nested project, `hadassah-seo-tech/archive/inp-may/`, missed by the original survey because it sits one level deeper than the others. `archive/README.md` records that it is the abandoned predecessor of the contractor workspace: work moved there on 2026-07-13 and it holds no unique content. Its history therefore belongs with the contractor project, and moving it there keeps every cross-reference inside a single project instead of turning it into a cross-project link the hub forbids following.

- [ ] **Step 1: Move the archive directory with the workspace**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
mv "$HUB/projects/hadassah-seo-tech/archive" "$HUB/projects/hadassah-seo-tech-contractor/archive"
ls "$HUB/projects/hadassah-seo-tech-contractor/archive"
```

Expected: `README.md` and `inp-may`.

- [ ] **Step 2: Shorten the now-internal relative paths**

Inside the promoted project, the contractor workspace is no longer a sibling of `archive/` — it is the project root. Rewrite the references accordingly:

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
P="$HUB/projects/hadassah-seo-tech-contractor"
grep -rn 'вся техничка:работа с подрядчиком' "$P/archive" "$P/ai"
```

For each hit, replace the path `../вся техничка:работа с подрядчиком/` (and any longer form of it) with `../../` when the reference points at the project root from inside `archive/inp-may/`, or with `../` when it points at the root from `archive/README.md`. Where the text names the workspace rather than pointing at a path, replace the folder name with the project id `hadassah-seo-tech-contractor`. Do not change any other wording.

- [ ] **Step 3: Move the lineage entry in the container's changelog**

`projects/hadassah-seo-tech/ai/changelog.md` describes archiving `inp-may/`. That history now belongs to the promoted project. Copy those entries into `projects/hadassah-seo-tech-contractor/ai/changelog.md` under a dated entry, and leave a one-line pointer in the container's changelog saying the archive moved with the contractor workspace on 2026-08-15.

- [ ] **Step 4: Verify no reference escapes the project**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
grep -rn 'вся техничка' "$HUB/projects/hadassah-seo-tech-contractor" | grep -v '^Binary'
```

Expected: no path-style hits remain; only prose mentions, if any. Then confirm nothing in the promoted project points outside it:

```bash
grep -rn '\.\./\.\./\.\.' "$HUB/projects/hadassah-seo-tech-contractor" | head
```

Expected: no output.

- [ ] **Step 5: Commit both projects**

```bash
cd /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/hadassah-seo-tech-contractor
git add -A && git commit -m "chore: bring the archived predecessor workspace along" && git push origin main
cd /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/hadassah-seo-tech
git add -A && git commit -m "chore: hand the archive to the promoted contractor project" && git push origin main
```

---

### Task 5: Archive the emptied `hadassah-seo-tech`

**Files:**
- Modify: `ai/project-registry.md`, `ai/project-cards/hadassah-seo-tech.md`

- [ ] **Step 1: Confirm the container is empty of project content**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
ls -a "$HUB/projects/hadassah-seo-tech"
```

Expected after Task 4b: only `.git`, `.gitignore`, `ai`, `knowledge`, and possibly `.DS_Store`. `archive/` is gone — it travelled to `hadassah-seo-tech-contractor`. If any nested project directory remains, stop.

- [ ] **Step 2: Set the status in both places**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
perl -0pi -e 's/(## hadassah-seo-tech\nName: [^\n]*\nType: [^\n]*\n)Status: active/${1}Status: archived/' \
  "$HUB/ai/project-registry.md"
perl -pi -e 's/^Status: active$/Status: archived/' \
  "$HUB/ai/project-cards/hadassah-seo-tech.md"
```

- [ ] **Step 3: Verify both records agree**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
grep -A 3 '^## hadassah-seo-tech$' "$HUB/ai/project-registry.md"
grep '^Status:' "$HUB/ai/project-cards/hadassah-seo-tech.md"
bash "$HUB/scripts/check-hub-registry.sh" "$HUB"
```

Expected: both show `archived`, and the registry check passes. An archived project is exempt from the required-memory-file check, so this must not introduce an error.

- [ ] **Step 4: Commit**

```bash
cd /Users/zykovsrg/Documents/vibecode/_ai-hub
git add ai/project-registry.md ai/project-cards/hadassah-seo-tech.md
git commit -m "chore: archive the emptied hadassah-seo-tech container"
```

---

### Task 6: Promote `кц:онкология`

**Files:**
- Move: `projects/hadassah-content/кц:онкология` → `projects/hadassah-content-oncology`
- Modify: `ai/project-registry.md`; Create: `ai/project-cards/hadassah-content-oncology.md`

- [ ] **Step 1: Get the per-project confirmation**

Show the exact source path, destination path, and id, and wait for an explicit yes.

- [ ] **Step 2: Run the promotion**

```bash
promote_nested_project \
  "hadassah-content/кц:онкология" \
  "hadassah-content-oncology" \
  "Hadassah Content — Oncology" \
  "work, hadassah, content, oncology" \
  "$(sed -n "/^## hadassah-content-oncology$/,/^$/p" "$CARD_CONTENT" | sed -n "s/^Purpose: //p")" \
  "$(sed -n "/^## hadassah-content-oncology$/,/^$/p" "$CARD_CONTENT" | sed -n "s/^Typical tasks: //p")"
```

- [ ] **Step 3: Verify**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
ls "$HUB/projects/hadassah-content-oncology"
git -C "$HUB/projects/hadassah-content-oncology" log --oneline -1
bash "$HUB/scripts/check-hub-registry.sh" "$HUB"
```

Expected: `Registry check passed: 26 projects`.

- [ ] **Step 4: Commit the container and the hub**

```bash
cd /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/hadassah-content
git add -A && git commit -m "refactor: promote oncology workspace to its own project" && git push origin main
cd /Users/zykovsrg/Documents/vibecode/_ai-hub
git add ai/project-registry.md ai/project-cards/hadassah-content-oncology.md
git commit -m "feat: register hadassah-content-oncology"
```

---

### Task 7: Promote `цк:детская хирургия`

**Files:**
- Move: `projects/hadassah-content/цк:детская хирургия` → `projects/hadassah-content-pediatric-surgery`
- Modify: `ai/project-registry.md`; Create: `ai/project-cards/hadassah-content-pediatric-surgery.md`

- [ ] **Step 1: Get the per-project confirmation**

Show the exact source path, destination path, and id, and wait for an explicit yes.

- [ ] **Step 2: Run the promotion**

```bash
promote_nested_project \
  "hadassah-content/цк:детская хирургия" \
  "hadassah-content-pediatric-surgery" \
  "Hadassah Content — Pediatric Surgery" \
  "work, hadassah, content, pediatric-surgery" \
  "$(sed -n "/^## hadassah-content-pediatric-surgery$/,/^$/p" "$CARD_CONTENT" | sed -n "s/^Purpose: //p")" \
  "$(sed -n "/^## hadassah-content-pediatric-surgery$/,/^$/p" "$CARD_CONTENT" | sed -n "s/^Typical tasks: //p")"
```

- [ ] **Step 3: Verify**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
ls "$HUB/projects/hadassah-content-pediatric-surgery"
git -C "$HUB/projects/hadassah-content-pediatric-surgery" log --oneline -1
bash "$HUB/scripts/check-hub-registry.sh" "$HUB"
```

Expected: `Registry check passed: 27 projects`.

- [ ] **Step 4: Commit the container and the hub**

```bash
cd /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/hadassah-content
git add -A && git commit -m "refactor: promote pediatric surgery workspace to its own project" && git push origin main
cd /Users/zykovsrg/Documents/vibecode/_ai-hub
git add ai/project-registry.md ai/project-cards/hadassah-content-pediatric-surgery.md
git commit -m "feat: register hadassah-content-pediatric-surgery"
```

---

### Task 8: Promote `цк:центр коррекции веса и метаболизма`

**Files:**
- Move: `projects/hadassah-content/цк:центр коррекции веса и метаболизма` → `projects/hadassah-content-weight-metabolism`
- Modify: `ai/project-registry.md`; Create: `ai/project-cards/hadassah-content-weight-metabolism.md`

- [ ] **Step 1: Get the per-project confirmation**

Show the exact source path, destination path, and id, and wait for an explicit yes.

- [ ] **Step 2: Run the promotion**

```bash
promote_nested_project \
  "hadassah-content/цк:центр коррекции веса и метаболизма" \
  "hadassah-content-weight-metabolism" \
  "Hadassah Content — Weight And Metabolism" \
  "work, hadassah, content, weight, metabolism" \
  "$(sed -n "/^## hadassah-content-weight-metabolism$/,/^$/p" "$CARD_CONTENT" | sed -n "s/^Purpose: //p")" \
  "$(sed -n "/^## hadassah-content-weight-metabolism$/,/^$/p" "$CARD_CONTENT" | sed -n "s/^Typical tasks: //p")"
```

- [ ] **Step 3: Verify**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
ls "$HUB/projects/hadassah-content-weight-metabolism"
git -C "$HUB/projects/hadassah-content-weight-metabolism" log --oneline -1
bash "$HUB/scripts/check-hub-registry.sh" "$HUB"
```

Expected: `Registry check passed: 28 projects`.

- [ ] **Step 4: Commit the container and the hub**

```bash
cd /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/hadassah-content
git add -A && git commit -m "refactor: promote weight and metabolism workspace to its own project" && git push origin main
cd /Users/zykovsrg/Documents/vibecode/_ai-hub
git add ai/project-registry.md ai/project-cards/hadassah-content-weight-metabolism.md
git commit -m "feat: register hadassah-content-weight-metabolism"
```

---

### Task 9: Archive the emptied `hadassah-content`

**Files:**
- Modify: `ai/project-registry.md`, `ai/project-cards/hadassah-content.md`

- [ ] **Step 1: Confirm the container is empty of project content**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
ls -a "$HUB/projects/hadassah-content"
```

Expected: only `.git`, `.gitignore`, `ai`, `knowledge`, and possibly `.DS_Store`.

- [ ] **Step 2: Set the status in both places**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
perl -0pi -e 's/(## hadassah-content\nName: [^\n]*\nType: [^\n]*\n)Status: active/${1}Status: archived/' \
  "$HUB/ai/project-registry.md"
perl -pi -e 's/^Status: active$/Status: archived/' \
  "$HUB/ai/project-cards/hadassah-content.md"
```

- [ ] **Step 3: Verify**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
grep -A 3 '^## hadassah-content$' "$HUB/ai/project-registry.md"
grep '^Status:' "$HUB/ai/project-cards/hadassah-content.md"
bash "$HUB/scripts/check-hub-registry.sh" "$HUB"
```

Expected: both `archived`, `Registry check passed: 28 projects`.

- [ ] **Step 4: Commit**

```bash
cd /Users/zykovsrg/Documents/vibecode/_ai-hub
git add ai/project-registry.md ai/project-cards/hadassah-content.md
git commit -m "chore: archive the emptied hadassah-content container"
```

---

### Task 10: Final verification and push

**Files:**
- Modify: `ai/active-project.md` if it still names a promoted or archived path

- [ ] **Step 1: Check the active-project record**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
cat "$HUB/ai/active-project.md"
```

If it names a path that no longer exists, ask the user which project should be recorded, then update it. Do not guess.

- [ ] **Step 2: Verify every new project is complete**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
for id in hadassah-seo-audit-jul hadassah-seo-tech-contractor hadassah-content-oncology \
  hadassah-content-pediatric-surgery hadassah-content-weight-metabolism; do
  printf '%-40s git:%s remote:%s card:%s\n' "$id" \
    "$([ -d "$HUB/projects/$id/.git" ] && echo y || echo N)" \
    "$(git -C "$HUB/projects/$id" remote get-url origin >/dev/null 2>&1 && echo y || echo N)" \
    "$([ -f "$HUB/ai/project-cards/$id.md" ] && echo y || echo N)"
done
bash "$HUB/scripts/check-hub-registry.sh" "$HUB"
```

Expected: five rows of `y y y` (a `remote:N` is acceptable only if Step 2 of that task reported `pending-sync`), and `Registry check passed: 28 projects`.

- [ ] **Step 3: Confirm no nested project memory remains**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
find "$HUB/projects" -mindepth 3 -maxdepth 3 -type d -name ai \
  -not -path "*/ai-dev-architecture/*"
```

Expected: no output. Hits under `ai-dev-architecture` are its `template/` and `hub-template/` and are correct.

- [ ] **Step 4: Push everything**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
git -C "$HUB" push origin main
for id in hadassah-analytics hadassah-seo-tech hadassah-content; do
  git -C "$HUB/projects/$id" push origin main
done
```

- [ ] **Step 5: Record the change in the hub**

Append to the hub's own history by committing the registry state already pushed; then report to the user: five projects promoted, one flattened, two archived, registry at 28.

---

## Notes for the implementer

- Source directory names contain `:` and spaces. Always quote them. `:` is legal in a macOS directory name but is displayed as `/` in Finder — the ASCII destination slugs exist to end that.
- The nested directories have no `.git` of their own; their history lives in the container repository, which is why the containers are archived rather than deleted. Do not attempt to extract history.
- If `gh repo create` fails, the local repository is still valid. Report `pending-sync` and continue; do not retry against an existing remote.
- `hadassah-seo-planner` is missing its `task-intake` skill (an incomplete standalone install). That is out of scope here and recorded in the spec.
