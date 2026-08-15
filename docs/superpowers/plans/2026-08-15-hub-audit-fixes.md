# Hub Audit Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the six defects found by the 2026-08-15 architecture audit, so that no check in this repository can report success without having verified anything.

**Architecture:** Four changes to shell scripts (`check-hub-registry.sh`, both updaters) and two changes to protected rule files, plus one new guard in `check-consistency.sh`. Every behavioural change is driven by a test added to the existing smoke-test suites first. The repository has no unit-test framework: `scripts/hub-smoke-test.sh` and `scripts/smoke-test.sh` are the test suites, built from `fail`/`assert_contains`/`assert_not_contains` helpers and disposable fixtures under `$TMP_DIR`.

**Tech Stack:** POSIX-ish bash with `set -euo pipefail`, GNU/BSD coreutils, `perl -pi` for fixture rewrites, git.

**Spec:** `docs/superpowers/specs/2026-08-15-hub-audit-fixes-design.md`

## Global Constraints

- Never read project content. The registry validator may read directory *names* under `projects/` and nothing else. Fixtures assert this: `$SENTINEL` (`MUST_NOT_BE_READ`) must never appear in any captured output.
- The stdout line `Registry check passed: N projects` must stay byte-identical. Warnings go to stderr only.
- The exit code of `check-hub-registry.sh` must stay 0 for an unregistered directory.
- Protected architecture files (`hub-template/ai/architecture.md`, `hub-template/ai/skills/*/SKILL.md`, `CLAUDE.md`, `AGENTS.md`) may only be edited in `architecture-update` mode, after showing exact wording and receiving explicit user confirmation. Tasks 5 and 6 stop and ask before editing.
- `.gitignore` in an installed hub is never overwritten. Only a missing required line is appended.
- Run mutation tests by reverting every mutation and confirming `git status --porcelain` is empty afterwards.
- All work happens in `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture`. The live hub at `/Users/zykovsrg/Documents/vibecode/_ai-hub` is touched only in Task 7.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `scripts/check-hub-registry.sh` | Registry ↔ filesystem validation gate. Gains the reverse direction. | 1 |
| `scripts/update-installed-hub.sh` | Hub updater. Gains absolute source resolution, self-comparison guard, honest `--check` text, `.gitignore` line guarantee. | 2, 3, 4 |
| `scripts/update-installed-architecture.sh` | Standalone updater. Same source-resolution fix. | 2 |
| `scripts/check-consistency.sh` | Cross-layer consistency. Gains the skill-naming guard. | 6 |
| `scripts/hub-smoke-test.sh` | Test suite for hub scripts. Gains four test blocks. | 1, 2, 3, 4 |
| `scripts/smoke-test.sh` | Test suite for standalone scripts. Gains one test block. | 2 |
| `hub-template/ai/architecture.md` | Hub rules. Gains three skill names. | 6 |
| `hub-template/ai/skills/hub-registry-check/SKILL.md` | Registry audit skill. Wording fix. | 5 |

---

### Task 1: Reverse registry check (defect 2)

**Files:**
- Modify: `scripts/check-hub-registry.sh:205-233`
- Test: `scripts/hub-smoke-test.sh` (insert after line 779, following the `Sentinel evidence:` echo for the valid fixture)

**Interfaces:**
- Consumes: the existing `$VALID` fixture, which already contains two unregistered directories (`projects/unregistered-project`, `projects/analytics-seo-backup`, created at `hub-smoke-test.sh:740`) and the `$ids` accumulator built by the registry parsing loop.
- Produces: `WARNING: unregistered directory in projects root: <name>` on stderr. Task 7 relies on this exact string.

- [ ] **Step 1: Write the failing test**

Insert into `scripts/hub-smoke-test.sh` immediately after the line `echo 'Sentinel evidence: validator output and xtrace contain neither the marker nor the named forbidden file paths.'`:

```bash
# The valid fixture intentionally holds two unregistered directories. They must
# be reported on stderr without changing the exit code or the stdout summary,
# and without reading anything inside them.
bash "$ROOT/scripts/check-hub-registry.sh" "$VALID" \
  > "$TMP_DIR/valid-warn.out" 2> "$TMP_DIR/valid-warn.err" \
  || fail 'an unregistered directory must not change the validator exit code'
assert_contains "$TMP_DIR/valid-warn.err" 'WARNING: unregistered directory in projects root: unregistered-project'
assert_contains "$TMP_DIR/valid-warn.err" 'WARNING: unregistered directory in projects root: analytics-seo-backup'
assert_contains "$TMP_DIR/valid-warn.out" 'Registry check passed: 1 projects'
assert_not_contains "$TMP_DIR/valid-warn.out" 'WARNING'
assert_not_contains "$TMP_DIR/valid-warn.err" "$SENTINEL"

# A hub whose projects root holds only registered projects stays silent.
QUIET_HUB="$TMP_DIR/quiet-hub"
copy_valid_hub "$QUIET_HUB"
rm -rf "$QUIET_HUB/projects/unregistered-project" "$QUIET_HUB/projects/analytics-seo-backup"
bash "$ROOT/scripts/check-hub-registry.sh" "$QUIET_HUB" \
  > "$TMP_DIR/quiet.out" 2> "$TMP_DIR/quiet.err" \
  || fail 'clean fixture must pass'
assert_contains "$TMP_DIR/quiet.out" 'Registry check passed: 1 projects'
assert_not_contains "$TMP_DIR/quiet.err" 'WARNING'
echo 'Unregistered-directory evidence: warned on stderr, exit code and stdout summary unchanged.'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/hub-smoke-test.sh`
Expected: FAIL with `expected 'WARNING: unregistered directory in projects root: unregistered-project' in .../valid-warn.err`

- [ ] **Step 3: Write minimal implementation**

In `scripts/check-hub-registry.sh`, add this function immediately before the final `echo "Registry check passed: $project_count projects"` line:

```bash
# Reverse direction: the registry loop above proves every entry has a directory.
# This proves the operator sees directories that have no entry. Names only —
# nothing inside a project is opened. A warning, never an error: the router only
# ever opens registered paths, and hub-project-migrate legitimately leaves a
# moved folder unregistered until its separate registration confirmation.
warn_unregistered_directories() {
  local child name
  for child in "$PROJECTS_ROOT"/*/; do
    [ -d "$child" ] || continue
    name="$(basename "$child")"
    if printf '%s\n' "$ids" | grep -Fxq "$name"; then
      continue
    fi
    echo "WARNING: unregistered directory in projects root: $name" >&2
  done
}

warn_unregistered_directories
```

Note the `if`/`continue` form rather than `grep … && continue`: under `set -e` a failing `grep` as the loop body's last command would abort the script.

- [ ] **Step 4: Run test to verify it passes**

Run: `bash scripts/hub-smoke-test.sh`
Expected: PASS, ending with `Hub smoke tests passed.` and printing `Unregistered-directory evidence: …`

- [ ] **Step 5: Verify the gate still passes on the live hub**

Run: `bash scripts/check-hub-registry.sh /Users/zykovsrg/Documents/vibecode/_ai-hub`
Expected: `Registry check passed: 29 projects`, exit 0, no warnings (all 29 directories are registered).

- [ ] **Step 6: Commit**

```bash
git add scripts/check-hub-registry.sh scripts/hub-smoke-test.sh
git commit -m "fix: warn about unregistered directories in the hub projects root"
```

---

### Task 2: Absolute source resolution and self-comparison guard (defect 1)

**Files:**
- Modify: `scripts/update-installed-hub.sh:95-99` and `:145-149`
- Modify: `scripts/update-installed-architecture.sh:97-101` and `:179-183`
- Test: `scripts/hub-smoke-test.sh` (insert before the line `bash "$ROOT/scripts/update-installed-hub.sh" --hub "$HUB_INSTALL" --source "$ROOT" --dry-run > "$TMP_DIR/hub-dry-run.out"`, currently line 1201)
- Test: `scripts/smoke-test.sh` (insert before line 306, the `$BAD_PROJECT` block)

**Interfaces:**
- Consumes: `$HUB_INSTALL` (an installed hub fixture) and `$ROOT` (this repository) from `hub-smoke-test.sh`; `$PROJECT` and `$ROOT` from `smoke-test.sh`.
- Produces: the error string `resolves to the hub itself` (hub updater) and `resolves to the project itself` (standalone updater).

- [ ] **Step 1: Write the failing tests**

Insert into `scripts/hub-smoke-test.sh` before the `hub-dry-run.out` invocation:

```bash
# Regression: --source must resolve against the caller's directory, not the hub.
# Before this fix a relative --source silently resolved inside the hub, so the
# updater could compare the hub with itself and report "no updates" (Audit 1).
RELATIVE_SOURCE_OUT="$TMP_DIR/relative-source.out"
(cd "$ROOT" && bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$HUB_INSTALL" --source . --dry-run) > "$RELATIVE_SOURCE_OUT" 2>&1
assert_contains "$RELATIVE_SOURCE_OUT" "Source template: $ROOT/hub-template"
assert_not_contains "$RELATIVE_SOURCE_OUT" "Source template: $HUB_INSTALL"

# A source that resolves to the target itself is refused outright.
if bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$HUB_INSTALL" --source "$HUB_INSTALL" --dry-run \
  > "$TMP_DIR/self-source.out" 2>&1; then
  fail 'hub updater compared the hub with itself'
fi
assert_contains "$TMP_DIR/self-source.out" 'resolves to the hub itself'
echo 'Source-resolution evidence: relative --source resolved against the caller, self-source refused.'
```

Insert into `scripts/smoke-test.sh` before the `$BAD_PROJECT` block:

```bash
# Regression: same relative-source defect in the standalone updater (Audit 1).
RELATIVE_SOURCE_OUT="$TMP_DIR/relative-source.out"
(cd "$ROOT" && bash "$ROOT/scripts/update-installed-architecture.sh" \
  --project "$PROJECT" --source . --dry-run) > "$RELATIVE_SOURCE_OUT" 2>&1
assert_not_contains "$RELATIVE_SOURCE_OUT" "Source template: $PROJECT"

if bash "$ROOT/scripts/update-installed-architecture.sh" \
  --project "$PROJECT" --source "$PROJECT" --dry-run \
  > "$TMP_DIR/self-source.out" 2>&1; then
  fail 'standalone updater compared the project with itself'
fi
assert_contains "$TMP_DIR/self-source.out" 'resolves to the project itself'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bash scripts/hub-smoke-test.sh`
Expected: FAIL with `did not expect 'Source template: <HUB_INSTALL>'` — proving the current code resolves `.` against the hub.

Run: `bash scripts/smoke-test.sh`
Expected: FAIL on the same kind of assertion.

- [ ] **Step 3: Resolve the source at parse time in both updaters**

In `scripts/update-installed-hub.sh`, replace lines 95–99:

```bash
    --source)
      shift
      [ "$#" -gt 0 ] || die "--source requires a directory"
      SOURCE_DIR="$1"
      ;;
```

with:

```bash
    --source)
      shift
      [ "$#" -gt 0 ] || die "--source requires a directory"
      # Resolve now, before the script cd's into the hub. A relative path
      # resolved later would be taken relative to the hub, not the caller.
      [ -d "$1" ] || die "--source directory not found: $1"
      SOURCE_DIR="$(cd "$1" && pwd -P)"
      ;;
```

Apply the identical replacement to `scripts/update-installed-architecture.sh` lines 97–101.

- [ ] **Step 4: Drop the now-redundant late resolution**

In `scripts/update-installed-hub.sh`, inside `resolve_source_template`, delete this line:

```bash
    SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
```

Delete the identical line inside `resolve_source_template` in `scripts/update-installed-architecture.sh`.

- [ ] **Step 5: Add the self-comparison guard to the hub updater**

In `scripts/update-installed-hub.sh`, inside `resolve_source_template`, immediately after the `grep -Fqx '# Personal AI Hub Architecture' …` validation and before the `for mandatory_skill` loop, add:

```bash
  # An installed hub is a copy of the template and satisfies every check above,
  # so without this guard the updater can compare the hub with itself and
  # report "no updates" (Audit 1).
  if [ "$(cd "$SOURCE_TEMPLATE" && pwd -P)" = "$(cd "$HUB_DIR" && pwd -P)" ]; then
    die "--source resolves to the hub itself; pass the template repository path"
  fi
```

- [ ] **Step 6: Add the self-comparison guard to the standalone updater**

In `scripts/update-installed-architecture.sh`, inside `resolve_source_template`, immediately after the `SOURCE_TEMPLATE` branch resolves (after the closing `fi` of the `if [ -d "$SOURCE_DIR/template/ai" ]` chain), add:

```bash
  if [ "$(cd "$SOURCE_TEMPLATE" && pwd -P)" = "$(cd "$PROJECT_DIR" && pwd -P)" ]; then
    die "--source resolves to the project itself; pass the template repository path"
  fi
```

- [ ] **Step 7: Run both suites to verify they pass**

Run: `bash scripts/hub-smoke-test.sh`
Expected: PASS, printing `Source-resolution evidence: …`

Run: `bash scripts/smoke-test.sh`
Expected: PASS, ending with `Smoke tests passed.`

- [ ] **Step 8: Commit**

```bash
git add scripts/update-installed-hub.sh scripts/update-installed-architecture.sh scripts/hub-smoke-test.sh scripts/smoke-test.sh
git commit -m "fix: resolve --source before entering the target and refuse self-comparison"
```

---

### Task 3: Honest `--check` output (defect 3)

**Files:**
- Modify: `scripts/update-installed-hub.sh:29-30` (help text) and `:472`
- Modify: `scripts/update-installed-architecture.sh:362`
- Test: `scripts/hub-smoke-test.sh` (insert after the `Source-resolution evidence:` echo added in Task 2)

**Interfaces:**
- Consumes: `$HUB_INSTALL`, already up to date against `$ROOT` at that point in the suite.
- Produces: nothing other tasks depend on. Line 468's existing string `stale superseded paths remain` must survive unchanged — `hub-smoke-test.sh:1368` asserts it.

- [ ] **Step 1: Write the failing test**

Insert into `scripts/hub-smoke-test.sh` after the `Source-resolution evidence:` echo:

```bash
# --check compares version numbers only. Its success message must not read as
# "the files match", because a hub with a matching version and a drifted rule
# file is reported as up to date (Audit 3, FT-20260815-002).
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$HUB_INSTALL" --source "$ROOT" --check > "$TMP_DIR/check-wording.out" 2>&1
assert_contains "$TMP_DIR/check-wording.out" 'Version numbers match'
assert_contains "$TMP_DIR/check-wording.out" '--dry-run'
assert_not_contains "$TMP_DIR/check-wording.out" 'Hub architecture is up to date (v'
echo 'Check-wording evidence: --check states that it compared version numbers only.'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/hub-smoke-test.sh`
Expected: FAIL with `expected 'Version numbers match' in .../check-wording.out`

- [ ] **Step 3: Change the hub updater's success message**

In `scripts/update-installed-hub.sh`, replace line 472:

```bash
    echo "Hub architecture is up to date (v$hub_version)."
```

with:

```bash
    echo "Version numbers match (v$hub_version). This compares the version line only,"
    echo "not file contents. Run --dry-run to compare the files themselves."
```

Leave line 468 (`… but stale superseded paths remain.`) untouched.

- [ ] **Step 4: Change the standalone updater's success message**

In `scripts/update-installed-architecture.sh`, replace line 362:

```bash
    echo "Architecture is up to date (v$project_version)."
```

with:

```bash
    echo "Version numbers match (v$project_version). This compares the version line only,"
    echo "not file contents. Run --dry-run to compare the files themselves."
```

- [ ] **Step 5: Update both help texts**

In `scripts/update-installed-hub.sh`, replace the `--check` help lines (29–30):

```
  --check            Compare the hub architecture version with the source and,
                     if the hub is behind, show a dry-run preview. Never writes.
```

with:

```
  --check            Compare the hub architecture VERSION NUMBER with the source
                     and, if the hub is behind, show a dry-run preview. Does not
                     compare file contents — use --dry-run for that. Never writes.
```

Apply the equivalent wording to the `--check` entry in `scripts/update-installed-architecture.sh`, substituting "project architecture" for "hub architecture".

- [ ] **Step 6: Run both suites to verify they pass**

Run: `bash scripts/hub-smoke-test.sh`
Expected: PASS, printing `Check-wording evidence: …`

Run: `bash scripts/smoke-test.sh`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/update-installed-hub.sh scripts/update-installed-architecture.sh scripts/hub-smoke-test.sh
git commit -m "fix: say that --check compares version numbers, not file contents"
```

---

### Task 4: Guarantee the `/projects/` ignore line (defect 5)

**Files:**
- Modify: `scripts/update-installed-hub.sh` (new step inside the apply path, next to `for_each_memory_file copy_missing_memory_file` near line 521)
- Test: `scripts/hub-smoke-test.sh` (insert after the existing `--apply --allow-dirty` block that produces `$TMP_DIR/hub-update.out`, currently line 1299)

**Interfaces:**
- Consumes: `$HUB_INSTALL` after a successful `--apply`.
- Produces: nothing other tasks depend on.

Do **not** add `.gitignore` to `PROTECTED_FILES`. Protected files are overwritten wholesale by `copy_file`, which would destroy any line the user added to their hub's `.gitignore`.

- [ ] **Step 1: Write the failing test**

Insert into `scripts/hub-smoke-test.sh` after the `--apply --allow-dirty` invocation and its existing assertions:

```bash
# The updater must guarantee the required ignore line without overwriting a
# hub .gitignore that carries the user's own entries (Audit 5).
printf '%s\n' '# user entry' '/scratch/' > "$HUB_INSTALL/.gitignore"
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$HUB_INSTALL" --source "$ROOT" --apply --allow-dirty > "$TMP_DIR/gitignore-update.out"
assert_contains "$HUB_INSTALL/.gitignore" '/projects/'
assert_contains "$HUB_INSTALL/.gitignore" '# user entry'
assert_contains "$HUB_INSTALL/.gitignore" '/scratch/'

# Running again must not duplicate the line.
bash "$ROOT/scripts/update-installed-hub.sh" \
  --hub "$HUB_INSTALL" --source "$ROOT" --apply --allow-dirty > "$TMP_DIR/gitignore-repeat.out"
[ "$(grep -Fxc '/projects/' "$HUB_INSTALL/.gitignore")" -eq 1 ] \
  || fail 'updater duplicated the /projects/ ignore line'
echo 'Gitignore evidence: required line ensured, user entries preserved, no duplication.'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/hub-smoke-test.sh`
Expected: FAIL with `expected '/projects/' in .../_ai-hub/.gitignore`

- [ ] **Step 3: Write the implementation**

In `scripts/update-installed-hub.sh`, add this function next to the other file helpers (immediately after `copy_missing_memory_file`):

```bash
# Append-only, mirroring install-hub.sh:90-91. Never overwrite: the hub's
# .gitignore may carry the user's own entries, which a protected-file copy
# would destroy (Audit 5).
ensure_projects_ignored() {
  if ! grep -Fqx '/projects/' "$HUB_DIR/.gitignore" 2>/dev/null; then
    printf '%s\n' '/projects/' >> "$HUB_DIR/.gitignore"
    echo "Added missing ignore line: /projects/"
  fi
}
```

Then call it in the apply path, immediately after the line `for_each_protected_file copy_file`:

```bash
ensure_projects_ignored
```

- [ ] **Step 4: Run the suite to verify it passes**

Run: `bash scripts/hub-smoke-test.sh`
Expected: PASS, printing `Gitignore evidence: …`

- [ ] **Step 5: Commit**

```bash
git add scripts/update-installed-hub.sh scripts/hub-smoke-test.sh
git commit -m "fix: ensure the hub .gitignore keeps the /projects/ line without overwriting it"
```

---

### Task 5: Sole allowed root wording (defect 6)

**Files:**
- Modify: `hub-template/ai/skills/hub-registry-check/SKILL.md` (step 2, third bullet)

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

This is a protected architecture file. **Stop and get explicit user confirmation before editing.**

- [ ] **Step 1: Show the exact change and ask**

Present to the user, in `architecture-update` form: file, current wording, proposed wording, token impact (none material), and why it belongs there.

Current (`hub-template/ai/skills/hub-registry-check/SKILL.md`, step 2):

```
   - unregistered direct children of each allowed root, using names only and
     without recursive scanning or project-content reads;
```

Proposed:

```
   - unregistered direct children of the sole allowed root, using names only
     and without recursive scanning or project-content reads;
```

Reason: `ai/architecture.md` lines 47–48 permit exactly one root and
`check-hub-registry.sh` lines 68–70 enforce it. The plural is a leftover from
the pre-portable layout and describes a state the rules forbid.

Then ask: `Replace this?`

- [ ] **Step 2: Apply the confirmed edit**

Only after explicit confirmation, make the replacement above.

- [ ] **Step 3: Verify no check regressed**

Run: `bash scripts/check-consistency.sh`
Expected: `All canonical lists are consistent.`

Run: `bash scripts/hub-smoke-test.sh`
Expected: PASS. (`hub-smoke-test.sh` asserts substrings of several hub skills; confirm none of them covers this line — if a test fails, the assertion text must be updated in the same commit, not the rule reverted.)

- [ ] **Step 4: Commit**

```bash
git add hub-template/ai/skills/hub-registry-check/SKILL.md
git commit -m "docs: name the sole allowed root in hub-registry-check"
```

---

### Task 6: Name the three skills and guard the naming (defect 4)

**Files:**
- Modify: `hub-template/ai/architecture.md` (Ownership And Registry, Local Router, Project-local Router sections)
- Modify: `scripts/check-consistency.sh` (insert after the `hub skill prefix` check, currently ending line 161)
- Test: mutation test, Step 6 below

**Interfaces:**
- Consumes: `hub-template/ai/skills/*/` directory names.
- Produces: the check label `[hub skill naming]`.

`hub-template/ai/architecture.md` is a protected architecture file. **Stop and get explicit user confirmation before editing it.** The `check-consistency.sh` change is not protected and needs no separate confirmation.

- [ ] **Step 1: Show the exact rule-file changes and ask**

Present all three edits together in `architecture-update` form.

Edit 1 — Ownership And Registry, final paragraph. Current last sentence:

```
Validate maintained registry changes
with `scripts/check-hub-registry.sh` before relying on them.
```

Proposed:

```
Validate maintained registry changes
with `scripts/check-hub-registry.sh` before relying on them. Use the hub-owned
`hub-registry-check` workflow to audit registration health; it is read-only
until each individual fix receives its own approval.
```

Edit 2 — Local Router, after the numbered sequence, first sentence of the
following paragraph. Current:

```
The router never discovers projects by listing arbitrary folders, follows a
```

Proposed:

```
This sequence is the hub-owned `hub-project-router` workflow. The router never
discovers projects by listing arbitrary folders, follows a
```

Edit 3 — Project-local Router, first sentence. Current:

```
A confirmed project may install a local router only after at least three
stable independent areas have been identified and that project's
architecture-update process has been explicitly approved.
```

Proposed:

```
A confirmed project may install a local router through the hub-owned
`hub-local-router-install` workflow, only after at least three stable
independent areas have been identified and that project's architecture-update
process has been explicitly approved.
```

Reason: these three skills are currently named in no rule layer at all, so the
rules and the skill set can drift apart unnoticed — which is exactly what
happened and was only caught by manual audit.

Then ask: `Replace this?`

- [ ] **Step 2: Apply the confirmed edits**

Only after explicit confirmation, make the three replacements above.

- [ ] **Step 3: Write the failing guard test**

There is no separate test file for `check-consistency.sh`; it is verified by mutation. Perform Step 6's mutation now to confirm the check does not yet exist:

```bash
mkdir -p hub-template/ai/skills/hub-unnamed-probe
printf '%s\n' '---' 'name: hub-unnamed-probe' 'description: probe' '---' \
  > hub-template/ai/skills/hub-unnamed-probe/SKILL.md
bash scripts/check-consistency.sh; echo "rc=$?"
```

Expected before the fix: `All canonical lists are consistent.`, `rc=0` — the drift is invisible.

Leave the probe skill in place for Step 5.

- [ ] **Step 4: Write the implementation**

In `scripts/check-consistency.sh`, insert immediately after the `hub skill prefix` block (after the line `|| echo "OK [hub skill prefix] — every hub skill directory is prefixed"`):

```bash
# Reverse of the [hub skill references] check above: that one reads the
# hardcoded HUB_REQUIRED_SKILLS list and proves declared -> exists. This proves
# exists -> declared, so a skill cannot be added without naming it in the rules.
hub_naming_ok=1
hub_rule_files="hub-template/CLAUDE.md hub-template/AGENTS.md hub-template/ai/architecture.md"
if [ -d hub-template/ai/skills ]; then
  while IFS= read -r skill_dir; do
    skill_name="$(basename "$skill_dir")"
    if ! grep -Fq "$skill_name" $hub_rule_files; then
      echo "UNNAMED [hub skill naming] — $skill_name is named in no hub rule file"
      fail=1
      hub_naming_ok=0
    fi
  done < <(find hub-template/ai/skills -mindepth 1 -maxdepth 1 -type d | sort)
fi
[ "$hub_naming_ok" -eq 0 ] \
  || echo "OK [hub skill naming] — every hub skill is named in a rule file"
```

- [ ] **Step 5: Run the check to verify the probe is now caught**

Run: `bash scripts/check-consistency.sh; echo "rc=$?"`
Expected: `UNNAMED [hub skill naming] — hub-unnamed-probe is named in no hub rule file`, `rc=1`

- [ ] **Step 6: Remove the probe and confirm the check passes**

```bash
rm -rf hub-template/ai/skills/hub-unnamed-probe
bash scripts/check-consistency.sh
git status --porcelain
```

Expected: `OK [hub skill naming] — every hub skill is named in a rule file`, `All canonical lists are consistent.`, and `git status --porcelain` showing only the intended edits to `hub-template/ai/architecture.md` and `scripts/check-consistency.sh`.

- [ ] **Step 7: Run the full suite**

Run: `bash scripts/hub-smoke-test.sh && bash scripts/smoke-test.sh`
Expected: both PASS.

- [ ] **Step 8: Commit**

```bash
git add hub-template/ai/architecture.md scripts/check-consistency.sh
git commit -m "feat: name the router, registry-check and local-router skills, and guard skill naming"
```

---

### Task 7: Regression suite, changelog, and delivery to the live hub

**Files:**
- Modify: `ai/changelog.md`
- Modify: live hub at `/Users/zykovsrg/Documents/vibecode/_ai-hub` (delivery only, via the updater)

**Interfaces:**
- Consumes: everything from Tasks 1–6.
- Produces: the delivered live hub.

- [ ] **Step 1: Run the whole regression suite**

```bash
bash scripts/check-consistency.sh
bash scripts/hub-smoke-test.sh
bash scripts/smoke-test.sh
bash scripts/check-hub-registry.sh /Users/zykovsrg/Documents/vibecode/_ai-hub
```

Expected: all four pass. The last one prints `Registry check passed: 29 projects` with no warnings.

- [ ] **Step 2: Preview the hub delivery**

```bash
bash scripts/update-installed-hub.sh \
  --hub /Users/zykovsrg/Documents/vibecode/_ai-hub \
  --source /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture \
  --dry-run
```

Expected: diffs for `ai/architecture.md`, `ai/skills/hub-registry-check/SKILL.md`, and `scripts/check-hub-registry.sh`. Nothing else. Note the absolute `--source`; a relative one is now refused rather than silently misresolved.

- [ ] **Step 3: Show the preview and ask for delivery confirmation**

Present the dry-run output to the user and ask for explicit confirmation to apply. The live hub's rule files are protected; the dry run is the required preview. Do not proceed without a clear yes.

- [ ] **Step 4: Apply after confirmation**

```bash
bash scripts/update-installed-hub.sh \
  --hub /Users/zykovsrg/Documents/vibecode/_ai-hub \
  --source /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture \
  --apply
```

Expected: the three files updated, hub memory (registry, cards, allowed-roots, active-project) untouched.

- [ ] **Step 5: Verify the delivered hub**

```bash
bash scripts/check-hub-registry.sh /Users/zykovsrg/Documents/vibecode/_ai-hub
diff -rq hub-template/ /Users/zykovsrg/Documents/vibecode/_ai-hub/ | grep -v '^Only in'
git -C /Users/zykovsrg/Documents/vibecode/_ai-hub status --porcelain
```

Expected: registry check passes; the only reported differences are the three data files (`ai/allowed-roots.md`, `ai/active-project.md`, `ai/project-registry.md`); the hub's git status shows the three delivered rule/script files as modified.

- [ ] **Step 6: Record the change in the changelog**

Insert this entry at the top of the entry list in `ai/changelog.md`, matching the file's existing heading style:

```markdown
## 2026-08-15 — Hub audit fixes

- `--source` is now resolved before the updater enters the target directory, and
  a source that resolves to the target itself is refused. Previously a relative
  `--source` resolved against the hub, so the updater could compare the hub with
  itself and report "no updates".
- `check-hub-registry.sh` now warns on stderr about directories in `projects/`
  that have no registry entry. Exit code and stdout summary are unchanged, so
  the migration order (move → separate registration → validation) still works.
- `--check` now states that it compared version numbers, not file contents, in
  both updaters and in `--help`. Closes FT-20260815-002.
- The hub updater guarantees the `/projects/` line in the hub `.gitignore` by
  appending it when missing. It never overwrites the file.
- `hub-project-router`, `hub-registry-check` and `hub-local-router-install` are
  now named in `hub-template/ai/architecture.md`, and a new
  `[hub skill naming]` check in `check-consistency.sh` fails if any hub skill is
  named in no rule file.
- `hub-registry-check` no longer says "each allowed root"; exactly one root is
  permitted.
- Delivered to the live hub via `update-installed-hub.sh --apply`.
```

- [ ] **Step 7: Commit both repositories**

```bash
git add ai/changelog.md
git commit -m "docs: record the hub audit fixes"
git -C /Users/zykovsrg/Documents/vibecode/_ai-hub add -A
git -C /Users/zykovsrg/Documents/vibecode/_ai-hub commit -m "chore: update hub rules and validator from template"
```

- [ ] **Step 8: Propose task-finish**

Report what changed, which checks ran, and that task memory changed (`ai/current-task.md`, `ai/changelog.md`). Propose `task-finish`; do not declare the task closed.

---

## Notes for the implementer

- `FT-20260815-002` in `ai/future-tasks.md` describes defect 3. When Task 3 lands, that entry should be marked `done` during `task-finish`, not deleted mid-plan.
- `HUB_REQUIRED_SKILLS` at `scripts/check-consistency.sh:128` is a fourth, unmarked copy of the skill inventory. It is deliberately out of scope; do not refactor it here.
- The repository's `.git/info/exclude` ignores `/ai/`, but `ai/current-task.md`, `ai/changelog.md` and `ai/future-tasks.md` are already tracked, so `git add` works on them. This inconsistency is `FT-20260814-002` and is out of scope.
