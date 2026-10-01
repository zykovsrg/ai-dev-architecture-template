# Hub Skill Namespace Implementation Plan (Part A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every hub-owned skill a `hub-` prefix so it can never collide with a project-owned skill of the same name, and make the updater able to remove the superseded paths that the rename leaves behind in already-installed hubs.

**Architecture:** `update-installed-hub.sh` gains an explicit `SUPERSEDED_PATHS` list and confirmation-gated removal. Once removal exists, the fifteen hub skills are renamed in `hub-template/`, their old paths are added to `SUPERSEDED_PATHS`, and the live hub is renamed to match. Two guards then make the collision unrepresentable: `check-consistency.sh` rejects an unprefixed skill in the template, and `check-hub-registry.sh` rejects one in an installed hub, which is also how a half-finished update gets caught.

**Tech Stack:** POSIX-ish bash (macOS bash 3.2 compatible — no `mapfile`, no associative arrays), Markdown rule files, existing script-based test suites (`check-consistency.sh`, `hub-smoke-test.sh`, `smoke-test.sh`).

## Global Constraints

- Repository: `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture`. Live hub: `/Users/zykovsrg/Documents/vibecode/_ai-hub`.
- macOS bash 3.2 compatible: no `mapfile`, no associative arrays.
- Persistent AI-facing instruction content is written in English.
- Hub architecture version ends at `Version: 1.3` in both `hub-template/ai/architecture.md` and the live hub's `ai/architecture.md`.
- All fifteen hub skills get the `hub-` prefix — no exceptions.
- Removal is driven by an explicit path list only. Never "delete whatever is absent from the template".
- `SUPERSEDED_PATHS` must never intersect hub memory files (`ai/allowed-roots.md`, `ai/active-project.md`, `ai/project-registry.md`, `ai/cross-project-signals.md`, `ai/project-cards/*`, `ai/archive/*`) or `PROTECTED_FILES`.
- The full check set after every task: `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, `bash scripts/smoke-test.sh`, and `bash /Users/zykovsrg/Documents/vibecode/_ai-hub/scripts/check-hub-registry.sh /Users/zykovsrg/Documents/vibecode/_ai-hub`.
- The fifteen hub skill names, in full: `environment-check`, `info-update`, `knowledge-capture`, `knowledge-enable`, `knowledge-review`, `local-router-install`, `project-create`, `project-migrate`, `project-register`, `project-router`, `project-switch`, `registry-check`, `task-finish`, `task-intake`, `task-switch`.

---

## File Structure

| File | Responsibility after this plan |
|---|---|
| `scripts/update-installed-hub.sh` | Copies protected files, creates missing memory templates, **and removes an explicit list of superseded paths after confirmation** |
| `scripts/check-consistency.sh` | Template-side invariants; gains the `hub-` prefix rule and the `SUPERSEDED_PATHS` non-intersection rule |
| `scripts/check-hub-registry.sh` | Installed-hub invariants; gains the `hub-` prefix rule (detects a stale directory left by a partial update) |
| `scripts/hub-smoke-test.sh` | Regression coverage for removal behaviour and the installed-hub prefix guard |
| `hub-template/ai/skills/hub-*/SKILL.md` | The fifteen renamed hub skills |
| `hub-template/ai/architecture.md`, `hub-template/CLAUDE.md`, `hub-template/AGENTS.md` | Rule text referencing the prefixed names |

---

### Task 1: Superseded-path preview in dry-run

**Files:**
- Modify: `scripts/update-installed-hub.sh`
- Test: `scripts/hub-smoke-test.sh`

**Interfaces:**
- Produces: `SUPERSEDED_PATHS` array (hub-relative paths, initially empty); `for_each_superseded_path <callback>`; `show_superseded_path <rel>`.

- [ ] **Step 1: Write the failing test**

Add near the other updater assertions in `scripts/hub-smoke-test.sh` (after the `hub-dry-run.out` block around line 1184):

```bash
# A superseded path present in the hub is announced in dry-run and not removed.
SUPERSEDED_PREVIEW="$TMP_DIR/superseded-preview-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_PREVIEW"
mkdir -p "$SUPERSEDED_PREVIEW/ai/skills/legacy-fixture-skill"
printf '%s\n' '# Legacy fixture' > "$SUPERSEDED_PREVIEW/ai/skills/legacy-fixture-skill/SKILL.md"
SUPERSEDED_TEST_SOURCE=1 bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_PREVIEW" --source "$ROOT" --dry-run \
  > "$TMP_DIR/superseded-preview.out" 2>&1
assert_contains "$TMP_DIR/superseded-preview.out" 'Superseded paths to remove:'
assert_contains "$TMP_DIR/superseded-preview.out" 'ai/skills/legacy-fixture-skill/SKILL.md'
assert_file "$SUPERSEDED_PREVIEW/ai/skills/legacy-fixture-skill/SKILL.md"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/hub-smoke-test.sh`
Expected: FAIL with `expected 'Superseded paths to remove:' in .../superseded-preview.out`

- [ ] **Step 3: Write minimal implementation**

In `scripts/update-installed-hub.sh`, directly after the `MEMORY_FILES=( ... )` array (around line 193), add:

```bash
# Paths removed from an installed hub because they were renamed or retired
# upstream. Explicit list only — never "delete whatever the template lacks".
SUPERSEDED_PATHS=()
if [ -n "${SUPERSEDED_TEST_SOURCE:-}" ]; then
  SUPERSEDED_PATHS=(
    "ai/skills/legacy-fixture-skill/SKILL.md"
  )
fi

for_each_superseded_path() {
  local callback="$1" rel
  for rel in ${SUPERSEDED_PATHS[@]+"${SUPERSEDED_PATHS[@]}"}; do
    "$callback" "$rel"
  done
}

show_superseded_path() {
  local rel="$1"
  [ -e "$HUB_DIR/$rel" ] || return 0
  changes_found=1
  echo "  $rel"
}
```

Then, inside the `if [ "$MODE" = "dry-run" ]` block, after the
`for_each_memory_file show_missing_memory_file` line, add:

```bash
  echo ""
  echo "Superseded paths to remove:"
  for_each_superseded_path show_superseded_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash scripts/hub-smoke-test.sh`
Expected: `Hub smoke tests passed.`

- [ ] **Step 5: Commit**

```bash
git add scripts/update-installed-hub.sh scripts/hub-smoke-test.sh
git commit -m "feat: preview superseded hub paths in dry-run"
```

---

### Task 2: Superseded-path removal in apply mode, with guards

**Files:**
- Modify: `scripts/update-installed-hub.sh`
- Test: `scripts/hub-smoke-test.sh`

**Interfaces:**
- Consumes: `SUPERSEDED_PATHS`, `for_each_superseded_path` from Task 1.
- Produces: `remove_superseded_path <rel>`, which deletes `$HUB_DIR/$rel` after validating it.

- [ ] **Step 1: Write the failing test**

Append to `scripts/hub-smoke-test.sh` after the Task 1 block:

```bash
# Apply mode removes the superseded path.
SUPERSEDED_APPLY="$TMP_DIR/superseded-apply-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_APPLY"
mkdir -p "$SUPERSEDED_APPLY/ai/skills/legacy-fixture-skill"
printf '%s\n' '# Legacy fixture' > "$SUPERSEDED_APPLY/ai/skills/legacy-fixture-skill/SKILL.md"
SUPERSEDED_TEST_SOURCE=1 bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_APPLY" --source "$ROOT" --apply --allow-dirty \
  > "$TMP_DIR/superseded-apply.out" 2>&1
assert_contains "$TMP_DIR/superseded-apply.out" 'Removed superseded path: ai/skills/legacy-fixture-skill/SKILL.md'
assert_not_exists "$SUPERSEDED_APPLY/ai/skills/legacy-fixture-skill/SKILL.md"

# A symlinked superseded path is refused, not followed.
SUPERSEDED_SYMLINK="$TMP_DIR/superseded-symlink-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_SYMLINK"
printf '%s\n' 'MUST_NOT_BE_REMOVED' > "$TMP_DIR/superseded-outside-target.md"
mkdir -p "$SUPERSEDED_SYMLINK/ai/skills/legacy-fixture-skill"
ln -s "$TMP_DIR/superseded-outside-target.md" \
  "$SUPERSEDED_SYMLINK/ai/skills/legacy-fixture-skill/SKILL.md"
if SUPERSEDED_TEST_SOURCE=1 bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_SYMLINK" --source "$ROOT" --apply --allow-dirty \
  > "$TMP_DIR/superseded-symlink.out" 2>&1; then
  fail 'updater removed a symlinked superseded path'
fi
assert_contains "$TMP_DIR/superseded-symlink.out" 'superseded path must not be a symlink'
assert_file "$TMP_DIR/superseded-outside-target.md"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/hub-smoke-test.sh`
Expected: FAIL with `expected 'Removed superseded path: ...' in .../superseded-apply.out`

- [ ] **Step 3: Write minimal implementation**

In `scripts/update-installed-hub.sh`, add next to `show_superseded_path`:

```bash
remove_superseded_path() {
  local rel="$1" target="$HUB_DIR/$rel"

  case "$rel" in
    /*|*..*) die "superseded path must be hub-relative without traversal: $rel" ;;
  esac
  [ ! -L "$target" ] || die "superseded path must not be a symlink: $rel"
  [ -e "$target" ] || return 0

  rm -rf "$target"
  echo "Removed superseded path: $rel"
}
```

Then, in apply mode, immediately after the `for_each_memory_file copy_missing_memory_file` line, add:

```bash
for_each_superseded_path remove_superseded_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash scripts/hub-smoke-test.sh`
Expected: `Hub smoke tests passed.`

- [ ] **Step 5: Commit**

```bash
git add scripts/update-installed-hub.sh scripts/hub-smoke-test.sh
git commit -m "feat: remove superseded hub paths on apply"
```

---

### Task 3: Consistency guard — superseded paths never touch hub memory

**Files:**
- Modify: `scripts/check-consistency.sh`

**Interfaces:**
- Consumes: `SUPERSEDED_PATHS` from `scripts/update-installed-hub.sh`, read via the existing `extract_array` helper.

- [ ] **Step 1: Write the failing check by mutation**

Temporarily add a memory path to the array in `scripts/update-installed-hub.sh`:

```bash
SUPERSEDED_PATHS=(
  "ai/project-registry.md"
)
```

- [ ] **Step 2: Run the checker to verify it does not catch this yet**

Run: `bash scripts/check-consistency.sh`
Expected: exits `0` — the dangerous entry passes unnoticed. This is the gap being closed.

- [ ] **Step 3: Write the implementation**

In `scripts/check-consistency.sh`, immediately after the existing `hub_classes_ok` block that prints `OK [hub update classes]`, add:

```bash
hub_superseded="$(extract_array scripts/update-installed-hub.sh SUPERSEDED_PATHS)"
hub_superseded_ok=1
while IFS= read -r superseded_path; do
  [ -n "$superseded_path" ] || continue
  if printf '%s\n' "$hub_memory" | grep -Fxq "$superseded_path" \
    || printf '%s\n' "$hub_protected" | grep -Fxq "$superseded_path"; then
    echo "OVERLAP [hub superseded paths] — $superseded_path is hub memory or a protected file"
    fail=1
    hub_superseded_ok=0
  fi
done <<EOF
$hub_superseded
EOF
[ "$hub_superseded_ok" -eq 0 ] \
  || echo "OK [hub superseded paths] — removals exclude hub memory and protected files"
```

- [ ] **Step 4: Run the checker to verify it now catches the mutation**

Run: `bash scripts/check-consistency.sh`
Expected: FAIL with `OVERLAP [hub superseded paths] — ai/project-registry.md is hub memory or a protected file`

- [ ] **Step 5: Revert the mutation and confirm green**

Restore `SUPERSEDED_PATHS=()` in `scripts/update-installed-hub.sh`, then run:

Run: `bash scripts/check-consistency.sh`
Expected: `OK [hub superseded paths] — removals exclude hub memory and protected files` and exit `0`

- [ ] **Step 6: Commit**

```bash
git add scripts/check-consistency.sh
git commit -m "test: reject superseded paths that touch hub memory"
```

---

### Task 4: Rename the fifteen hub skills in the template

**Files:**
- Rename: `hub-template/ai/skills/<name>/` → `hub-template/ai/skills/hub-<name>/` for all fifteen
- Modify: each renamed `SKILL.md`, `hub-template/ai/architecture.md`, `hub-template/CLAUDE.md`, `hub-template/AGENTS.md`, `scripts/check-consistency.sh`, `scripts/hub-smoke-test.sh`, `scripts/update-installed-hub.sh`, `docs/`, `getting-started/`

**Interfaces:**
- Produces: the fifteen prefixed skill directory names used by every later task.

- [ ] **Step 1: Rename the directories**

```bash
cd hub-template/ai/skills
for name in environment-check info-update knowledge-capture knowledge-enable \
  knowledge-review local-router-install project-create project-migrate \
  project-register project-router project-switch registry-check task-finish \
  task-intake task-switch; do
  git mv "$name" "hub-$name"
done
cd -
```

- [ ] **Step 2: Run the checks to see exactly what breaks**

Run: `bash scripts/check-consistency.sh`
Expected: FAIL with `MISSING [hub skill references] — project-router` and one line per remaining name.

- [ ] **Step 3: Update every reference**

```bash
for name in environment-check info-update knowledge-capture knowledge-enable \
  knowledge-review local-router-install project-create project-migrate \
  project-register project-router project-switch registry-check task-finish \
  task-intake task-switch; do
  grep -rlZ --include='*.md' --include='*.sh' -e "\`$name\`" -e "skills/$name" \
    -e "name: $name" hub-template scripts docs getting-started 2>/dev/null \
  | xargs -0 -r perl -pi -e "
      s/\`\Q$name\E\`/\`hub-$name\`/g;
      s{skills/\Q$name\E/}{skills/hub-$name/}g;
      s/^name: \Q$name\E\$/name: hub-$name/m;
    "
done
```

Then fix the two lists that name skills as bare words rather than in backticks:

In `scripts/check-consistency.sh`:

```bash
HUB_REQUIRED_SKILLS="hub-project-router hub-project-switch hub-project-register hub-project-create hub-project-migrate hub-registry-check hub-info-update hub-local-router-install hub-environment-check hub-task-intake hub-task-switch hub-task-finish hub-knowledge-enable hub-knowledge-capture hub-knowledge-review"
```

In `scripts/update-installed-hub.sh`, inside `validate_source_template`:

```bash
  for mandatory_skill in hub-project-router hub-project-switch hub-project-register hub-registry-check hub-knowledge-capture hub-knowledge-review; do
```

In `scripts/hub-smoke-test.sh`, the skill loop:

```bash
for skill in hub-project-router hub-project-switch hub-project-register hub-project-create hub-project-migrate hub-registry-check hub-environment-check hub-task-intake hub-task-switch hub-task-finish hub-knowledge-enable hub-knowledge-capture hub-knowledge-review; do
```

- [ ] **Step 4: Verify no bare references survive**

Run:

```bash
grep -rn --include='*.md' --include='*.sh' -E '(`|skills/)(environment-check|info-update|knowledge-capture|knowledge-enable|knowledge-review|local-router-install|project-create|project-migrate|project-register|project-router|project-switch|registry-check|task-finish|task-intake|task-switch)\b' hub-template scripts docs getting-started
```

Expected: no output. Any hit is a missed reference — fix it before continuing.

Note: `template/` (the standalone template) must NOT be touched. Its skills keep their unprefixed names; that is the whole point of the rename.

- [ ] **Step 5: Run the full check set**

Run: `bash scripts/check-consistency.sh && bash scripts/hub-smoke-test.sh && bash scripts/smoke-test.sh`
Expected: all three exit `0`.

- [ ] **Step 6: Commit**

```bash
git add -A hub-template scripts docs getting-started
git commit -m "refactor: prefix hub-owned skills with hub-"
```

---

### Task 5: Register the old paths as superseded and bump the version

**Files:**
- Modify: `scripts/update-installed-hub.sh`, `hub-template/ai/architecture.md`

**Interfaces:**
- Consumes: `SUPERSEDED_PATHS` from Task 1, the renamed directories from Task 4.

- [ ] **Step 1: Populate the array**

Replace the placeholder block in `scripts/update-installed-hub.sh` with the real list and delete the `SUPERSEDED_TEST_SOURCE` fixture branch:

```bash
SUPERSEDED_PATHS=(
  "ai/skills/environment-check"
  "ai/skills/info-update"
  "ai/skills/knowledge-capture"
  "ai/skills/knowledge-enable"
  "ai/skills/knowledge-review"
  "ai/skills/local-router-install"
  "ai/skills/project-create"
  "ai/skills/project-migrate"
  "ai/skills/project-register"
  "ai/skills/project-router"
  "ai/skills/project-switch"
  "ai/skills/registry-check"
  "ai/skills/task-finish"
  "ai/skills/task-intake"
  "ai/skills/task-switch"
)
```

- [ ] **Step 2: Point the smoke-test fixtures at a real superseded path**

The entries are now *directories*, not files, so the fixtures and assertions must
target a directory. In `scripts/hub-smoke-test.sh`, drop every
`SUPERSEDED_TEST_SOURCE=1 ` prefix and rewrite the three fixtures as:

```bash
# A superseded path present in the hub is announced in dry-run and not removed.
SUPERSEDED_PREVIEW="$TMP_DIR/superseded-preview-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_PREVIEW"
mkdir -p "$SUPERSEDED_PREVIEW/ai/skills/task-intake"
printf '%s\n' '# Legacy fixture' > "$SUPERSEDED_PREVIEW/ai/skills/task-intake/SKILL.md"
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_PREVIEW" --source "$ROOT" --dry-run \
  > "$TMP_DIR/superseded-preview.out" 2>&1
assert_contains "$TMP_DIR/superseded-preview.out" 'Superseded paths to remove:'
assert_contains "$TMP_DIR/superseded-preview.out" 'ai/skills/task-intake'
assert_file "$SUPERSEDED_PREVIEW/ai/skills/task-intake/SKILL.md"

# Apply mode removes the superseded directory.
SUPERSEDED_APPLY="$TMP_DIR/superseded-apply-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_APPLY"
mkdir -p "$SUPERSEDED_APPLY/ai/skills/task-intake"
printf '%s\n' '# Legacy fixture' > "$SUPERSEDED_APPLY/ai/skills/task-intake/SKILL.md"
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_APPLY" --source "$ROOT" --apply --allow-dirty \
  > "$TMP_DIR/superseded-apply.out" 2>&1
assert_contains "$TMP_DIR/superseded-apply.out" 'Removed superseded path: ai/skills/task-intake'
assert_not_exists "$SUPERSEDED_APPLY/ai/skills/task-intake"

# A symlinked superseded path is refused, not followed.
SUPERSEDED_SYMLINK="$TMP_DIR/superseded-symlink-hub"
cp -R "$HUB_INSTALL" "$SUPERSEDED_SYMLINK"
mkdir -p "$TMP_DIR/superseded-outside-dir"
printf '%s\n' 'MUST_NOT_BE_REMOVED' > "$TMP_DIR/superseded-outside-dir/SKILL.md"
ln -s "$TMP_DIR/superseded-outside-dir" "$SUPERSEDED_SYMLINK/ai/skills/task-intake"
if bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$SUPERSEDED_SYMLINK" --source "$ROOT" --apply --allow-dirty \
  > "$TMP_DIR/superseded-symlink.out" 2>&1; then
  fail 'updater removed a symlinked superseded path'
fi
assert_contains "$TMP_DIR/superseded-symlink.out" 'superseded path must not be a symlink'
assert_file "$TMP_DIR/superseded-outside-dir/SKILL.md"
```

- [ ] **Step 3: Bump the version**

In `hub-template/ai/architecture.md` line 3:

```markdown
Version: 1.3
```

- [ ] **Step 4: Run the full check set**

Run: `bash scripts/check-consistency.sh && bash scripts/hub-smoke-test.sh && bash scripts/smoke-test.sh`
Expected: all three exit `0`. `check-consistency.sh` must print `OK [hub superseded paths]`.

- [ ] **Step 5: Commit**

```bash
git add scripts/update-installed-hub.sh scripts/hub-smoke-test.sh hub-template/ai/architecture.md
git commit -m "feat: retire pre-prefix hub skill paths on update"
```

---

### Task 6: Rename the skills in the live installed hub

**Files:**
- Rename: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/skills/<name>/` → `hub-<name>/` for all fifteen
- Modify: the live hub's `CLAUDE.md`, `AGENTS.md`, `ai/architecture.md`

**Interfaces:**
- Consumes: the renamed template from Task 4 and the version bump from Task 5.

- [ ] **Step 1: Copy the four rule files from the template**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
P=$HUB/projects/ai-dev-architecture
cp "$P/hub-template/ai/architecture.md" "$HUB/ai/architecture.md"
cp "$P/hub-template/CLAUDE.md" "$HUB/CLAUDE.md"
cp "$P/hub-template/AGENTS.md" "$HUB/AGENTS.md"
```

- [ ] **Step 2: Rename the live skill directories**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
cd "$HUB/ai/skills"
for name in environment-check info-update knowledge-capture knowledge-enable \
  knowledge-review local-router-install project-create project-migrate \
  project-register project-router project-switch registry-check task-finish \
  task-intake task-switch; do
  git mv "$name" "hub-$name"
done
cd -
```

- [ ] **Step 3: Copy the renamed skill bodies from the template**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
P=$HUB/projects/ai-dev-architecture
for name in environment-check info-update knowledge-capture knowledge-enable \
  knowledge-review local-router-install project-create project-migrate \
  project-register project-router project-switch registry-check task-finish \
  task-intake task-switch; do
  cp "$P/hub-template/ai/skills/hub-$name/SKILL.md" "$HUB/ai/skills/hub-$name/SKILL.md"
done
```

- [ ] **Step 4: Verify the live hub matches the template**

Run:

```bash
diff -r /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/hub-template/ai/skills \
        /Users/zykovsrg/Documents/vibecode/_ai-hub/ai/skills
```

Expected: no output.

- [ ] **Step 5: Run the registry check against the live hub**

Run: `bash /Users/zykovsrg/Documents/vibecode/_ai-hub/scripts/check-hub-registry.sh /Users/zykovsrg/Documents/vibecode/_ai-hub`
Expected: `Registry check passed: 23 projects`

- [ ] **Step 6: Commit in the hub repository**

```bash
cd /Users/zykovsrg/Documents/vibecode/_ai-hub
git add -A
git commit -m "refactor: prefix hub-owned skills with hub-"
```

---

### Task 7: Template guard — every hub skill directory carries the prefix

**Files:**
- Modify: `scripts/check-consistency.sh`

- [ ] **Step 1: Write the implementation**

In `scripts/check-consistency.sh`, immediately after the `OK [hub skill references]` block, add:

```bash
hub_prefix_ok=1
if [ -d hub-template/ai/skills ]; then
  while IFS= read -r skill_dir; do
    case "$(basename "$skill_dir")" in
      hub-*) ;;
      *)
        echo "MISMATCH [hub skill prefix] — $skill_dir must be named hub-*"
        fail=1
        hub_prefix_ok=0
        ;;
    esac
  done < <(find hub-template/ai/skills -mindepth 1 -maxdepth 1 -type d | sort)
fi
[ "$hub_prefix_ok" -eq 0 ] \
  || echo "OK [hub skill prefix] — every hub skill directory is prefixed"
```

- [ ] **Step 2: Run the checker to confirm the positive case**

Run: `bash scripts/check-consistency.sh`
Expected: `OK [hub skill prefix] — every hub skill directory is prefixed`, exit `0`

- [ ] **Step 3: Mutation-check the guard**

```bash
mkdir hub-template/ai/skills/unprefixed-fixture
bash scripts/check-consistency.sh; echo "EXIT=$?"
rmdir hub-template/ai/skills/unprefixed-fixture
```

Expected: `MISMATCH [hub skill prefix] — hub-template/ai/skills/unprefixed-fixture must be named hub-*` and `EXIT=1`, then green again after `rmdir`.

- [ ] **Step 4: Commit**

```bash
git add scripts/check-consistency.sh
git commit -m "test: require the hub- prefix on template skills"
```

---

### Task 8: Installed-hub guard — detect a stale unprefixed skill

**Files:**
- Modify: `scripts/check-hub-registry.sh`
- Test: `scripts/hub-smoke-test.sh`

**Interfaces:**
- Produces: `validate_skill_namespace`, called once before `validate_projects_root`.

- [ ] **Step 1: Write the failing test**

Append to `scripts/hub-smoke-test.sh` next to the other `check-hub-registry.sh` fixtures:

```bash
# A leftover unprefixed skill directory means an update did not finish.
STALE_SKILL="$TMP_DIR/stale-skill-hub"
copy_valid_hub "$STALE_SKILL"
mkdir -p "$STALE_SKILL/ai/skills/hub-task-intake" "$STALE_SKILL/ai/skills/task-intake"
if bash "$ROOT/scripts/check-hub-registry.sh" "$STALE_SKILL" \
  > "$TMP_DIR/stale-skill.out" 2>&1; then
  fail 'validator accepted an unprefixed hub skill directory'
fi
assert_contains "$TMP_DIR/stale-skill.out" 'hub skill directory must be named hub-*: ai/skills/task-intake'

# A hub whose skills are all prefixed passes.
FRESH_SKILL="$TMP_DIR/fresh-skill-hub"
copy_valid_hub "$FRESH_SKILL"
mkdir -p "$FRESH_SKILL/ai/skills/hub-task-intake"
bash "$ROOT/scripts/check-hub-registry.sh" "$FRESH_SKILL" > "$TMP_DIR/fresh-skill.out"
assert_contains "$TMP_DIR/fresh-skill.out" 'Registry check passed'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/hub-smoke-test.sh`
Expected: FAIL with `validator accepted an unprefixed hub skill directory`

- [ ] **Step 3: Write the implementation**

In `scripts/check-hub-registry.sh`, add next to `validate_entry_files`:

```bash
# A directory without the hub- prefix is a leftover from a pre-1.3 hub whose
# update did not remove the superseded path.
validate_skill_namespace() {
  local skills_dir="$HUB_DIR/ai/skills" skill_dir
  [ -d "$skills_dir" ] || return 0
  for skill_dir in "$skills_dir"/*/; do
    [ -d "$skill_dir" ] || continue
    case "$(basename "$skill_dir")" in
      hub-*) ;;
      *) die "hub skill directory must be named hub-*: ai/skills/$(basename "$skill_dir")" ;;
    esac
  done
}
```

Call it directly above `validate_projects_root`:

```bash
validate_entry_files
validate_skill_namespace
validate_projects_root
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash scripts/hub-smoke-test.sh`
Expected: `Hub smoke tests passed.`

- [ ] **Step 5: Sync the validator into the live hub and verify**

```bash
HUB=/Users/zykovsrg/Documents/vibecode/_ai-hub
cp scripts/check-hub-registry.sh "$HUB/scripts/check-hub-registry.sh"
bash "$HUB/scripts/check-hub-registry.sh" "$HUB"
```

Expected: `Registry check passed: 23 projects`

- [ ] **Step 6: Mutation-check the guard**

```bash
bash scripts/hub-smoke-test.sh > /dev/null 2>&1; echo "baseline=$?"
perl -pi -e 's/^validate_skill_namespace$/: # disabled/' scripts/check-hub-registry.sh
bash scripts/hub-smoke-test.sh > /dev/null 2>&1; echo "mutant=$? (expect 1)"
git checkout scripts/check-hub-registry.sh
bash scripts/hub-smoke-test.sh > /dev/null 2>&1; echo "restored=$? (expect 0)"
```

- [ ] **Step 7: Commit both repositories**

```bash
git add scripts/check-hub-registry.sh scripts/hub-smoke-test.sh
git commit -m "test: detect stale unprefixed skills in an installed hub"
cd /Users/zykovsrg/Documents/vibecode/_ai-hub
git add scripts/check-hub-registry.sh
git commit -m "test: detect stale unprefixed skills in an installed hub"
```

---

### Task 9: Record the change

**Files:**
- Modify: `CHANGELOG.md`, `ai/changelog.md`

- [ ] **Step 1: Add the release entry**

At the top of `CHANGELOG.md`, below `# Changelog`:

```markdown
## v6.16 — 2026-08-14

- Prefixed all fifteen hub-owned skills with `hub-`. Six of them (`environment-check`, `task-intake`, `task-switch`, `task-finish`, `knowledge-capture`, `knowledge-review`) shared a name with a standalone project skill of different content, leaving skill selection inside a hub-confirmed project undefined. A uniform prefix removes the ambiguity structurally rather than by convention.
- Added `SUPERSEDED_PATHS` and confirmation-gated removal to `update-installed-hub.sh`. Without it the rename would have left the old directories in every installed hub, reproducing the collision under the old names.
- Added three guards: superseded paths may not intersect hub memory or protected files; every template skill directory must carry the prefix; an unprefixed directory in an installed hub is an error that names the stale path.
- Bumped `hub-template/ai/architecture.md` to `1.3`.
```

- [ ] **Step 2: Add the project memory entry**

Under `## Текущий changelog` in `ai/changelog.md`:

```markdown
### 2026-08-14

- Change: Renamed all fifteen hub skills to `hub-*`, added superseded-path removal to the hub updater, and added three guards covering removal safety and the prefix on both the template and installed-hub sides.
- Impact: A hub-owned skill can no longer be confused with a standalone project skill of the same name, and an installed hub that keeps a pre-1.3 skill directory now fails its registry check instead of silently offering two skills under one name.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, `bash scripts/smoke-test.sh`, and `bash scripts/check-hub-registry.sh` against the live hub all passed. The installed-hub prefix guard was mutation-tested.
```

- [ ] **Step 3: Commit and push both repositories**

```bash
git add CHANGELOG.md ai/changelog.md
git commit -m "docs: record hub skill namespace change"
git push origin main
cd /Users/zykovsrg/Documents/vibecode/_ai-hub
git push origin main
```

---

## Notes for the implementer

- Confirmation for removal is the updater's existing gate, not a new prompt: the
  script runs in `dry-run` mode by default and only deletes under `--apply`. Task 1
  puts the removals in the dry-run preview so the operator sees the exact list
  before choosing `--apply`. Do not add a second interactive prompt.

- `template/` is the standalone project template and must keep its unprefixed skill names. Only `hub-template/` is renamed. Task 4 Step 4 exists to catch an accidental edit there.
- The live hub at `_ai-hub` is a working installation, not a fixture. Task 6 changes it directly; run the registry check before committing.
- `ai/` in the architecture repository is listed in `.git/info/exclude`, so this plan file and the spec are not tracked. `ai/changelog.md` and `CHANGELOG.md` are tracked and commit normally.
